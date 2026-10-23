"""Create a request, publish it, and apply the response in one transaction."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog import find_file
from app.config import get_settings
from app.edi.build import build_block, split_codes
from app.edi.envelope import Identity, unbracket
from app.edi.parse import parse_response
from app.models import (
    ExtractJob,
    ExtractOrphan,
    ExtractRequest,
    ExtractResponse,
    ExtractStatusLog,
    FirmsFacility,
    FirmsFacilityHistory,
    RefCarrier,
    RefCountry,
    RefDistrictPort,
    RefForeignPort,
    RefHtsUpdate,
    RefPull,
    User,
    utcnow,
)
from app.mq.outbound import ExtractOutbound, MqError
from app.security import requires_admin

log = logging.getLogger('extract')

FULL_PULLS = {'ALL_DATE', 'ALL_DISTRICT', 'FULL', 'AIR', 'RANGE'}
BUILD_FILE = {
    'F111': 'FIRMS',
    'F101': 'DISTRICT',
    'F102': 'COUNTRY',
    'F104': 'FOREIGN_PORT',
    'F106': 'CARRIER',
    'F110': 'HTS',
}
APP_IDS = {'F101': 'FQ', 'F102': 'FQ', 'F104': 'FQ', 'F106': 'FQ', 'F110': 'HB', 'F111': 'FQ'}


def new_control_id() -> str:
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(secrets.choice(alphabet) for _ in range(20))


def _build_params(file_code: str, query_type: str, params: dict) -> tuple[str, dict]:
    """Map the screen's record id and field names onto the builder."""
    kind = BUILD_FILE[file_code]
    if file_code == 'F111' and query_type == 'LIST':
        valid, invalid = split_codes(str(params.get('codes', '')))
        if invalid:
            raise ValueError(f'Not valid FIRMS codes: {", ".join(invalid[:8])}')
        if not valid:
            raise ValueError('Enter at least one FIRMS code')
        return 'LIST', {'codes': valid}
    if file_code == 'F111' and query_type == 'CODE':
        return 'CODE', {'code': params.get('firms_code', '')}
    if file_code == 'F111' and query_type == 'NAME':
        return 'NAME', {'name': params.get('facility_name', ''), 'district': params.get('district', '')}
    if file_code == 'F111' and query_type in {'DISTRICT', 'ALL_DATE'}:
        return query_type, {'district': params.get('district', ''), 'begin_date': params.get('begin_date', '')}
    if file_code == 'F106' and query_type == 'AIR':
        return 'AIR_ALL', {}
    if file_code == 'F106':
        return query_type, {'name': params.get('carrier_name', ''), 'code': params.get('carrier_code', '')}
    if file_code == 'F110':
        return 'RANGE', {
            'update_number': params.get('update_number', ''),
            'from_hts': params.get('from_number', ''),
            'to_hts': params.get('to_number', ''),
        }
    return query_type, {} if kind else params


def _log(session: Session, row: ExtractRequest, to_status: str, actor: str, notes: str) -> None:
    session.add(ExtractStatusLog(
        request_id=row.id,
        from_status=row.status if row.status != to_status else row.status,
        to_status=to_status,
        changed_by=actor,
        notes=notes,
    ))


def mask_password(edi: str) -> str:
    lines = [ln for ln in (edi or '').split('\n')]
    if lines and lines[0].startswith('A') and len(lines[0]) >= 14:
        lines[0] = lines[0][:8] + (' ' * 6) + lines[0][14:]
    return '\n'.join(lines)


def _identity() -> Identity:
    settings = get_settings()
    if not settings.transmitter_ready:
        raise HTTPException(status_code=422, detail=[
            'Transmitter identity is incomplete. Set KN_SITE_CODE, KN_SENDER_ID, '
            'KN_TRANSMITTER_PASSWORD, KN_PROCESSING_PORT, KN_FILER_CODE, '
            'KN_PREPARER_PORT and KN_PREPARER_FILER.',
        ])
    return Identity(
        site_code=settings.site_code,
        sender_id=settings.sender_id,
        password=settings.password,
        port=settings.processing_port,
        filer=settings.filer_code,
        preparer_port=settings.preparer_port,
        preparer_filer=settings.preparer_filer,
    )


