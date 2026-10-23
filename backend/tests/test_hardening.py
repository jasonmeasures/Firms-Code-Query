"""Password at rest, startup checks, DDL single source, and the reference sink seam."""

from pathlib import Path

from app.config import DEV_CALLBACK_SECRET, DEV_PASSWORD, Settings, get_settings, startup_problems
from app.db import SessionLocal
from app.migrations.generate_ddl import render
from app.models import ExtractRequest, RefCountry


def _submit(client):
    res = client.post('/api/extract/queries', headers={'X-Demo-User': 'operator'}, json={
        'file_code': 'F111', 'query_type': 'CODE', 'params': {'firms_code': 'E364'},
    })
    assert res.status_code == 200, res.text
    return res.json()['request']


def test_password_is_not_stored_but_is_sent(client):
    req = _submit(client)
    with SessionLocal() as session:
        stored = session.get(ExtractRequest, req['id']).edi_text
    assert stored.split('\n')[0][8:14] == ' ' * 6
    outbox = Path(get_settings().mq_outbox_dir) / f"{req['control_id']}.edi"
    sent = outbox.read_text()
    assert get_settings().password in sent.split('\n')[0]


def test_retry_resends_the_real_password(client, monkeypatch):
    from app.mq.outbound import ExtractOutbound, MqError
    real = ExtractOutbound.put
    state = {'fail': True}

    def put(self, **kw):
        if state['fail']:
            raise MqError('down')
        captured.append(kw['edi'])
        return real(self, **kw)
    captured: list[str] = []
    monkeypatch.setattr(ExtractOutbound, 'put', put)
    res = client.post('/api/extract/queries', headers={'X-Demo-User': 'admin'}, json={
        'file_code': 'F111', 'query_type': 'CODE', 'params': {'firms_code': 'E364'},
    })
    assert res.status_code == 503
    with SessionLocal() as session:
        row = session.query(ExtractRequest).one()
        rid = row.id
    state['fail'] = False
    ok = client.post(f'/api/extract/requests/{rid}/retry', headers={'X-Demo-User': 'admin'})
    assert ok.status_code == 200, ok.text
    assert get_settings().password in captured[0].split('\n')[0]


def test_callback_secret_compare_rejects_wrong_and_missing(client):
    for headers in ({}, {'X-Callback-Secret': 'nope'}):
        res = client.post('/api/extract/callback', headers=headers, json={'message': 'x'})
        assert res.status_code == 401


def _settings(**over):
    base = dict(get_settings().__dict__)
    base.update(over)
    return Settings(**base)


def test_non_dev_refuses_dev_defaults():
    problems = startup_problems(_settings(
        app_env='prod', password=DEV_PASSWORD, callback_secret=DEV_CALLBACK_SECRET, cors_origins=('*',),
    ))
    assert len(problems) == 3


def test_non_dev_with_real_values_starts():
    assert startup_problems(_settings(
        app_env='prod', password='ZX81QA', callback_secret='long-random-value', cors_origins=('https://x.example',),
    )) == []


def test_dev_skips_startup_checks():
    assert startup_problems(_settings(app_env='dev', password=DEV_PASSWORD)) == []


def test_cors_has_no_origins_by_default():
    assert get_settings().cors_origins == ()


def test_committed_ddl_matches_the_models():
    path = Path(__file__).resolve().parents[1] / 'migrations' / '001_extract_reference.sql'
    assert path.read_text() == render(), 'regenerate: python -m app.migrations.generate_ddl > migrations/001_extract_reference.sql'


def test_workflow_writes_through_the_sink(client, monkeypatch):
    seen = []

    class Spy:
        def apply(self, session, parsed, control_id):
            seen.append(control_id)
    monkeypatch.setattr('app.services.workflow.get_reference_sink', lambda: Spy())
    req = _submit(client)
    from tests.conftest import fo_for
    res = client.post('/api/extract/callback', headers={'X-Callback-Secret': 'test-secret'}, json={
        'message': fo_for(req['control_id']), 'correlation_id': req['control_id'],
    })
    assert res.status_code == 200, res.text
    assert seen == [req['control_id']]
    with SessionLocal() as session:
        assert session.query(RefCountry).count() == 0
