"""HTTP API for extract queries, responses, reference tables and the vault."""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.catalog import file_catalog
from app.db import get_session
from app.edi.csv_export import render_csv
from app.models import (
    ExtractJob,
    ExtractOrphan,
    ExtractRequest,
    FirmsFacility,
    FirmsFacilityHistory,
    RefCarrier,
    RefCountry,
    RefDistrictPort,
    RefForeignPort,
    RefHtsUpdate,
    RefPull,
    User,
)
from app.mq.outbound import ExtractOutbound
from app.security import can_see, current_user, require_admin, visible_requests
from app.services.entry import ENTRY_SOURCES, validate_entry_locations
from app.services.workflow import apply_response, mask_password, preview, resume_unsent, retry, submit

router = APIRouter(prefix='/api/extract')


class QueryBody(BaseModel):
    file_code: str
    query_type: str
    params: dict = Field(default_factory=dict)
    kn_number: str | None = None
    control_id: str | None = None


class CallbackBody(BaseModel):
    message: str
    correlation_id: str | None = None


class DevResponseBody(BaseModel):
    message: str


class EntryLocation(BaseModel):
    firms_code: str
    source: str = 'AE20'


class EntryValidateBody(BaseModel):
    locations: list[EntryLocation] = Field(default_factory=list)


def _request_dict(row: ExtractRequest, *, with_edi: bool = False) -> dict:
    payload = {
        'id': row.id,
        'control_id': row.control_id,
        'kn_number': row.kn_number,
        'file_code': row.file_code,
        'query_type': row.query_type,
        'params': row.params or {},
        'status': row.status,
        'mq_send_state': row.mq_send_state,
        'mq_send_error': row.mq_send_error,
        'requested_by': row.requested_by,
        'job_id': row.job_id,
        'created_at': row.created_at.isoformat() if row.created_at else None,
        'submitted_at': row.submitted_at.isoformat() if row.submitted_at else None,
        'updated_at': row.updated_at.isoformat() if row.updated_at else None,
        'timeline': [
            {
                'from_status': item.from_status,
                'to_status': item.to_status,
                'changed_at': item.changed_at.isoformat() if item.changed_at else None,
                'changed_by': item.changed_by,
                'notes': item.notes,
            }
            for item in row.status_log
        ],
    }
    if with_edi:
        payload['edi'] = mask_password(row.edi_text)
        if row.response:
            payload['response'] = {
                'raw_text': row.response.raw_text,
                'parsed': row.response.parsed_json,
                'received_at': row.response.received_at.isoformat() if row.response.received_at else None,
                'parse_errors': row.response.parse_errors,
            }
        else:
            payload['response'] = None
    return payload


def _job_dict(job: ExtractJob) -> dict:
    rows = list(job.requests)
    return {
        'id': job.id,
        'file_code': job.file_code,
        'query_type': job.query_type,
        'status': job.status,
        'requested_by': job.requested_by,
        'created_at': job.created_at.isoformat() if job.created_at else None,
        'total': len(rows),
        'pending': sum(1 for row in rows if row.status == 'PENDING_CBP'),
        'approved': sum(1 for row in rows if row.status == 'APPROVED'),
        'rejected': sum(1 for row in rows if row.status == 'REJECTED'),
        'failed': sum(1 for row in rows if row.mq_send_state == 'FAILED'),
        'requests': [_request_dict(row) for row in rows],
    }


def _load(session: Session, request_id: str, user: User) -> ExtractRequest:
    row = session.get(ExtractRequest, request_id)
    if row is None or not can_see(user, row):
        raise HTTPException(status_code=404, detail='Request not found')
    return row


@router.get('/files')
def files() -> dict:
    return {'files': file_catalog()}


@router.get('/me')
def me(user: User = Depends(current_user)) -> dict:
    return {'id': user.id, 'name': user.display_name, 'role': user.role}


@router.post('/preview')
def preview_query(body: QueryBody, user: User = Depends(current_user)) -> dict:
    return preview(user, body.file_code, body.query_type, body.params, body.kn_number, body.control_id)


@router.post('/queries')
def create_query(body: QueryBody, session: Session = Depends(get_session), user: User = Depends(current_user)) -> dict:
    result = submit(session, user, body.file_code, body.query_type, body.params, body.kn_number, body.control_id)
    payload = {'request': _request_dict(result['request'], with_edi=True)}
    if result['job'] is not None:
        payload['job'] = _job_dict(result['job'])
    return payload


@router.get('/requests')
def list_requests(
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
    q: str = '',
) -> dict:
    query = visible_requests(user)
    if q.strip():
        term = f'%{q.strip().upper()}%'
        query = query.where(or_(
            ExtractRequest.control_id.like(term),
            ExtractRequest.kn_number.like(term),
            ExtractRequest.file_code.like(term),
        ))
    rows = session.scalars(query.limit(200)).all()
    return {'requests': [_request_dict(row) for row in rows]}


