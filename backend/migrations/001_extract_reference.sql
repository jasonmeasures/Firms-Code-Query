-- Generated from app/models.py by app.migrations.generate_ddl. Do not edit.
-- Provisional Postgres tables for the ACE extract reference loads. Names are
-- local to this app; engineering will map them onto the CHB schema.
-- Local development uses SQLAlchemy create_all() against SQLite.

CREATE TABLE IF NOT EXISTS extract_counter (
	name VARCHAR(20) NOT NULL, 
	last_value INTEGER NOT NULL, 
	PRIMARY KEY (name)
);

CREATE TABLE IF NOT EXISTS extract_orphans (
	id VARCHAR(36) NOT NULL, 
	control_id VARCHAR(21), 
	kn_number VARCHAR(21), 
	raw_text TEXT NOT NULL, 
	received_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS extract_users (
	id VARCHAR(36) NOT NULL, 
	display_name VARCHAR(120) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS firms_facility (
	firms_code VARCHAR(4) NOT NULL, 
	district_port VARCHAR(4) NOT NULL, 
	status VARCHAR(1) NOT NULL, 
	facility_type VARCHAR(2) NOT NULL, 
	name VARCHAR(35) NOT NULL, 
	last_update VARCHAR(6) NOT NULL, 
	address VARCHAR(35) NOT NULL, 
	city VARCHAR(35) NOT NULL, 
	state VARCHAR(2) NOT NULL, 
	zip VARCHAR(9) NOT NULL, 
	country VARCHAR(2) NOT NULL, 
	source_control_id VARCHAR(20), 
	first_seen TIMESTAMP WITH TIME ZONE NOT NULL, 
	last_seen TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (firms_code)
);

CREATE TABLE IF NOT EXISTS firms_facility_history (
	id VARCHAR(36) NOT NULL, 
	firms_code VARCHAR(4) NOT NULL, 
	change_type VARCHAR(20) NOT NULL, 
	field_name VARCHAR(20) NOT NULL, 
	old_value VARCHAR(40) NOT NULL, 
	new_value VARCHAR(40) NOT NULL, 
	changed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	source_control_id VARCHAR(20), 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_firms_facility_history_firms_code ON firms_facility_history (firms_code);

CREATE TABLE IF NOT EXISTS ref_carrier (
	code VARCHAR(4) NOT NULL, 
	name VARCHAR(35) NOT NULL, 
	mode VARCHAR(2) NOT NULL, 
	mode_name VARCHAR(40) NOT NULL, 
	address VARCHAR(32) NOT NULL, 
	airway_bill_prefix VARCHAR(3) NOT NULL, 
	source_control_id VARCHAR(20), 
	first_seen TIMESTAMP WITH TIME ZONE, 
	last_seen TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (code)
);

CREATE TABLE IF NOT EXISTS ref_country (
	iso VARCHAR(2) NOT NULL, 
	name VARCHAR(30) NOT NULL, 
	rate_column VARCHAR(1) NOT NULL, 
	restriction VARCHAR(1) NOT NULL, 
	gsp VARCHAR(1) NOT NULL, 
	gsp_begin VARCHAR(6) NOT NULL, 
	gsp_end VARCHAR(6) NOT NULL, 
	spi VARCHAR(1) NOT NULL, 
	currency_name VARCHAR(15) NOT NULL, 
	currency_code VARCHAR(3) NOT NULL, 
	drawback VARCHAR(1) NOT NULL, 
	schedule_c VARCHAR(4) NOT NULL, 
	agoa_spi VARCHAR(1) NOT NULL, 
	agoa_ldd VARCHAR(1) NOT NULL, 
	programs JSON, 
	source_control_id VARCHAR(20), 
	first_seen TIMESTAMP WITH TIME ZONE, 
	last_seen TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (iso)
);

CREATE TABLE IF NOT EXISTS ref_district_port (
	code VARCHAR(5) NOT NULL, 
	name VARCHAR(24) NOT NULL, 
	address1 VARCHAR(32) NOT NULL, 
	address2 VARCHAR(32) NOT NULL, 
	address3 VARCHAR(32) NOT NULL, 
	carrier_type VARCHAR(1) NOT NULL, 
	primary_team_location VARCHAR(4) NOT NULL, 
	secondary_team_location VARCHAR(4) NOT NULL, 
	port_of_unlading VARCHAR(1) NOT NULL, 
	city VARCHAR(15) NOT NULL, 
	state VARCHAR(2) NOT NULL, 
	zip VARCHAR(9) NOT NULL, 
	subport_code VARCHAR(5) NOT NULL, 
	source_control_id VARCHAR(20), 
	first_seen TIMESTAMP WITH TIME ZONE, 
	last_seen TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (code)
);

CREATE TABLE IF NOT EXISTS ref_foreign_port (
	code VARCHAR(5) NOT NULL, 
	name VARCHAR(30) NOT NULL, 
	source_control_id VARCHAR(20), 
	first_seen TIMESTAMP WITH TIME ZONE, 
	last_seen TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (code)
);

CREATE TABLE IF NOT EXISTS ref_hts_update (
	id VARCHAR(36) NOT NULL, 
	control_id VARCHAR(20) NOT NULL, 
	update_number VARCHAR(4) NOT NULL, 
	from_number VARCHAR(10) NOT NULL, 
	to_number VARCHAR(10) NOT NULL, 
	narrative VARCHAR(52) NOT NULL, 
	received_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (control_id)
);

CREATE TABLE IF NOT EXISTS ref_pulls (
	file_code VARCHAR(4) NOT NULL, 
	last_success_at TIMESTAMP WITH TIME ZONE, 
	last_control_id VARCHAR(20), 
	row_count INTEGER NOT NULL, 
	PRIMARY KEY (file_code)
);

CREATE TABLE IF NOT EXISTS extract_jobs (
	id VARCHAR(36) NOT NULL, 
	file_code VARCHAR(4) NOT NULL, 
	query_type VARCHAR(20) NOT NULL, 
	params JSON, 
	status VARCHAR(20) NOT NULL, 
	requested_by VARCHAR(36) NOT NULL, 
	tenant_id VARCHAR(64), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(requested_by) REFERENCES extract_users (id)
);

CREATE TABLE IF NOT EXISTS extract_requests (
	id VARCHAR(36) NOT NULL, 
	control_id VARCHAR(20) NOT NULL, 
	kn_number VARCHAR(21) NOT NULL, 
	file_code VARCHAR(4) NOT NULL, 
	query_type VARCHAR(20) NOT NULL, 
	params JSON, 
	edi_text TEXT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	mq_send_state VARCHAR(10), 
	mq_send_error VARCHAR(500), 
	requested_by VARCHAR(36) NOT NULL, 
	tenant_id VARCHAR(64), 
	job_id VARCHAR(36), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	submitted_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(requested_by) REFERENCES extract_users (id), 
	FOREIGN KEY(job_id) REFERENCES extract_jobs (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_extract_requests_control_id ON extract_requests (control_id);

CREATE INDEX IF NOT EXISTS ix_extract_requests_requested_by ON extract_requests (requested_by);

CREATE TABLE IF NOT EXISTS extract_responses (
	id VARCHAR(36) NOT NULL, 
	request_id VARCHAR(36) NOT NULL, 
	raw_text TEXT NOT NULL, 
	parsed_json JSON, 
	received_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	parse_errors TEXT, 
	PRIMARY KEY (id), 
	UNIQUE (request_id), 
	FOREIGN KEY(request_id) REFERENCES extract_requests (id)
);

CREATE TABLE IF NOT EXISTS extract_status_log (
	id VARCHAR(36) NOT NULL, 
	request_id VARCHAR(36) NOT NULL, 
	from_status VARCHAR(20), 
	to_status VARCHAR(20) NOT NULL, 
	changed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	changed_by VARCHAR(60), 
	notes TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(request_id) REFERENCES extract_requests (id)
);

CREATE INDEX IF NOT EXISTS ix_extract_status_log_request_id ON extract_status_log (request_id);
