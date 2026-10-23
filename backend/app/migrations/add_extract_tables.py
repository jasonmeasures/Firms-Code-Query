"""Provisional Postgres tables for engineering to map onto the CHB schema.

Local development uses SQLAlchemy create_all() against SQLite. Do not run
this script on SQLite. Table and column names are expected to change when
the CHB repository is connected.
"""

REVISION = 'add_extract_tables'
DOWN_REVISION = None

POSTGRES_UPGRADE = """
CREATE TABLE IF NOT EXISTS extract_users (
    id            VARCHAR(36) PRIMARY KEY,
    display_name  VARCHAR(120) NOT NULL,
    role          VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS extract_jobs (
    id            VARCHAR(36) PRIMARY KEY,
    file_code     VARCHAR(4) NOT NULL,
    query_type    VARCHAR(20) NOT NULL,
    params        JSONB,
    status        VARCHAR(20) NOT NULL,
    requested_by  VARCHAR(36) NOT NULL REFERENCES extract_users(id),
    tenant_id     VARCHAR(64),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS extract_requests (
    id              VARCHAR(36) PRIMARY KEY,
    control_id      VARCHAR(20) NOT NULL UNIQUE,
    kn_number       VARCHAR(21) NOT NULL UNIQUE,
    file_code       VARCHAR(4) NOT NULL,
    query_type      VARCHAR(20) NOT NULL,
    params          JSONB,
    edi_text        TEXT NOT NULL,
    status          VARCHAR(20) NOT NULL,
    mq_send_state   VARCHAR(10),
    mq_send_error   VARCHAR(500),
    requested_by    VARCHAR(36) NOT NULL REFERENCES extract_users(id),
    tenant_id       VARCHAR(64),
    job_id          VARCHAR(36) REFERENCES extract_jobs(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    submitted_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_extract_requests_user ON extract_requests (requested_by);

CREATE TABLE IF NOT EXISTS extract_responses (
    id            VARCHAR(36) PRIMARY KEY,
    request_id    VARCHAR(36) NOT NULL UNIQUE REFERENCES extract_requests(id),
    raw_text      TEXT NOT NULL,
    parsed_json   JSONB,
    received_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    parse_errors  TEXT
);

CREATE TABLE IF NOT EXISTS extract_status_log (
    id            VARCHAR(36) PRIMARY KEY,
    request_id    VARCHAR(36) NOT NULL REFERENCES extract_requests(id),
    from_status   VARCHAR(20),
    to_status     VARCHAR(20) NOT NULL,
    changed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    changed_by    VARCHAR(60),
    notes         TEXT
);

CREATE TABLE IF NOT EXISTS extract_orphans (
    id            VARCHAR(36) PRIMARY KEY,
    control_id    VARCHAR(21),
    kn_number     VARCHAR(21),
    raw_text      TEXT NOT NULL,
    received_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS firms_facility (
    firms_code          VARCHAR(4) PRIMARY KEY,
    district_port       VARCHAR(4) NOT NULL DEFAULT '',
    status              VARCHAR(1) NOT NULL DEFAULT '',
    facility_type       VARCHAR(2) NOT NULL DEFAULT '',
    name                VARCHAR(35) NOT NULL DEFAULT '',
    last_update         VARCHAR(6) NOT NULL DEFAULT '',
    address             VARCHAR(35) NOT NULL DEFAULT '',
    city                VARCHAR(35) NOT NULL DEFAULT '',
    state               VARCHAR(2) NOT NULL DEFAULT '',
    zip                 VARCHAR(9) NOT NULL DEFAULT '',
    country             VARCHAR(2) NOT NULL DEFAULT '',
    source_control_id   VARCHAR(20),
    first_seen          TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS firms_facility_history (
    id                  VARCHAR(36) PRIMARY KEY,
    firms_code          VARCHAR(4) NOT NULL,
    change_type         VARCHAR(20) NOT NULL,
    field_name          VARCHAR(20) NOT NULL DEFAULT '',
    old_value           VARCHAR(40) NOT NULL DEFAULT '',
    new_value           VARCHAR(40) NOT NULL DEFAULT '',
    changed_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_control_id   VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS ref_district_port (
    code VARCHAR(5) PRIMARY KEY,
    name VARCHAR(24) NOT NULL DEFAULT '',
    address1 VARCHAR(32) NOT NULL DEFAULT '',
    address2 VARCHAR(32) NOT NULL DEFAULT '',
    address3 VARCHAR(32) NOT NULL DEFAULT '',
    carrier_type VARCHAR(1) NOT NULL DEFAULT '',
    primary_team_location VARCHAR(4) NOT NULL DEFAULT '',
    secondary_team_location VARCHAR(4) NOT NULL DEFAULT '',
    port_of_unlading VARCHAR(1) NOT NULL DEFAULT '',
    city VARCHAR(15) NOT NULL DEFAULT '',
    state VARCHAR(2) NOT NULL DEFAULT '',
    zip VARCHAR(9) NOT NULL DEFAULT '',
    subport_code VARCHAR(5) NOT NULL DEFAULT '',
    source_control_id VARCHAR(20),
    first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ref_country (
    iso VARCHAR(2) PRIMARY KEY,
    name VARCHAR(30) NOT NULL DEFAULT '',
    rate_column VARCHAR(1) NOT NULL DEFAULT '',
    restriction VARCHAR(1) NOT NULL DEFAULT '',
    gsp VARCHAR(1) NOT NULL DEFAULT '',
    gsp_begin VARCHAR(6) NOT NULL DEFAULT '',
    gsp_end VARCHAR(6) NOT NULL DEFAULT '',
    spi VARCHAR(1) NOT NULL DEFAULT '',
    currency_name VARCHAR(15) NOT NULL DEFAULT '',
    currency_code VARCHAR(3) NOT NULL DEFAULT '',
    drawback VARCHAR(1) NOT NULL DEFAULT '',
    schedule_c VARCHAR(4) NOT NULL DEFAULT '',
    agoa_spi VARCHAR(1) NOT NULL DEFAULT '',
    agoa_ldd VARCHAR(1) NOT NULL DEFAULT '',
    programs JSONB,
    source_control_id VARCHAR(20),
    first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ref_foreign_port (
    code VARCHAR(5) PRIMARY KEY,
    name VARCHAR(30) NOT NULL DEFAULT '',
    source_control_id VARCHAR(20),
    first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ref_carrier (
    code VARCHAR(4) PRIMARY KEY,
    name VARCHAR(35) NOT NULL DEFAULT '',
    mode VARCHAR(2) NOT NULL DEFAULT '',
    mode_name VARCHAR(40) NOT NULL DEFAULT '',
    address VARCHAR(32) NOT NULL DEFAULT '',
    airway_bill_prefix VARCHAR(3) NOT NULL DEFAULT '',
    source_control_id VARCHAR(20),
    first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ref_hts_update (
    id VARCHAR(36) PRIMARY KEY,
    control_id VARCHAR(20) NOT NULL UNIQUE,
    update_number VARCHAR(4) NOT NULL DEFAULT '',
    from_number VARCHAR(10) NOT NULL DEFAULT '',
    to_number VARCHAR(10) NOT NULL DEFAULT '',
    narrative VARCHAR(52) NOT NULL DEFAULT '',
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ref_pulls (
    file_code VARCHAR(4) PRIMARY KEY,
    last_success_at TIMESTAMPTZ,
    last_control_id VARCHAR(20),
    row_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS extract_counter (
    name VARCHAR(20) PRIMARY KEY,
    last_value INTEGER NOT NULL DEFAULT 0
);
"""
