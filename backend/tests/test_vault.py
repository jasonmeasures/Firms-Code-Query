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
    assert body['all_80'] is True
    assert any(rec['id'] == 'F111' for rec in body['records'])
    after = client.get('/api/extract/vault', headers={'X-Demo-User': 'operator'}).json()['filings']
    assert len(after) == len(before)


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