def _guard(user: User, file_code: str, query_type: str) -> None:
    if find_file(file_code) is None:
        raise HTTPException(status_code=422, detail=[f'{file_code} is not in the June 25, 2018 extract chapter'])
    if requires_admin(query_type) and user.role != 'ADMIN':
        raise HTTPException(status_code=403, detail='Whole-file loads are limited to an admin')


def render_edi(file_code: str, query_type: str, params: dict, kn_number: str, control_id: str) -> str:
    try:
        build_type, build_params = _build_params(file_code, query_type, params)
        return build_block(
            _identity(),
            when=datetime.now().strftime('%m%d%y'),
            kn_number=kn_number,
            control_id=control_id,
            file_code=BUILD_FILE[file_code],
            query_type=build_type,
            params=build_params,
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=[str(exc)]) from exc


def preview(user: User, file_code: str, query_type: str, params: dict, kn_number: str | None, control_id: str | None) -> dict:
    _guard(user, file_code, query_type)
    kn = (kn_number or '').strip().upper()
    control = (control_id or '').strip().upper() or 'PREVIEWPREVIEWPREVIE'
    edi = render_edi(file_code, query_type, params or {}, kn, control)
    lines = edi.split('\n')
    return {
        'edi': mask_password(edi),
        'line_count': len(lines),
        'all_80': all(len(ln) == 80 for ln in lines),
        'kn_number': kn,
        'control_id': control,
        'app_id': APP_IDS[file_code],
    }


def _store_request(
    session: Session,
    user: User,
    file_code: str,
    query_type: str,
    params: dict,
    *,
    kn_number: str | None = None,
    control_id: str | None = None,
    job: ExtractJob | None = None,
) -> ExtractRequest:
    control = (control_id or '').strip().upper() or new_control_id()
    if session.scalar(select(ExtractRequest).where(ExtractRequest.control_id == control)):
        raise HTTPException(status_code=409, detail='That control ID is already used. Generate another.')
    kn = (kn_number or '').strip().upper()
    if kn and session.scalar(select(ExtractRequest).where(ExtractRequest.kn_number == kn)):
        raise HTTPException(status_code=409, detail='That A-record user data is already used.')
    edi = render_edi(file_code, query_type, params, kn, control)
    row = ExtractRequest(
        control_id=control,
        kn_number=kn,
        file_code=file_code,
        query_type=query_type,
        params=params,
        edi_text=edi,
        status='DRAFT',
        requested_by=user.id,
        job=job,
    )
    session.add(row)
    session.flush()
    _log(session, row, 'DRAFT', user.id, 'Built')
    return row


def transmit(session: Session, row: ExtractRequest, actor: str) -> None:
    row.mq_send_state = 'PENDING'
    row.mq_send_error = None
    session.commit()
    log.info('extract.queue control_id=%s request_id=%s file=%s', row.control_id, row.id, row.file_code)
    try:
        ExtractOutbound().put(
            edi=row.edi_text,
            control_id=row.control_id,
            request_id=row.id,
            file_code=row.file_code,
        )
    except (MqError, OSError, Exception) as exc:  # noqa: BLE001 - surface the PUT failure, leave the row
        row.mq_send_state = 'FAILED'
        row.mq_send_error = str(exc)[:500]
        _log(session, row, 'DRAFT', actor, f'MQ PUT failed: {row.mq_send_error}')
        row.status = 'DRAFT'
        session.commit()
        log.info('extract.failed control_id=%s request_id=%s', row.control_id, row.id)
        raise HTTPException(status_code=503, detail=['MQ PUT failed. The request stays draft.', row.mq_send_error]) from exc
    row.mq_send_state = 'SENT'
    row.submitted_at = datetime.now(timezone.utc)
    _log(session, row, 'PENDING_CBP', actor, f'MQ PUT {row.control_id}')
    row.status = 'PENDING_CBP'
    session.commit()
    log.info('extract.sent control_id=%s request_id=%s', row.control_id, row.id)


def submit(
    session: Session,
    user: User,
    file_code: str,
    query_type: str,
    params: dict | None,
    kn_number: str | None = None,
    control_id: str | None = None,
) -> dict:
    params = params or {}
    file_code = file_code.upper()
    query_type = query_type.upper()
    _guard(user, file_code, query_type)
    if query_type == 'ALL_DISTRICT':
        return _district_job(session, user, params)
    if query_type == 'LIST':
        valid, invalid = split_codes(str(params.get('codes', '')))
        if invalid:
            raise HTTPException(status_code=422, detail=[f'Not valid FIRMS codes: {", ".join(invalid[:8])}'])
        cap = get_settings().max_body_records
        if len(valid) > cap:
            return _chunked_list(session, user, valid, cap)
    row = _store_request(session, user, file_code, query_type, params, kn_number=kn_number, control_id=control_id)
    session.commit()
    transmit(session, row, user.id)
    session.refresh(row)
    return {'request': row, 'job': None}


