"""API tests: RLS, mock MQ round trip, idempotent apply, CSV download."""

import os
from pathlib import Path

from app.db import SessionLocal
from app.models import FirmsFacilityHistory
from tests.conftest import fo_for as _response_for


def test_operator_cannot_load_the_whole_file(client):
    res = client.post('/api/extract/queries', headers={'X-Demo-User': 'operator'}, json={
        'file_code': 'F111', 'query_type': 'ALL_DATE', 'params': {'begin_date': '010100'},
    })
    assert res.status_code == 403


def test_operator_cannot_see_another_users_request(client):
    created = client.post('/api/extract/queries', headers={'X-Demo-User': 'admin'}, json={
        'file_code': 'F111', 'query_type': 'CODE', 'params': {'firms_code': 'E364'},
    })
    assert created.status_code == 200, created.text
    request_id = created.json()['request']['id']
    hidden = client.get(f'/api/extract/requests/{request_id}', headers={'X-Demo-User': 'operator'})
    assert hidden.status_code == 404
    visible = client.get(f'/api/extract/requests/{request_id}', headers={'X-Demo-User': 'admin'})
    assert visible.status_code == 200
    assert 'KLEAR1' not in visible.json()['edi']


def test_round_trip_persists_facility_and_csv(client):
    created = client.post('/api/extract/queries', headers={'X-Demo-User': 'operator'}, json={
        'file_code': 'F111', 'query_type': 'CODE', 'params': {'firms_code': 'E364'},
    })
    assert created.status_code == 200, created.text
    body = created.json()['request']
    assert body['status'] == 'PENDING_CBP'
    assert body['mq_send_state'] == 'SENT'
    control = body['control_id']
    kn = body['kn_number']
    assert kn == ''
    outbox = Path(os.environ['MQ_OUTBOX_DIR']) / f'{control}.edi'
    assert outbox.exists()
    assert 'KLEAR1' in outbox.read_text()

    applied = client.post('/api/extract/callback', headers={'X-Callback-Secret': 'test-secret'}, json={
        'message': _response_for(control, kn),
        'correlation_id': control,
    })
    assert applied.status_code == 200, applied.text
    assert applied.json()['status'] == 'APPROVED'

    again = client.post('/api/extract/callback', headers={'X-Callback-Secret': 'test-secret'}, json={
        'message': _response_for(control, kn),
        'correlation_id': control,
    })
    assert again.json()['duplicate'] is True

    with SessionLocal() as session:
        history = session.query(FirmsFacilityHistory).filter_by(firms_code='E364').all()
        assert len(history) == 1
        assert history[0].change_type == 'new'

    csv_res = client.get(f'/api/extract/requests/{body["id"]}/csv', headers={'X-Demo-User': 'operator'})
    assert csv_res.status_code == 200
    assert 'PORT LIBERTY - BAYONNE' in csv_res.text
    assert '\r\n' in csv_res.text
    assert csv_res.text.count('\r\n') == 2


def test_unknown_control_is_kept_for_admin(client):
    missing = client.post('/api/extract/callback', headers={'X-Callback-Secret': 'test-secret'}, json={
        'message': _response_for('ZZZZZZZZZZZZZZZZZZZZ', 'KN-MISSING'),
        'correlation_id': 'ZZZZZZZZZZZZZZZZZZZZ',
    })
    assert missing.status_code == 404
    vault = client.get('/api/extract/vault', headers={'X-Demo-User': 'admin'})
    assert vault.json()['orphans']
    operator = client.get('/api/extract/vault', headers={'X-Demo-User': 'operator'})
    assert operator.json()['orphans'] == []


def test_callback_secret_required(client):
    open_call = client.post('/api/extract/callback', json={'message': 'A'.ljust(80)})
    assert open_call.status_code == 401
