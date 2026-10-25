"""EDI vault add / edit, matching the 5106 lock and password rules."""

from tests.conftest import fo_for

SAMPLE = """\
[A2809S1FKLEAR1101826     FQ                                KN-09PC-11:EE        ]
[B  2809S1FFQ                                  2809S1F  1   2TGFEC9WQDMLKMFSFASI ]
[F111E364                                                                        ]
[Y  2809S1FFQ                                                                    ]
[Z2809S1F      101826                                                            ]
"""


def test_add_and_edit_edi(client):
    created = client.post('/api/extract/vault', headers={'X-Demo-User': 'operator'}, json={'edi': SAMPLE})
    assert created.status_code == 200, created.text
    item = created.json()
    assert item['file_code'] == 'F111'
    assert item['status'] == 'DRAFT'
    assert item['editable'] is True
    assert 'KLEAR1' not in item['edi']
    assert any(rec['id'] == 'F111' for rec in item['records'])

    listed = client.get('/api/extract/vault', headers={'X-Demo-User': 'operator'}).json()
    assert any(row['id'] == item['id'] for row in listed['filings'])

    edited = SAMPLE.replace('E364', 'E999')
    saved = client.put(f"/api/extract/vault/{item['id']}", headers={'X-Demo-User': 'operator'}, json={'edi': edited})
    assert saved.status_code == 200, saved.text
    assert 'E999' in saved.json()['edi']


def test_sent_edi_is_read_only(client):
    created = client.post('/api/extract/queries', headers={'X-Demo-User': 'operator'}, json={
        'file_code': 'F111', 'query_type': 'CODE', 'params': {'firms_code': 'E364'},
    }).json()['request']
    item = client.get(f"/api/extract/vault/{created['id']}", headers={'X-Demo-User': 'operator'}).json()
    assert item['editable'] is False
    blocked = client.put(f"/api/extract/vault/{created['id']}", headers={'X-Demo-User': 'operator'}, json={'edi': SAMPLE})
    assert blocked.status_code == 409


def test_vault_cannot_change_password_or_control(client):
    created = client.post('/api/extract/vault', headers={'X-Demo-User': 'admin'}, json={'edi': SAMPLE}).json()
    tampered = SAMPLE.replace('KLEAR1', 'SECRET').replace('2TGFEC9WQDMLKMFSFASI', 'XXXXXXXXXXXXXXXXXXXX')
    res = client.put(f"/api/extract/vault/{created['id']}", headers={'X-Demo-User': 'admin'}, json={'edi': tampered})
    assert res.status_code == 422


def test_operator_cannot_see_admin_unmatched(client):
    client.post('/api/extract/callback', headers={'X-Callback-Secret': 'test-secret'}, json={
        'message': fo_for('ZZZZZZZZZZZZZZZZZZZZ'),
        'correlation_id': 'ZZZZZZZZZZZZZZZZZZZZ',
    })
    admin = client.get('/api/extract/vault', headers={'X-Demo-User': 'admin'}).json()
    assert admin['orphans']
    operator = client.get('/api/extract/vault', headers={'X-Demo-User': 'operator'}).json()
    assert operator['orphans'] == []


def test_mq_test_is_admin_only(client):
    assert client.post('/api/extract/mq/test', headers={'X-Demo-User': 'operator'}, json={}).status_code == 403
    res = client.post('/api/extract/mq/test', headers={'X-Demo-User': 'admin'}, json={})
    assert res.status_code == 200
    assert res.json()['status']['outbound_queue'] == 'CBP.OUT.EXTRACT.QUERY'


