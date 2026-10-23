"""Authentication must fail closed unless APP_ENV is explicitly a dev value."""

import pytest

from app.config import get_settings


def test_app_env_defaults_to_prod(monkeypatch):
    monkeypatch.delenv('APP_ENV', raising=False)
    monkeypatch.setattr('app.config.load_dotenv', lambda *a, **k: None, raising=False)
    s = get_settings()
    assert s.app_env == 'prod' and not s.is_dev


@pytest.mark.parametrize('value', ['', 'staging', 'production', 'prod'])
def test_demo_header_refused_outside_dev(client, monkeypatch, value):
    monkeypatch.setenv('APP_ENV', value)
    res = client.get('/api/extract/me', headers={'X-Demo-User': 'admin'})
    assert res.status_code == 401
    assert client.get('/api/extract/me').status_code == 401


def test_demo_header_works_in_dev(client):
    res = client.get('/api/extract/me', headers={'X-Demo-User': 'admin'})
    assert res.status_code == 200 and res.json()['role'] == 'ADMIN'


def test_dev_response_hidden_outside_dev(client, monkeypatch):
    monkeypatch.setenv('APP_ENV', 'staging')
    res = client.post('/api/extract/requests/x/dev-response', headers={'X-Demo-User': 'admin'}, json={'message': 'x'})
    assert res.status_code in {401, 404}


def test_dockerignore_keeps_secrets_out_of_the_image():
    from pathlib import Path
    lines = (Path(__file__).resolve().parents[1] / '.dockerignore').read_text().split()
    for needed in ('.env', '.venv/', '*.db', 'mq_outbox/'):
        assert needed in lines
