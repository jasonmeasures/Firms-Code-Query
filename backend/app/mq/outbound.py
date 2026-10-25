"""Mock outbox, with a live pymqi path left for Engine's transmitter.

Queues are Extract Reference queues, not the 5106 queues. Delivery flags match
the 5106 outbound adapter: persistent, priority 5, TTL one day. The control ID
is the correlation id.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.config import get_settings
from app.edi.envelope import bracket

TTL_MS = 86_400_000
PRIORITY = 5
DELIVERY = 'PERSISTENT'


class MqError(RuntimeError):
    pass


class ExtractOutbound:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.outbox = Path(settings.mq_outbox_dir)
        if not self.outbox.is_absolute():
            self.outbox = Path(__file__).resolve().parents[2] / self.outbox

    def put(self, *, edi: str, control_id: str, request_id: str, file_code: str) -> dict:
        settings = self.settings
        envelope = {
            'queue': settings.outbound_queue,
            'inbound_queue': settings.inbound_queue,
            'jms_type': f'CBP_EXTRACT_{file_code}',
            'jms_correlation_id': control_id,
            'delivery': DELIVERY,
            'ttl_ms': TTL_MS,
            'priority': PRIORITY,
            'request_id': request_id,
            'file_code': file_code,
            'edi': bracket(edi),
        }
        if settings.mq_mode == 'live':
            return self._put_live(envelope)
        return self._put_mock(envelope)

    def _put_mock(self, envelope: dict) -> dict:
        self.outbox.mkdir(parents=True, exist_ok=True)
        path = self.outbox / f"{envelope['jms_correlation_id']}.json"
        path.write_text(json.dumps(envelope, indent=2), encoding='utf-8')
        edi_path = self.outbox / f"{envelope['jms_correlation_id']}.edi"
        edi_path.write_text(envelope['edi'], encoding='utf-8')
        return {'transport': 'mock', 'path': str(path), 'queue': envelope['queue']}

    def _put_live(self, envelope: dict) -> dict:
        settings = self.settings
        try:
            import pymqi  # type: ignore
        except ImportError as exc:
            raise MqError('MQ_MODE=live needs pymqi and the Engine transmitter') from exc
        if not (settings.mq_queue_manager and settings.mq_channel and settings.mq_host):
            raise MqError('Live MQ needs MQ_QUEUE_MANAGER, MQ_CHANNEL, and MQ_HOST')
        conn = pymqi.connect(
            settings.mq_queue_manager,
            settings.mq_channel,
            f'{settings.mq_host}({settings.mq_port})',
        )
        try:
            queue = pymqi.Queue(conn, settings.outbound_queue)
            md = pymqi.MD()
            md.Persistence = pymqi.CMQC.MQPER_PERSISTENT
            md.Priority = PRIORITY
            md.CorrelId = envelope['jms_correlation_id'].encode('ascii').ljust(24)
            md.Expiry = TTL_MS // 100
            queue.put(envelope['edi'].encode('ascii'), md)
            queue.close()
        finally:
            conn.disconnect()
        return {'transport': 'live', 'queue': settings.outbound_queue}

    def status(self) -> dict:
        settings = self.settings
        writable = True
        detail = 'Mock outbox is writable'
        if settings.mq_mode != 'live':
            try:
                self.outbox.mkdir(parents=True, exist_ok=True)
                probe = self.outbox / '.write_check'
                probe.write_text('ok', encoding='utf-8')
                probe.unlink()
            except OSError as exc:
                writable = False
                detail = str(exc)
        else:
            detail = 'Live mode is configured' if settings.mq_host else 'Live mode is missing a host'
            writable = bool(settings.mq_host and settings.mq_queue_manager and settings.mq_channel)
        files = list(self.outbox.glob('*.edi')) if self.outbox.exists() else []
        return {
            'mode': settings.mq_mode,
            'outbound_queue': settings.outbound_queue,
            'inbound_queue': settings.inbound_queue,
            'queue_manager': settings.mq_queue_manager,
            'channel': settings.mq_channel,
            'host': settings.mq_host,
            'port': settings.mq_port,
            'reachable': writable,
            'detail': detail,
            'priority': PRIORITY,
            'ttl_ms': TTL_MS,
            'outbox_dir': str(self.outbox),
            'outbox_count': len(files),
        }