def _chunked_list(session: Session, user: User, codes: list[str], cap: int) -> dict:
    job = ExtractJob(file_code='F111', query_type='LIST', params={'count': len(codes)}, status='PENDING_CBP', requested_by=user.id)
    session.add(job)
    session.flush()
    rows = []
    for start in range(0, len(codes), cap):
        chunk = codes[start:start + cap]
        row = _store_request(session, user, 'F111', 'LIST', {'codes': ' '.join(chunk)}, job=job)
        rows.append(row)
    session.commit()
    for row in rows:
        try:
            transmit(session, row, user.id)
        except HTTPException:
            continue  # the row is marked FAILED; keep sending the other chunks
    _refresh_job(job)
    session.commit()
    return {'request': rows[0], 'job': job}


def _district_job(session: Session, user: User, params: dict) -> dict:
    codes = session.scalars(select(RefDistrictPort.code)).all()
    districts = sorted({code[:2] for code in codes if len(code) >= 2 and code[:2].isdigit()})
    if not districts:
        raise HTTPException(status_code=409, detail='Load the region/district/port file before a district sweep')
    begin = str(params.get('begin_date') or '')
    job = ExtractJob(
        file_code='F111',
        query_type='ALL_DISTRICT',
        params={'districts': districts, 'begin_date': begin},
        status='PENDING_CBP',
        requested_by=user.id,
    )
    session.add(job)
    session.flush()
    rows = []
    for district in districts:
        row = _store_request(
            session, user, 'F111', 'DISTRICT',
            {'district': district, 'begin_date': begin},
            job=job,
        )
        rows.append(row)
    session.commit()
    for row in rows:
        try:
            transmit(session, row, user.id)
        except HTTPException:
            continue
    _refresh_job(job)
    session.commit()
    return {'request': rows[0], 'job': job}


def retry(session: Session, user: User, row: ExtractRequest, confirm: bool) -> ExtractRequest:
    if user.role != 'ADMIN':
        raise HTTPException(status_code=403, detail='Retry requires an admin')
    if row.mq_send_state not in {'PENDING', 'FAILED'} or row.status not in {'DRAFT', 'PENDING_CBP'}:
        raise HTTPException(status_code=409, detail='This request has no failed or unconfirmed send to retry')
    if row.mq_send_state == 'PENDING' and not confirm:
        raise HTTPException(status_code=409, detail=[
            'The original send may already have been delivered. Retry with confirm_possible_duplicate=true.',
        ])
    log.info('extract.retry control_id=%s request_id=%s user=%s', row.control_id, row.id, user.id)
    transmit(session, row, user.id)
    session.refresh(row)
    return row


def resume_unsent(session: Session, user: User, job: ExtractJob) -> None:
    """Resend every chunk that failed or never left the building."""
    for row in list(job.requests):
        if row.mq_send_state == 'FAILED':
            try:
                retry(session, user, row, confirm=False)
            except HTTPException:
                continue
        elif row.mq_send_state is None and row.status == 'DRAFT':
            try:
                transmit(session, row, user.id)
            except HTTPException:
                continue
    session.refresh(job)
    _refresh_job(job)
    session.commit()


