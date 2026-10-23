"""Phase 2 FIRMS checks for AE 20, SE11, X10, and SE20 CES/LOC."""

from app.db import SessionLocal
from app.models import FirmsFacility
from app.services.entry import ENTRY_SOURCES, validate_firms_for_entry


def _seed(**overrides):
    row = FirmsFacility(
        firms_code=overrides.get('firms_code', 'E364'),
        district_port='4601',
        status=overrides.get('status', 'A'),
        facility_type=overrides.get('facility_type', '03'),
        name=overrides.get('name', 'PORT LIBERTY - BAYONNE'),
    )
    with SessionLocal() as session:
        session.add(row)
        session.commit()


def test_entry_sources_are_the_prompt_list(client):
    res = client.get('/api/extract/reference/firms/entry-sources', headers={'X-Demo-User': 'operator'})
    assert set(item['id'] for item in res.json()['sources']) == set(ENTRY_SOURCES)


def test_active_code_is_allowed_on_every_source(client):
    _seed()
    for source in ENTRY_SOURCES:
        res = client.post('/api/extract/reference/firms/validate', headers={'X-Demo-User': 'operator'}, json={
            'locations': [{'source': source, 'firms_code': 'e364'}],
        })
        body = res.json()['results'][0]
        assert body['allowed'] is True
        assert body['code'] == 'OK'
        assert body['severity'] == 'ok'


def test_unknown_and_invalid_are_blocked(client):
    missing = client.post('/api/extract/reference/firms/validate', headers={'X-Demo-User': 'operator'}, json={
        'locations': [{'source': 'SE11', 'firms_code': 'ZZZZ'}],
    }).json()['results'][0]
    assert missing['allowed'] is False
    assert missing['code'] == 'NOT_ON_FILE'
    bad = client.post('/api/extract/reference/firms/validate', headers={'X-Demo-User': 'operator'}, json={
        'locations': [{'source': 'X10', 'firms_code': 'E36'}],
    }).json()['results'][0]
    assert bad['code'] == 'INVALID'


def test_deactivated_is_blocked(client):
    _seed(firms_code='DEAD', status='D', facility_type='04')
    res = client.post('/api/extract/reference/firms/validate', headers={'X-Demo-User': 'operator'}, json={
        'locations': [{'source': 'AE20', 'firms_code': 'DEAD'}],
    })
    body = res.json()['results'][0]
    assert body['allowed'] is False
    assert body['code'] == 'DEACTIVATED'


def test_types_07_and_08_warn_but_do_not_block(client):
    _seed(firms_code='DATA', facility_type='07', name='DATA SITE')
    _seed(firms_code='ADMN', facility_type='08', name='CBP ADMIN')
    res = client.post('/api/extract/reference/firms/validate', headers={'X-Demo-User': 'operator'}, json={
        'locations': [
            {'source': 'SE20_CES', 'firms_code': 'DATA'},
            {'source': 'SE20_LOC', 'firms_code': 'ADMN'},
        ],
    }).json()
    assert res['ok'] is True
    assert [item['code'] for item in res['warnings']] == ['ENTRY_TYPE', 'ENTRY_TYPE']
    assert all(item['allowed'] for item in res['results'])


def test_service_rejects_unknown_source():
    with SessionLocal() as session:
        result = validate_firms_for_entry(session, 'E364', 'NOPE')
    assert result['code'] == 'UNKNOWN_SOURCE'
    assert result['allowed'] is False
