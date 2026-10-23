"""Acceptance paths from the build prompt and UC-01 through UC-06."""

from app.db import SessionLocal
from app.models import FirmsFacility, FirmsFacilityHistory, RefDistrictPort
from app.mq.outbound import ExtractOutbound, MqError
from tests.conftest import fo_for


def test_acceptance_e364_port_liberty_card(client):
    created = client.post('/api/extract/queries', headers={'X-Demo-User': 'operator'}, json={
        'file_code': 'F111', 'query_type': 'CODE', 'params': {'firms_code': 'E364'},
    })
    assert created.status_code == 200, created.text
    body = created.json()['request']
    applied = client.post('/api/extract/callback', headers={'X-Callback-Secret': 'test-secret'}, json={
        'message': fo_for(body['control_id'], body['kn_number']),
        'correlation_id': body['control_id'],
    })
    assert applied.json()['status'] == 'APPROVED'
    detail = client.get(f"/api/extract/requests/{body['id']}", headers={'X-Demo-User': 'operator'}).json()
    rows = detail['response']['parsed']['rows']
    assert rows[0]['facility_name'] == 'PORT LIBERTY - BAYONNE'
    assert rows[0]['status_label'] == 'Active'
    assert rows[0]['facility_type'] == 'Pier'
    csv_text = client.get(f"/api/extract/requests/{body['id']}/csv", headers={'X-Demo-User': 'operator'}).text
    assert 'PORT LIBERTY - BAYONNE' in csv_text
    assert 'Active' in csv_text


def test_acceptance_list_and_csv(client):
    blocked = client.post('/api/extract/queries', headers={'X-Demo-User': 'operator'}, json={
        'file_code': 'F111', 'query_type': 'LIST', 'params': {'codes': 'E364, e364; NO; AB'},
    })
    assert blocked.status_code == 422
    assert 'NO' in blocked.json()['detail'][0]
    created = client.post('/api/extract/queries', headers={'X-Demo-User': 'operator'}, json={
        'file_code': 'F111', 'query_type': 'LIST', 'params': {'codes': 'E364 E999'},
    })
    body = created.json()['request']
    extra = 'F2114601E999A01OTHER FACILITY'.ljust(80)
    applied = client.post('/api/extract/callback', headers={'X-Callback-Secret': 'test-secret'}, json={
        'message': fo_for(body['control_id'], '', extra),
        'correlation_id': body['control_id'],
    })
    assert applied.status_code == 200
    csv_text = client.get(f"/api/extract/requests/{body['id']}/csv", headers={'X-Demo-User': 'operator'}).text
    assert csv_text.count('\r\n') == 3
    assert 'E364' in csv_text
    assert 'E999' in csv_text


def test_acceptance_whole_file_updates_change_log(client):
    operator = client.post('/api/extract/queries', headers={'X-Demo-User': 'operator'}, json={
        'file_code': 'F111', 'query_type': 'ALL_DATE', 'params': {'begin_date': '010100'},
    })
    assert operator.status_code == 403
    created = client.post('/api/extract/queries', headers={'X-Demo-User': 'admin'}, json={
        'file_code': 'F111', 'query_type': 'ALL_DATE', 'params': {'begin_date': '010100'},
    })
    assert created.status_code == 200, created.text
    control = created.json()['request']['control_id']
    extra = 'F2114601E999D04OLD WAREHOUSE'.ljust(80)
    client.post('/api/extract/callback', headers={'X-Callback-Secret': 'test-secret'}, json={
        'message': fo_for(control, '', extra),
        'correlation_id': control,
    })
    summary = client.get('/api/extract/reference/summary', headers={'X-Demo-User': 'admin'}).json()
    firms = next(item for item in summary['files'] if item['file_code'] == 'F111')
    assert firms['count'] == 2
    changes = client.get('/api/extract/reference/firms/changes', headers={'X-Demo-User': 'admin'}).json()['changes']
    assert {item['change_type'] for item in changes} == {'new'}
    assert {item['firms_code'] for item in changes} == {'E364', 'E999'}
    with SessionLocal() as session:
        assert session.get(FirmsFacility, 'E999').status == 'D'
        assert session.query(FirmsFacilityHistory).count() == 2


