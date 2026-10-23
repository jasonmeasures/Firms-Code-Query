"""Shared API fixtures. Environment must be set before the app is imported."""

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent

os.environ.setdefault('APP_ENV', 'dev')
os.environ.setdefault('KN_SITE_CODE', '2809')
os.environ.setdefault('KN_SENDER_ID', 'S1F')
os.environ.setdefault('KN_TRANSMITTER_PASSWORD', 'KLEAR1')
os.environ.setdefault('KN_PROCESSING_PORT', '2809')
os.environ.setdefault('KN_FILER_CODE', 'S1F')
os.environ.setdefault('KN_PREPARER_PORT', '2809')
os.environ.setdefault('KN_PREPARER_FILER', 'S1F')
os.environ.setdefault('EXTRACT_CALLBACK_SECRET', 'test-secret')
os.environ.setdefault('MQ_MODE', 'mock')
os.environ.setdefault('DATABASE_URL', 'sqlite:///' + str(ROOT / 'test_extract.db'))
os.environ.setdefault('MQ_OUTBOX_DIR', str(ROOT / 'mq_outbox'))
os.environ.setdefault('EXTRACT_MAX_BODY_RECORDS', '50')

from fastapi.testclient import TestClient  # noqa: E402

from app.db import engine, init_db  # noqa: E402
from app.models import Base  # noqa: E402
from main import app  # noqa: E402

PORT_LIBERTY = """\
[A2809S1F      101826     FO                                KN-PLACEHOLDER       ]
[B  2809S1FFO                                               CONTROLCONTROLCONTRO ]
[F2114601E364A03PORT LIBERTY - BAYONNE             101726                        ]
[F311302 PORT JERSEY BLVD               JERSEY CITY                        NJ    ]
[F411073054569US                                                                 ]
[Y  2809S1FFO                                                                    ]
[Z2809S1F      101826                                                            ]
"""


def fo_for(control: str, kn: str = '', *extra_f211: str) -> str:
    text = PORT_LIBERTY.replace('CONTROLCONTROLCONTRO', control)
    text = text.replace('KN-PLACEHOLDER       ', kn.ljust(21))
    if extra_f211:
        lines = text.strip().split('\n')
        insert_at = next(i for i, line in enumerate(lines) if line.startswith('[Y'))
        for record in extra_f211:
            lines.insert(insert_at, record if record.startswith('[') else f'[{record}]')
            insert_at += 1
        text = '\n'.join(lines) + '\n'
    return text


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    init_db()
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def admin(client: TestClient, **kwargs):
    kwargs.setdefault('headers', {})['X-Demo-User'] = 'admin'
    return kwargs


def operator(client: TestClient, **kwargs):
    kwargs.setdefault('headers', {})['X-Demo-User'] = 'operator'
    return kwargs