@router.get('/requests/{request_id}')
def get_request(request_id: str, session: Session = Depends(get_session), user: User = Depends(current_user)) -> dict:
    return _request_dict(_load(session, request_id, user), with_edi=True)


@router.get('/requests/{request_id}/csv')
def request_csv(request_id: str, session: Session = Depends(get_session), user: User = Depends(current_user)) -> Response:
    row = _load(session, request_id, user)
    if row.response is None or not row.response.parsed_json:
        raise HTTPException(status_code=409, detail='This request has no parsed response yet')
    text = render_csv(row.response.parsed_json)
    filename = f'{row.file_code}_{row.control_id}.csv'
    return Response(
        content=text,
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.post('/requests/{request_id}/retry')
def retry_request(
    request_id: str,
    confirm_possible_duplicate: bool = Query(default=False),
    session: Session = Depends(get_session),
    user: User = Depends(require_admin),
) -> dict:
    row = _load(session, request_id, user)
    retry(session, user, row, confirm_possible_duplicate)
    session.refresh(row)
    return _request_dict(row, with_edi=True)


@router.post('/requests/{request_id}/dev-response')
def dev_response(
    request_id: str,
    body: DevResponseBody,
    session: Session = Depends(get_session),
    user: User = Depends(require_admin),
) -> dict:
    from app.config import get_settings
    if not get_settings().is_dev:
        raise HTTPException(status_code=404, detail='Not available')
    row = _load(session, request_id, user)
    apply_response(session, body.message, correlation_id=row.control_id)
    session.refresh(row)
    return _request_dict(row, with_edi=True)


@router.get('/jobs/{job_id}')
def get_job(job_id: str, session: Session = Depends(get_session), user: User = Depends(current_user)) -> dict:
    job = session.get(ExtractJob, job_id)
    if job is None or (user.role != 'ADMIN' and job.requested_by != user.id):
        raise HTTPException(status_code=404, detail='Job not found')
    return _job_dict(job)


@router.post('/jobs/{job_id}/resume')
def resume_job(job_id: str, session: Session = Depends(get_session), user: User = Depends(require_admin)) -> dict:
    job = session.get(ExtractJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail='Job not found')
    resume_unsent(session, user, job)
    session.refresh(job)
    return _job_dict(job)


@router.post('/callback')
def callback(
    body: CallbackBody,
    session: Session = Depends(get_session),
    x_callback_secret: str | None = Header(default=None),
) -> dict:
    from app.config import get_settings
    secret = get_settings().callback_secret
    if not secret:
        raise HTTPException(status_code=503, detail='EXTRACT_CALLBACK_SECRET is not set')
    if not hmac.compare_digest((x_callback_secret or '').encode(), secret.encode()):
        raise HTTPException(status_code=401, detail='Callback secret rejected')
    return apply_response(session, body.message, body.correlation_id)


@router.get('/mq/status')
def mq_status(user: User = Depends(current_user)) -> dict:
    return ExtractOutbound().status()


@router.get('/vault')
def vault(session: Session = Depends(get_session), user: User = Depends(current_user)) -> dict:
    rows = session.scalars(visible_requests(user).limit(200)).all()
    payload = {'requests': [_request_dict(row, with_edi=True) for row in rows]}
    failed = [row for row in rows if row.mq_send_state == 'FAILED']
    if user.role == 'ADMIN':
        orphans = session.scalars(select(ExtractOrphan).order_by(ExtractOrphan.received_at.desc()).limit(100)).all()
        payload['orphans'] = [
            {
                'id': item.id,
                'control_id': item.control_id,
                'kn_number': item.kn_number,
                'raw_text': item.raw_text,
                'received_at': item.received_at.isoformat() if item.received_at else None,
            }
            for item in orphans
        ]
        payload['dead_letters'] = [_request_dict(row, with_edi=True) for row in failed]
    else:
        payload['orphans'] = []
        payload['dead_letters'] = []
    return payload


@router.get('/reference/summary')
def reference_summary(session: Session = Depends(get_session), user: User = Depends(current_user)) -> dict:
    pulls = {row.file_code: row for row in session.scalars(select(RefPull)).all()}

    def block(file_code: str, count: int) -> dict:
        pull = pulls.get(file_code)
        return {
            'file_code': file_code,
            'count': count,
            'last_pull': pull.last_success_at.isoformat() if pull and pull.last_success_at else None,
            'last_control_id': pull.last_control_id if pull else None,
        }

    return {
        'files': [
            block('F101', session.scalar(select(func.count()).select_from(RefDistrictPort)) or 0),
            block('F102', session.scalar(select(func.count()).select_from(RefCountry)) or 0),
            block('F104', session.scalar(select(func.count()).select_from(RefForeignPort)) or 0),
            block('F106', session.scalar(select(func.count()).select_from(RefCarrier)) or 0),
            block('F110', session.scalar(select(func.count()).select_from(RefHtsUpdate)) or 0),
            block('F111', session.scalar(select(func.count()).select_from(FirmsFacility)) or 0),
        ],
        'role': user.role,
    }


@router.get('/reference/firms')
def firms_table(
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
    q: str = '',
    status: str = '',
    facility_type: str = '',
    state: str = '',
    district: str = '',
) -> dict:
    del user
    query = select(FirmsFacility)
    if q.strip():
        term = f'%{q.strip().upper()}%'
        query = query.where(or_(FirmsFacility.firms_code.like(term), FirmsFacility.name.like(term)))
    if status:
        query = query.where(FirmsFacility.status == status.upper()[:1])
    if facility_type:
        query = query.where(FirmsFacility.facility_type == facility_type)
    if state:
        query = query.where(FirmsFacility.state == state.upper())
    if district:
        query = query.where(FirmsFacility.district_port.like(f'{district}%'))
    rows = session.scalars(query.order_by(FirmsFacility.firms_code).limit(500)).all()
    return {'rows': [_facility(row) for row in rows]}


def _facility(row: FirmsFacility) -> dict:
    return {
        'firms_code': row.firms_code,
        'district_port': row.district_port,
        'status': 'Active' if row.status == 'A' else 'Deactivated' if row.status == 'D' else row.status,
        'facility_type': row.facility_type,
        'name': row.name,
        'last_update': row.last_update,
        'address': row.address,
        'city': row.city,
        'state': row.state,
        'zip': row.zip,
        'country': row.country,
        'source_control_id': row.source_control_id,
        'first_seen': row.first_seen.isoformat() if row.first_seen else None,
        'last_seen': row.last_seen.isoformat() if row.last_seen else None,
    }


@router.get('/reference/firms/entry-sources')
def firms_entry_sources(user: User = Depends(current_user)) -> dict:
    del user
    return {'sources': [{'id': key, 'label': label} for key, label in ENTRY_SOURCES.items()]}


@router.post('/reference/firms/validate')
def firms_validate(
    body: EntryValidateBody,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
) -> dict:
    del user
    return validate_entry_locations(session, [item.model_dump() for item in body.locations])


@router.get('/reference/firms/changes')
def firms_changes(session: Session = Depends(get_session), user: User = Depends(require_admin)) -> dict:
    del user
    rows = session.scalars(
        select(FirmsFacilityHistory).order_by(FirmsFacilityHistory.changed_at.desc()).limit(200)
    ).all()
    return {
        'changes': [
            {
                'firms_code': row.firms_code,
                'change_type': row.change_type,
                'field_name': row.field_name,
                'old_value': row.old_value,
                'new_value': row.new_value,
                'changed_at': row.changed_at.isoformat() if row.changed_at else None,
                'source_control_id': row.source_control_id,
            }
            for row in rows
        ]
    }


@router.get('/reference/ports')
def ports(session: Session = Depends(get_session), user: User = Depends(current_user), q: str = '') -> dict:
    del user
    query = select(RefDistrictPort)
    if q.strip():
        term = f'%{q.strip().upper()}%'
        query = query.where(or_(RefDistrictPort.code.like(term), RefDistrictPort.name.like(term)))
    rows = session.scalars(query.order_by(RefDistrictPort.code).limit(500)).all()
    return {'rows': [
        {'code': row.code, 'name': row.name, 'city': row.city, 'state': row.state, 'zip': row.zip}
        for row in rows
    ]}


@router.get('/reference/countries')
def countries(session: Session = Depends(get_session), user: User = Depends(current_user), q: str = '') -> dict:
    del user
    query = select(RefCountry)
    if q.strip():
        term = f'%{q.strip().upper()}%'
        query = query.where(or_(RefCountry.iso.like(term), RefCountry.name.like(term)))
    rows = session.scalars(query.order_by(RefCountry.iso).limit(500)).all()
    return {'rows': [{'iso': row.iso, 'name': row.name, 'spi': row.spi} for row in rows]}


@router.get('/reference/foreign-ports')
def foreign_ports(session: Session = Depends(get_session), user: User = Depends(current_user), q: str = '') -> dict:
    del user
    query = select(RefForeignPort)
    if q.strip():
        term = f'%{q.strip().upper()}%'
        query = query.where(or_(RefForeignPort.code.like(term), RefForeignPort.name.like(term)))
    rows = session.scalars(query.order_by(RefForeignPort.code).limit(500)).all()
    return {'rows': [{'code': row.code, 'name': row.name} for row in rows]}


@router.get('/reference/carriers')
def carriers(session: Session = Depends(get_session), user: User = Depends(current_user), q: str = '') -> dict:
    del user
    query = select(RefCarrier)
    if q.strip():
        term = f'%{q.strip().upper()}%'
        query = query.where(or_(RefCarrier.code.like(term), RefCarrier.name.like(term)))
    rows = session.scalars(query.order_by(RefCarrier.code).limit(500)).all()
    return {'rows': [
        {'code': row.code, 'name': row.name, 'mode': row.mode, 'mode_name': row.mode_name}
        for row in rows
    ]}