def test_acceptance_admin_find_retry_and_dead_letter(client, monkeypatch):
    calls = {'n': 0}
    real = ExtractOutbound.put

    def flaky(self, **kwargs):
        calls['n'] += 1
        if calls['n'] == 1:
            raise MqError('queue down')
        return real(self, **kwargs)

    monkeypatch.setattr(ExtractOutbound, 'put', flaky)
    created = client.post('/api/extract/queries', headers={'X-Demo-User': 'admin'}, json={
        'file_code': 'F111', 'query_type': 'CODE', 'params': {'firms_code': 'E364'},
        'control_id': 'FINDMECONTROLID12345',
    })
    assert created.status_code == 503
    found = client.get('/api/extract/requests?q=FINDMECONTROLID12345', headers={'X-Demo-User': 'admin'}).json()
    assert found['requests']
    request_id = found['requests'][0]['id']
    vault = client.get('/api/extract/vault', headers={'X-Demo-User': 'admin'}).json()
    assert vault['dead_letters']
    assert vault['dead_letters'][0]['control_id'] == 'FINDMECONTROLID12345'
    operator_vault = client.get('/api/extract/vault', headers={'X-Demo-User': 'operator'}).json()
    assert operator_vault['dead_letters'] == []
    retried = client.post(f'/api/extract/requests/{request_id}/retry', headers={'X-Demo-User': 'admin'})
    assert retried.status_code == 200, retried.text
    assert retried.json()['mq_send_state'] == 'SENT'
    cleared = client.get('/api/extract/vault', headers={'X-Demo-User': 'admin'}).json()
    assert cleared['dead_letters'] == []
    client.post('/api/extract/callback', headers={'X-Callback-Secret': 'test-secret'}, json={
        'message': fo_for('ZZZZZZZZZZZZZZZZZZZZ', 'KN-MISSING'),
        'correlation_id': 'ZZZZZZZZZZZZZZZZZZZZ',
    })
    orphans = client.get('/api/extract/vault', headers={'X-Demo-User': 'admin'}).json()['orphans']
    assert orphans
    assert client.get('/api/extract/vault', headers={'X-Demo-User': 'operator'}).json()['orphans'] == []


def test_acceptance_f101_then_sweep(client):
    created = client.post('/api/extract/queries', headers={'X-Demo-User': 'admin'}, json={
        'file_code': 'F101', 'query_type': 'FULL', 'params': {},
    })
    control = created.json()['request']['control_id']
    f101 = (
        'F10104601NEW YORK SEAPORT         201 VARICK STREET                   A1001    '
        '\n'
        'F10101001BOSTON                     10 CAUSEWAY                        A1001    '
    )
    # pad each line to 80
    records = '\n'.join(line.ljust(80) for line in f101.split('\n') if line.strip())
    message = (
        f"[A2809S1F      101826     FO                                {'':<21}]\n"
        f"[B  2809S1FFO                                               {control} ]\n"
        + '\n'.join(f'[{line}]' for line in records.split('\n'))
        + '\n[Y  2809S1FFO                                                                    ]\n'
        + '[Z2809S1F      101826                                                            ]\n'
    )
    applied = client.post('/api/extract/callback', headers={'X-Callback-Secret': 'test-secret'}, json={
        'message': message, 'correlation_id': control,
    })
    assert applied.status_code == 200, applied.text
    with SessionLocal() as session:
        codes = [row.code for row in session.query(RefDistrictPort).all()]
    assert len(codes) >= 2
    sweep = client.post('/api/extract/queries', headers={'X-Demo-User': 'admin'}, json={
        'file_code': 'F111', 'query_type': 'ALL_DISTRICT', 'params': {},
    })
    assert sweep.status_code == 200, sweep.text
    assert sweep.json()['job']['total'] >= 2