def apply_response(session: Session, message: str, correlation_id: str | None = None) -> dict:
    parsed = parse_response(message)
    echoed = parsed.control_id
    supplied = (correlation_id or '').strip().upper()
    if supplied and echoed and supplied != echoed:
        raise HTTPException(status_code=409, detail='Correlation ID does not match the control ID echoed in the B record')
    control = supplied or echoed
    row = None
    if control:
        row = session.scalar(select(ExtractRequest).where(ExtractRequest.control_id == control))
    if row is None and parsed.kn_number:
        found = session.scalar(select(ExtractRequest).where(ExtractRequest.kn_number == parsed.kn_number))
        if found and echoed and found.control_id != echoed:
            raise HTTPException(status_code=409, detail='KN number does not belong to the echoed control ID')
        row = found
    bare = unbracket(message)
    if row is None:
        session.add(ExtractOrphan(control_id=control or None, kn_number=parsed.kn_number or None, raw_text=bare))
        session.commit()
        log.info('extract.orphan control_id=%s', control)
        raise HTTPException(status_code=404, detail='No request matches this control ID. The response was kept for an admin.')
    if row.response and row.response.raw_text == bare:
        log.info('extract.duplicate control_id=%s request_id=%s', row.control_id, row.id)
        return {'request_id': row.id, 'status': row.status, 'duplicate': True}
    _apply_rows(session, parsed, row.control_id)
    warnings = '\n'.join(parsed.warnings) or None
    if row.response:
        row.response.raw_text = bare
        row.response.parsed_json = parsed.as_dict()
        row.response.received_at = utcnow()
        row.response.parse_errors = warnings
    else:
        session.add(ExtractResponse(
            request_id=row.id,
            raw_text=bare,
            parsed_json=parsed.as_dict(),
            parse_errors=warnings,
        ))
    errors = [item for item in parsed.rows if item.get('kind') in {'rejection', 'carrier_rejection'}]
    data = [item for item in parsed.rows if item.get('kind') not in {'rejection', 'carrier_rejection', 'carrier_query'}]
    new_status = 'REJECTED' if errors and not data else 'APPROVED'
    previous = row.status
    _log(session, row, new_status, 'mq', f'Response for {row.control_id}')
    row.status = new_status
    if row.query_type in FULL_PULLS or row.file_code in {'F101', 'F102', 'F104'}:
        _touch_pull(session, row, len(data))
    if row.job:
        _refresh_job(row.job)
    session.commit()
    log.info('extract.matched control_id=%s request_id=%s status=%s from=%s', row.control_id, row.id, new_status, previous)
    return {'request_id': row.id, 'status': new_status, 'duplicate': False, 'rows': len(parsed.rows)}


def _refresh_job(job: ExtractJob) -> None:
    rows = list(job.requests)
    if not rows:
        return
    waiting = [row for row in rows if row.status == 'PENDING_CBP' or row.mq_send_state in {None, 'PENDING'}]
    failed = [row for row in rows if row.mq_send_state == 'FAILED']
    if waiting:
        job.status = 'PENDING_CBP'
    elif failed:
        job.status = 'SUBMITTED'
    elif any(row.status == 'APPROVED' for row in rows):
        job.status = 'APPROVED'
    else:
        job.status = 'REJECTED'


def _touch_pull(session: Session, row: ExtractRequest, count: int) -> None:
    pull = session.get(RefPull, row.file_code)
    if pull is None:
        pull = RefPull(file_code=row.file_code, row_count=0)
        session.add(pull)
    pull.last_success_at = utcnow()
    pull.last_control_id = row.control_id
    pull.row_count = count


def _apply_rows(session: Session, parsed, control_id: str) -> None:
    now = utcnow()
    for row in parsed.rows:
        kind = row.get('kind')
        if kind == 'facility' and row.get('firms_code'):
            _upsert_facility(session, row, control_id, now)
        elif kind == 'district_port' and row.get('code'):
            _upsert_port(session, row, control_id, now)
        elif kind == 'country' and row.get('iso'):
            _upsert_country(session, row, control_id, now)
        elif kind == 'foreign_port' and row.get('code'):
            _upsert_foreign_port(session, row, control_id, now)
        elif kind == 'carrier' and row.get('carrier_code'):
            _upsert_carrier(session, row, control_id, now)
        elif kind == 'hts_update':
            existing = session.scalar(select(RefHtsUpdate).where(RefHtsUpdate.control_id == control_id))
            if existing is None:
                session.add(RefHtsUpdate(
                    control_id=control_id,
                    update_number=row.get('update_number', ''),
                    from_number=row.get('from_number', ''),
                    to_number=row.get('to_number', ''),
                    narrative=row.get('narrative', '')[:52],
                ))
            else:
                existing.narrative = row.get('narrative', '')[:52]
                existing.update_number = row.get('update_number', '')
                existing.from_number = row.get('from_number', '')
                existing.to_number = row.get('to_number', '')


