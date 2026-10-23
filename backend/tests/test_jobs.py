"""District sweep and chunked list jobs."""

from app.db import SessionLocal
from app.models import RefDistrictPort


def test_sweep_requires_f101(client):
    res = client.post('/api/extract/queries', headers={'X-Demo-User': 'admin'}, json={
        'file_code': 'F111', 'query_type': 'ALL_DISTRICT', 'params': {},
    })
    assert res.status_code == 409
    assert 'district' in res.json()['detail'].lower()


def test_district_sweep_creates_one_request_per_district(client):
    with SessionLocal() as session:
        session.add(RefDistrictPort(code='4601', name='NEW YORK'))
        session.add(RefDistrictPort(code='4602', name='NEWARK'))
        session.add(RefDistrictPort(code='1001', name='BOSTON'))
        session.commit()
    res = client.post('/api/extract/queries', headers={'X-Demo-User': 'admin'}, json={
        'file_code': 'F111', 'query_type': 'ALL_DISTRICT', 'params': {'begin_date': '010100'},
    })
    assert res.status_code == 200, res.text
    job = res.json()['job']
    assert job['total'] == 2
    assert job['pending'] == 2
    districts = sorted(item['params']['district'] for item in job['requests'])
    assert districts == ['10', '46']
    edi = client.get(f"/api/extract/requests/{job['requests'][0]['id']}", headers={'X-Demo-User': 'admin'}).json()['edi']
    assert edi.split('\n')[2].startswith('F111')


def test_list_over_cap_becomes_a_job(client, monkeypatch):
    monkeypatch.setenv('EXTRACT_MAX_BODY_RECORDS', '2')
    codes = 'E364 E365 E366 E367 E368'
    res = client.post('/api/extract/queries', headers={'X-Demo-User': 'operator'}, json={
        'file_code': 'F111', 'query_type': 'LIST', 'params': {'codes': codes},
    })
    assert res.status_code == 200, res.text
    job = res.json()['job']
    assert job is not None
    assert job['query_type'] == 'LIST'
    assert job['total'] == 3
    assert job['pending'] == 3


def test_job_progress_after_one_response(client):
    with SessionLocal() as session:
        session.add(RefDistrictPort(code='4601', name='NEW YORK'))
        session.add(RefDistrictPort(code='1001', name='BOSTON'))
        session.commit()
    created = client.post('/api/extract/queries', headers={'X-Demo-User': 'admin'}, json={
        'file_code': 'F111', 'query_type': 'ALL_DISTRICT', 'params': {},
    }).json()
    first = created['job']['requests'][0]
    from tests.conftest import fo_for
    applied = client.post('/api/extract/callback', headers={'X-Callback-Secret': 'test-secret'}, json={
        'message': fo_for(first['control_id']),
        'correlation_id': first['control_id'],
    })
    assert applied.status_code == 200
    job = client.get(f"/api/extract/jobs/{created['job']['id']}", headers={'X-Demo-User': 'admin'}).json()
    assert job['approved'] == 1
    assert job['pending'] == 1
    assert job['status'] == 'PENDING_CBP'


def _fail_mq(monkeypatch, fail_first=1):
    from app.mq.outbound import ExtractOutbound, MqError
    real = ExtractOutbound.put
    calls = {'n': 0}

    def put(self, **kw):
        calls['n'] += 1
        if calls['n'] <= fail_first:
            raise MqError('queue manager down')
        return real(self, **kw)
    monkeypatch.setattr(ExtractOutbound, 'put', put)


def test_chunked_list_survives_a_failed_send_and_can_resume(client, monkeypatch):
    monkeypatch.setenv('EXTRACT_MAX_BODY_RECORDS', '2')
    _fail_mq(monkeypatch)
    res = client.post('/api/extract/queries', headers={'X-Demo-User': 'operator'}, json={
        'file_code': 'F111', 'query_type': 'LIST', 'params': {'codes': 'E364 E365 E366 E367 E368'},
    })
    assert res.status_code == 200, res.text
    job = res.json()['job']
    assert job['total'] == 3
    assert job['failed'] == 1
    assert job['pending'] == 2
    assert all(r['mq_send_state'] in {'FAILED', 'SENT'} for r in job['requests'])
    resumed = client.post(f"/api/extract/jobs/{job['id']}/resume", headers={'X-Demo-User': 'admin'})
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()['failed'] == 0
    assert resumed.json()['pending'] == 3


def test_resume_sends_chunks_that_never_left_draft(client, monkeypatch):
    monkeypatch.setenv('EXTRACT_MAX_BODY_RECORDS', '2')
    from app.models import ExtractRequest
    created = client.post('/api/extract/queries', headers={'X-Demo-User': 'operator'}, json={
        'file_code': 'F111', 'query_type': 'LIST', 'params': {'codes': 'E364 E365 E366'},
    }).json()['job']
    with SessionLocal() as session:
        row = session.get(ExtractRequest, created['requests'][1]['id'])
        row.mq_send_state, row.status, row.submitted_at = None, 'DRAFT', None
        session.commit()
    resumed = client.post(f"/api/extract/jobs/{created['id']}/resume", headers={'X-Demo-User': 'admin'}).json()
    assert resumed['pending'] == 2
    assert all(r['mq_send_state'] == 'SENT' for r in resumed['requests'])