def test_check_edi_does_not_save(client):
    before = client.get('/api/extract/vault', headers={'X-Demo-User': 'operator'}).json()['filings']
    empty = client.post('/api/extract/vault/check', headers={'X-Demo-User': 'operator'}, json={'edi': ''})
    assert empty.status_code == 200
    assert empty.json()['ok'] is False
    good = client.post('/api/extract/vault/check', headers={'X-Demo-User': 'operator'}, json={'edi': SAMPLE})
    assert good.status_code == 200, good.text
    body = good.json()
    assert body['ok'] is True
    assert body['rule_errors'] == []
    assert body['all_80'] is True
    assert any(rec['id'] == 'F111' for rec in body['records'])
    after = client.get('/api/extract/vault', headers={'X-Demo-User': 'operator'}).json()['filings']
    assert len(after) == len(before)


def test_download_masks_password_and_uses_control_filename(client):
    created = client.post('/api/extract/vault', headers={'X-Demo-User': 'operator'}, json={'edi': SAMPLE}).json()
    res = client.get(f"/api/extract/vault/{created['id']}/download", headers={'X-Demo-User': 'operator'})
    assert res.status_code == 200
    assert res.headers['content-type'].startswith('text/plain')
    assert created['filename'] in res.headers.get('content-disposition', '')
    assert 'KLEAR1' not in res.text
    assert 'F111' in res.text
    assert 'E364' in res.text


def test_operator_cannot_download_another_users_edi(client):
    created = client.post('/api/extract/vault', headers={'X-Demo-User': 'admin'}, json={'edi': SAMPLE}).json()
    res = client.get(f"/api/extract/vault/{created['id']}/download", headers={'X-Demo-User': 'operator'})
    assert res.status_code == 404


def test_sent_edi_can_still_be_downloaded(client):
    created = client.post('/api/extract/queries', headers={'X-Demo-User': 'operator'}, json={
        'file_code': 'F111', 'query_type': 'CODE', 'params': {'firms_code': 'E364'},
    }).json()['request']
    res = client.get(f"/api/extract/vault/{created['id']}/download", headers={'X-Demo-User': 'operator'})
    assert res.status_code == 200
    assert created['control_id'] in res.headers.get('content-disposition', '')


def test_check_accepts_full_file_and_f106_modes(client):
    from app.edi.build import f101, f102, f104, f106
    from tests.test_extract_rules import wrap

    for body in (f101(), f102(), f104(), f106(code="AA"), f106(name="DELTA"), f106()):
        res = client.post("/api/extract/vault/check", headers={"X-Demo-User": "admin"}, json={"edi": wrap(body)})
        assert res.status_code == 200, res.text
        assert res.json()["ok"] is True, res.json()
        assert res.json()["rule_errors"] == []


def test_check_accepts_blank_f110_on_hb(client):
    from app.edi.build import f110
    from tests.test_extract_rules import wrap

    ok = client.post("/api/extract/vault/check", headers={"X-Demo-User": "admin"}, json={"edi": wrap(f110(), app="HB")})
    assert ok.json()["ok"] is True
    bad = client.post("/api/extract/vault/check", headers={"X-Demo-User": "admin"}, json={"edi": wrap(f110(), app="FQ")})
    assert bad.json()["ok"] is False
    assert bad.json()["rule_errors"]


def test_scratch_add_warns_on_bad_f106_and_f110(client):
    from tests.test_extract_rules import wrap

    bad_carrier = wrap(("F106" + " " * 35 + "X").ljust(80))
    added = client.post("/api/extract/vault", headers={"X-Demo-User": "operator"}, json={"edi": bad_carrier})
    assert added.status_code == 200, added.text
    assert any("Carrier code" in e for e in added.json()["warnings"])
    bad_hts = wrap(("F110" + " " * 4 + "!!NOT-HTS!").ljust(80), app="HB").replace(
        "2TGFEC9WQDMLKMFSFASI", "HTSCONTROLID00000001"
    )
    hts = client.post("/api/extract/vault", headers={"X-Demo-User": "admin"}, json={"edi": bad_hts})
    assert hts.status_code == 200, hts.text
    assert hts.json()["warnings"]