def _upsert_facility(session: Session, row: dict, control_id: str, now: datetime) -> None:
    current = session.get(FirmsFacility, row['firms_code'])
    if current is None:
        session.add(FirmsFacility(
            firms_code=row['firms_code'],
            district_port=row.get('district_port', ''),
            status=row.get('status', ''),
            facility_type=row.get('facility_type_code', ''),
            name=row.get('facility_name', ''),
            last_update=row.get('last_update', ''),
            address=row.get('address', ''),
            city=row.get('city', ''),
            state=row.get('state', ''),
            zip=row.get('zip', ''),
            country=row.get('country', ''),
            source_control_id=control_id,
            first_seen=now,
            last_seen=now,
        ))
        session.add(FirmsFacilityHistory(
            firms_code=row['firms_code'], change_type='new', field_name='firms_code',
            new_value=row['firms_code'], source_control_id=control_id, changed_at=now,
        ))
        return
    if current.status != row.get('status', '') and row.get('status') == 'D':
        session.add(FirmsFacilityHistory(
            firms_code=current.firms_code, change_type='deactivated', field_name='status',
            old_value=current.status, new_value='D', source_control_id=control_id, changed_at=now,
        ))
    elif current.status != row.get('status', '') or current.name != row.get('facility_name', ''):
        session.add(FirmsFacilityHistory(
            firms_code=current.firms_code, change_type='updated', field_name='name' if current.name != row.get('facility_name', '') else 'status',
            old_value=current.name if current.name != row.get('facility_name', '') else current.status,
            new_value=row.get('facility_name', '') if current.name != row.get('facility_name', '') else row.get('status', ''),
            source_control_id=control_id, changed_at=now,
        ))
    current.district_port = row.get('district_port', '')
    current.status = row.get('status', '')
    current.facility_type = row.get('facility_type_code', '')
    current.name = row.get('facility_name', '')
    current.last_update = row.get('last_update', '')
    current.address = row.get('address', '')
    current.city = row.get('city', '')
    current.state = row.get('state', '')
    current.zip = row.get('zip', '')
    current.country = row.get('country', '')
    current.source_control_id = control_id
    current.last_seen = now


def _stamp(current, now: datetime, control_id: str) -> None:
    if current.first_seen is None:
        current.first_seen = now
    current.last_seen = now
    current.source_control_id = control_id


def _upsert_port(session: Session, row: dict, control_id: str, now: datetime) -> None:
    current = session.get(RefDistrictPort, row['code'])
    if current is None:
        current = RefDistrictPort(code=row['code'], first_seen=now, last_seen=now)
        session.add(current)
    for key in (
        'name', 'address1', 'address2', 'address3', 'carrier_type', 'primary_team_location',
        'secondary_team_location', 'port_of_unlading', 'city', 'state', 'zip', 'subport_code',
    ):
        setattr(current, key, row.get(key, '') or '')
    _stamp(current, now, control_id)


def _upsert_country(session: Session, row: dict, control_id: str, now: datetime) -> None:
    current = session.get(RefCountry, row['iso'])
    if current is None:
        current = RefCountry(iso=row['iso'], first_seen=now, last_seen=now)
        session.add(current)
    for key in (
        'name', 'rate_column', 'restriction', 'gsp', 'gsp_begin', 'gsp_end', 'spi',
        'currency_name', 'currency_code', 'drawback', 'schedule_c', 'agoa_spi', 'agoa_ldd',
    ):
        setattr(current, key, row.get(key, '') or '')
    current.programs = row.get('programs') or []
    _stamp(current, now, control_id)


def _upsert_foreign_port(session: Session, row: dict, control_id: str, now: datetime) -> None:
    current = session.get(RefForeignPort, row['code'])
    if current is None:
        current = RefForeignPort(code=row['code'], first_seen=now, last_seen=now)
        session.add(current)
    current.name = row.get('name', '')
    _stamp(current, now, control_id)


def _upsert_carrier(session: Session, row: dict, control_id: str, now: datetime) -> None:
    current = session.get(RefCarrier, row['carrier_code'])
    if current is None:
        current = RefCarrier(code=row['carrier_code'], first_seen=now, last_seen=now)
        session.add(current)
    current.name = row.get('carrier_name', '')
    current.mode = row.get('mode', '')
    current.mode_name = row.get('mode_name', '')
    current.address = row.get('address', '')
    current.airway_bill_prefix = row.get('airway_bill_prefix', '')
    _stamp(current, now, control_id)
