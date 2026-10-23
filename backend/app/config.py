"""Transmission identity and queue settings.

The communication password is read from the environment and is never
hard-coded. Site, sender, port and filer have dev defaults so a local
copy of .env.example runs. Production must set every value.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and value.strip():
            return value.strip()
    return default


@dataclass(frozen=True)
class Settings:
    app_env: str
    site_code: str
    sender_id: str
    password: str
    processing_port: str
    filer_code: str
    preparer_port: str
    preparer_filer: str
    database_url: str
    mq_mode: str
    mq_outbox_dir: str
    mq_queue_manager: str
    mq_channel: str
    mq_host: str
    mq_port: str
    callback_secret: str
    outbound_queue: str
    inbound_queue: str
    max_body_records: int

    @property
    def is_dev(self) -> bool:
        """Demo sign-in and dev-only routes need an explicit APP_ENV=dev (or local/test)."""
        return self.app_env in {"dev", "local", "test"}

    @property
    def transmitter_ready(self) -> bool:
        return all([
            len(self.site_code) == 4,
            len(self.sender_id) == 3,
            len(self.password) == 6,
            len(self.processing_port) == 4,
            len(self.filer_code) == 3,
            len(self.preparer_port) == 4,
            len(self.preparer_filer) == 3,
        ])


def get_settings() -> Settings:
    root = Path(__file__).resolve().parents[1]
    port = _env("KN_PROCESSING_PORT", "KN_PORT", default="2809").upper()
    filer = _env("KN_FILER_CODE", "KN_FILER", default="S1F").upper()
    raw_max = _env("EXTRACT_MAX_BODY_RECORDS", "MAX_QUERY_RECORDS_PER_BLOCK", default="50")
    try:
        max_body = max(1, int(raw_max))
    except ValueError:
        max_body = 50
    return Settings(
        app_env=_env("APP_ENV", default="prod").lower(),
        site_code=_env("KN_SITE_CODE", default="2809").upper(),
        sender_id=_env("KN_SENDER_ID", default="S1F").upper(),
        password=_env("KN_TRANSMITTER_PASSWORD").upper(),
        processing_port=port,
        filer_code=filer,
        preparer_port=_env("KN_PREPARER_PORT", default=port).upper(),
        preparer_filer=_env("KN_PREPARER_FILER", default=filer).upper(),
        database_url=_env("DATABASE_URL", default=f"sqlite:///{root / 'extract.db'}"),
        mq_mode=_env("MQ_MODE", default="mock"),
        mq_outbox_dir=_env("MQ_OUTBOX_DIR", default=str(root / "mq_outbox")),
        mq_queue_manager=_env("MQ_QUEUE_MANAGER"),
        mq_channel=_env("MQ_CHANNEL"),
        mq_host=_env("MQ_HOST"),
        mq_port=_env("MQ_PORT", default="1414"),
        callback_secret=_env("EXTRACT_CALLBACK_SECRET", "MQ_CALLBACK_SECRET"),
        outbound_queue=_env("EXTRACT_OUTBOUND_QUEUE", "MQ_OUTBOUND_QUEUE", default="CBP.OUT.EXTRACT.QUERY"),
        inbound_queue=_env("EXTRACT_INBOUND_QUEUE", "MQ_INBOUND_QUEUE", default="CBP.IN.EXTRACT.RESPONSE"),
        max_body_records=max_body,
    )