def test_check_rejects_a_5106_t1_block(client):
    res = client.post('/api/extract/vault/check', headers={'X-Demo-User': 'operator'}, json={
        'edi': 'T1A ACME IMPORTER',
    })
    assert res.status_code == 200
    assert res.json()['ok'] is False
    assert any('F111' in err or 'F101' in err for err in res.json()['errors'])


def test_check_reports_erf_rules_without_blocking_scratch_save(client):
    bad = SAMPLE.replace("F111E364", "F111XXX ")
    checked = client.post("/api/extract/vault/check", headers={"X-Demo-User": "operator"}, json={"edi": bad})
    assert checked.status_code == 200
    assert checked.json()["ok"] is False
    assert checked.json()["errors"] == []
    assert any("FIRMS code" in e for e in checked.json()["rule_errors"])
    added = client.post("/api/extract/vault", headers={"X-Demo-User": "operator"}, json={"edi": bad})
    assert added.status_code == 200, added.text
    assert any("FIRMS code" in e for e in added.json()["warnings"])


def test_sendable_edit_blocks_extract_rule_failures(client, monkeypatch):
    from app.db import SessionLocal
    from app.models import ExtractRequest
    from app.mq.outbound import ExtractOutbound, MqError

    monkeypatch.setattr(ExtractOutbound, "put", lambda self, **_kw: (_ for _ in ()).throw(MqError("down")))
    res = client.post(
        "/api/extract/queries",
        headers={"X-Demo-User": "admin"},
        json={"file_code": "F111", "query_type": "CODE", "params": {"firms_code": "E364"}},
    )
    assert res.status_code == 503
    with SessionLocal() as session:
        row = session.query(ExtractRequest).one()
        rid = row.id
        lines = (row.edi_text or "").split("\n")
    for index, line in enumerate(lines):
        if line.startswith("F111"):
            lines[index] = "F111XXX".ljust(80)
    blocked = client.put(
        f"/api/extract/vault/{rid}",
        headers={"X-Demo-User": "admin"},
        json={"edi": "\n".join(lines)},
    )
    assert blocked.status_code == 422
    assert "FIRMS code" in blocked.text


def test_retry_rejects_edi_that_fails_extract_rules(client, monkeypatch):
    from app.db import SessionLocal
    from app.models import ExtractRequest
    from app.mq.outbound import ExtractOutbound, MqError

    monkeypatch.setattr(ExtractOutbound, "put", lambda self, **_kw: (_ for _ in ()).throw(MqError("down")))
    res = client.post(
        "/api/extract/queries",
        headers={"X-Demo-User": "admin"},
        json={"file_code": "F111", "query_type": "CODE", "params": {"firms_code": "E364"}},
    )
    assert res.status_code == 503
    with SessionLocal() as session:
        row = session.query(ExtractRequest).one()
        rid = row.id
        lines = (row.edi_text or "").split("\n")
        for index, line in enumerate(lines):
            if line.startswith("F111"):
                lines[index] = "F111XXX".ljust(80)
        row.edi_text = "\n".join(lines)
        session.commit()
    retried = client.post(f"/api/extract/requests/{rid}/retry", headers={"X-Demo-User": "admin"})
    assert retried.status_code == 422
    assert "FIRMS code" in retried.text


def test_usage_counts_visible_queries(client):
    client.post('/api/extract/queries', headers={'X-Demo-User': 'operator'}, json={
        'file_code': 'F111', 'query_type': 'CODE', 'params': {'firms_code': 'E364'},
    })
    client.post('/api/extract/vault', headers={'X-Demo-User': 'admin'}, json={'edi': SAMPLE})
    operator = client.get('/api/extract/usage', headers={'X-Demo-User': 'operator'}).json()
    assert operator['total_events'] >= 1
    assert any(row['event_type'] == 'extract_query' for row in operator['events'])
    admin = client.get('/api/extract/usage', headers={'X-Demo-User': 'admin'}).json()
    assert admin['total_events'] >= operator['total_events']
