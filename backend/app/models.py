"""Provisional persistence. Engineering will map these onto the CHB tables.

Column names follow backend/app/migrations/add_extract_tables.py.
Local development creates them with SQLAlchemy against SQLite.
`tenant_id` is reserved and unused: KlearNow is the only tenant today.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    """Local stand-in until Entra is connected. Not a CHB user table."""

    __tablename__ = "extract_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20))


class ExtractJob(Base):
    __tablename__ = "extract_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    file_code: Mapped[str] = mapped_column(String(4))
    query_type: Mapped[str] = mapped_column(String(20))
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    requested_by: Mapped[str] = mapped_column(String(36), ForeignKey("extract_users.id"))
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    requests: Mapped[list[ExtractRequest]] = relationship(back_populates="job")


class ExtractRequest(Base):
    __tablename__ = "extract_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    control_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    kn_number: Mapped[str] = mapped_column(String(21), default="")
    file_code: Mapped[str] = mapped_column(String(4))
    query_type: Mapped[str] = mapped_column(String(20))
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    edi_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    mq_send_state: Mapped[str | None] = mapped_column(String(10), nullable=True)
    mq_send_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    requested_by: Mapped[str] = mapped_column(String(36), ForeignKey("extract_users.id"), index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    job_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("extract_jobs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    job: Mapped[ExtractJob | None] = relationship(back_populates="requests")
    response: Mapped[ExtractResponse | None] = relationship(back_populates="request", uselist=False)
    status_log: Mapped[list[ExtractStatusLog]] = relationship(back_populates="request")


class ExtractResponse(Base):
    __tablename__ = "extract_responses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    request_id: Mapped[str] = mapped_column(String(36), ForeignKey("extract_requests.id"), unique=True)
    raw_text: Mapped[str] = mapped_column(Text)
    parsed_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    parse_errors: Mapped[str | None] = mapped_column(Text, nullable=True)
    request: Mapped[ExtractRequest] = relationship(back_populates="response")


class ExtractStatusLog(Base):
    __tablename__ = "extract_status_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    request_id: Mapped[str] = mapped_column(String(36), ForeignKey("extract_requests.id"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str] = mapped_column(String(20))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    changed_by: Mapped[str | None] = mapped_column(String(60), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    request: Mapped[ExtractRequest] = relationship(back_populates="status_log")


class ExtractOrphan(Base):
    """A response we could not match. Held for an admin. Never discarded."""

    __tablename__ = "extract_orphans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    control_id: Mapped[str | None] = mapped_column(String(21), nullable=True)
    kn_number: Mapped[str | None] = mapped_column(String(21), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FirmsFacility(Base):
    __tablename__ = "firms_facility"

    firms_code: Mapped[str] = mapped_column(String(4), primary_key=True)
    district_port: Mapped[str] = mapped_column(String(4), default="")
    status: Mapped[str] = mapped_column(String(1), default="")
    facility_type: Mapped[str] = mapped_column(String(2), default="")
    name: Mapped[str] = mapped_column(String(35), default="")
    last_update: Mapped[str] = mapped_column(String(6), default="")
    address: Mapped[str] = mapped_column(String(35), default="")
    city: Mapped[str] = mapped_column(String(35), default="")
    state: Mapped[str] = mapped_column(String(2), default="")
    zip: Mapped[str] = mapped_column(String(9), default="")
    country: Mapped[str] = mapped_column(String(2), default="")
    source_control_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FirmsFacilityHistory(Base):
    __tablename__ = "firms_facility_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firms_code: Mapped[str] = mapped_column(String(4), index=True)
    change_type: Mapped[str] = mapped_column(String(20))
    field_name: Mapped[str] = mapped_column(String(20), default="")
    old_value: Mapped[str] = mapped_column(String(40), default="")
    new_value: Mapped[str] = mapped_column(String(40), default="")
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source_control_id: Mapped[str | None] = mapped_column(String(20), nullable=True)


class RefDistrictPort(Base):
    __tablename__ = "ref_district_port"

    code: Mapped[str] = mapped_column(String(5), primary_key=True)
    name: Mapped[str] = mapped_column(String(24), default="")
    address1: Mapped[str] = mapped_column(String(32), default="")
    address2: Mapped[str] = mapped_column(String(32), default="")
    address3: Mapped[str] = mapped_column(String(32), default="")
    carrier_type: Mapped[str] = mapped_column(String(1), default="")
    primary_team_location: Mapped[str] = mapped_column(String(4), default="")
    secondary_team_location: Mapped[str] = mapped_column(String(4), default="")
    port_of_unlading: Mapped[str] = mapped_column(String(1), default="")
    city: Mapped[str] = mapped_column(String(15), default="")
    state: Mapped[str] = mapped_column(String(2), default="")
    zip: Mapped[str] = mapped_column(String(9), default="")
    subport_code: Mapped[str] = mapped_column(String(5), default="")
    source_control_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RefCountry(Base):
    __tablename__ = "ref_country"

    iso: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(30), default="")
    rate_column: Mapped[str] = mapped_column(String(1), default="")
    restriction: Mapped[str] = mapped_column(String(1), default="")
    gsp: Mapped[str] = mapped_column(String(1), default="")
    gsp_begin: Mapped[str] = mapped_column(String(6), default="")
    gsp_end: Mapped[str] = mapped_column(String(6), default="")
    spi: Mapped[str] = mapped_column(String(1), default="")
    currency_name: Mapped[str] = mapped_column(String(15), default="")
    currency_code: Mapped[str] = mapped_column(String(3), default="")
    drawback: Mapped[str] = mapped_column(String(1), default="")
    schedule_c: Mapped[str] = mapped_column(String(4), default="")
    agoa_spi: Mapped[str] = mapped_column(String(1), default="")
    agoa_ldd: Mapped[str] = mapped_column(String(1), default="")
    programs: Mapped[list | None] = mapped_column(JSON, nullable=True)
    source_control_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RefForeignPort(Base):
    __tablename__ = "ref_foreign_port"

    code: Mapped[str] = mapped_column(String(5), primary_key=True)
    name: Mapped[str] = mapped_column(String(30), default="")
    source_control_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RefCarrier(Base):
    __tablename__ = "ref_carrier"

    code: Mapped[str] = mapped_column(String(4), primary_key=True)
    name: Mapped[str] = mapped_column(String(35), default="")
    mode: Mapped[str] = mapped_column(String(2), default="")
    mode_name: Mapped[str] = mapped_column(String(40), default="")
    address: Mapped[str] = mapped_column(String(32), default="")
    airway_bill_prefix: Mapped[str] = mapped_column(String(3), default="")
    source_control_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RefHtsUpdate(Base):
    __tablename__ = "ref_hts_update"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    control_id: Mapped[str] = mapped_column(String(20), unique=True)
    update_number: Mapped[str] = mapped_column(String(4), default="")
    from_number: Mapped[str] = mapped_column(String(10), default="")
    to_number: Mapped[str] = mapped_column(String(10), default="")
    narrative: Mapped[str] = mapped_column(String(52), default="")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RefPull(Base):
    __tablename__ = "ref_pulls"

    file_code: Mapped[str] = mapped_column(String(4), primary_key=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_control_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)


class ExtractCounter(Base):
    __tablename__ = "extract_counter"

    name: Mapped[str] = mapped_column(String(20), primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, default=0)
