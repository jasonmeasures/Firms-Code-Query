"""Where conformed reference rows land.

`ReferenceSink` is the seam for the CHB tables. Today `SqlReferenceSink`
upserts into this app's own tables. When the CHB schema is known, add another
sink that maps the same parsed rows onto it and return it from
`get_reference_sink()`; the workflow does not change.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    FirmsFacility,
    FirmsFacilityHistory,
    RefCarrier,
    RefCountry,
    RefDistrictPort,
    RefForeignPort,
    RefHtsUpdate,
    utcnow,
)


class ReferenceSink(Protocol):
    def apply(self, session: Session, parsed, control_id: str) -> None: ...


def apply_rows(session: Session, parsed, control_id: str) -> None:
    now = utcnow()
    for row in parsed.rows:
        kind = row.get('kind')
        if kind == 'facility' and row.get('firms_code'):
            _upsert_facility(session, row, control_id, now)
        elif kind == 'district_port' and row.get('code'):
            _upsert_port(session, row, control_id, now)
        elif kind == 'country' and row.get('iso'):
            _upsert_country(session, row, control_id, now)
        elif kind == 'foreign_port' and row.get('code'):
            _upsert_foreign_port(session, row, control_id, now)
        elif kind == 'carrier' and row.get('carrier_code'):
            _upsert_carrier(session, row, control_id, now)
        elif kind == 'hts_update':
            existing = session.scalar(select(RefHtsUpdate).where(RefHtsUpdate.control_id == control_id))
            if existing is None:
                session.add(RefHtsUpdate(
                    control_id=control_id,
                    update_number=row.get('update_number', ''),
                    from_number=row.get('from_number', ''),
                    to_number=row.get('to_number', ''),
                    narrative=row.get('narrative', '')[:52],
                ))
            else:
                existing.narrative = row.get('narrative', '')[:52]
                existing.update_number = row.get('update_number', '')
                existing.from_number = row.get('from_number', '')
                existing.to_number = row.get('to_number', '')


def _upsert_facility(session: Session, row: dict, control_id: str, now: datetime) -> None:
    current = session.get(FirmsFacility, row['firms_code'])
    if current is None:
        session.add(FirmsFacility(
            firms_code=row['firms_code'],
            district_port=row.get('district_port', ''),
            status=row.get('status', ''),
            facility_type=row.get('facility_type_code', ''),
            name=row.get('facility_name', ''),
            last_update=row.get('last_update', ''),
            address=row.get('address', ''),
            city=row.get('city', ''),
            state=row.get('state', ''),
            zip=row.get('zip', ''),
            country=row.get('country', ''),
            source_control_id=control_id,
            first_seen=now,
            last_seen=now,
        ))
        session.add(FirmsFacilityHistory(
            firms_code=row['firms_code'], change_type='new', field_name='firms_code',
            new_value=row['firms_code'], source_control_id=control_id, changed_at=now,
        ))
        return
    if current.status != row.get('status', '') and row.get('status') == 'D':
        session.add(FirmsFacilityHistory(
            firms_code=current.firms_code, change_type='deactivated', field_name='status',
            old_value=current.status, new_value='D', source_control_id=control_id, changed_at=now,
        ))
    elif current.status != row.get('status', '') or current.name != row.get('facility_name', ''):
        session.add(FirmsFacilityHistory(
            firms_code=current.firms_code, change_type='updated', field_name='name' if current.name != row.get('facility_name', '') else 'status',
            old_value=current.name if current.name != row.get('facility_name', '') else current.status,
            new_value=row.get('facility_name', '') if current.name != row.get('facility_name', '') else row.get('status', ''),
            source_control_id=control_id, changed_at=now,
        ))
    current.district_port = row.get('district_port', '')
    current.status = row.get('status', '')
    current.facility_type = row.get('facility_type_code', '')
    current.name = row.get('facility_name', '')
    current.last_update = row.get('last_update', '')
    current.address = row.get('address', '')
    current.city = row.get('city', '')
    current.state = row.get('state', '')
    current.zip = row.get('zip', '')
    current.country = row.get('country', '')
    current.source_control_id = control_id
    current.last_seen = now


def _stamp(current, now: datetime, control_id: str) -> None:
    if current.first_seen is None:
        current.first_seen = now
    current.last_seen = now
    current.source_control_id = control_id


def _upsert_port(session: Session, row: dict, control_id: str, now: datetime) -> None:
    current = session.get(RefDistrictPort, row['code'])
    if current is None:
        current = RefDistrictPort(code=row['code'], first_seen=now, last_seen=now)
        session.add(current)
    for key in (
        'name', 'address1', 'address2', 'address3', 'carrier_type', 'primary_team_location',
        'secondary_team_location', 'port_of_unlading', 'city', 'state', 'zip', 'subport_code',
    ):
        setattr(current, key, row.get(key, '') or '')
    _stamp(current, now, control_id)


def _upsert_country(session: Session, row: dict, control_id: str, now: datetime) -> None:
    current = session.get(RefCountry, row['iso'])
    if current is None:
        current = RefCountry(iso=row['iso'], first_seen=now, last_seen=now)
        session.add(current)
    for key in (
        'name', 'rate_column', 'restriction', 'gsp', 'gsp_begin', 'gsp_end', 'spi',
        'currency_name', 'currency_code', 'drawback', 'schedule_c', 'agoa_spi', 'agoa_ldd',
    ):
        setattr(current, key, row.get(key, '') or '')
    current.programs = row.get('programs') or []
    _stamp(current, now, control_id)


def _upsert_foreign_port(session: Session, row: dict, control_id: str, now: datetime) -> None:
    current = session.get(RefForeignPort, row['code'])
    if current is None:
        current = RefForeignPort(code=row['code'], first_seen=now, last_seen=now)
        session.add(current)
    current.name = row.get('name', '')
    _stamp(current, now, control_id)


def _upsert_carrier(session: Session, row: dict, control_id: str, now: datetime) -> None:
    current = session.get(RefCarrier, row['carrier_code'])
    if current is None:
        current = RefCarrier(code=row['carrier_code'], first_seen=now, last_seen=now)
        session.add(current)
    current.name = row.get('carrier_name', '')
    current.mode = row.get('mode', '')
    current.mode_name = row.get('mode_name', '')
    current.address = row.get('address', '')
    current.airway_bill_prefix = row.get('airway_bill_prefix', '')
    _stamp(current, now, control_id)


class SqlReferenceSink:
    """Upsert parsed rows into the local extract tables."""

    def apply(self, session: Session, parsed, control_id: str) -> None:
        apply_rows(session, parsed, control_id)


def get_reference_sink() -> ReferenceSink:
    return SqlReferenceSink()
