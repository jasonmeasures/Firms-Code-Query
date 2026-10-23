# Use Cases — ACE Extract Reference / FIRMS Code Query

> **Document Type:** Use Cases  
> **Feature:** ACE Extract Reference (FIRMS, ports, countries, carriers, HTS)  
> **Version:** 1.0  
> **Date:** 2026-10-23  
> **Parent:** `firms_query_build_prompt.md`, ACE Extract Reference 2018-06-25  
> **Epic:** not created

---

## Legend

| Field | Meaning |
| --- | --- |
| UC-ID | Unique id |
| Actor | Who initiates |
| Priority | Must / Should / Deferred |

---

## UC-01 — Look up one FIRMS code

| | |
| --- | --- |
| **Actor** | Operator |
| **Priority** | Must |
| **Preconditions** | Local mock MQ. Transmitter identity set. |
| **Trigger** | Operator opens F111 → One code and enters `E364`. |

### Main flow

1. Operator enters a 4-character FIRMS code.
2. Screen shows an EDI preview with 80-character records and a generated control ID.
3. Operator submits. Request is written and published to the mock outbox.
4. A canned FO response is applied. Facility card shows Port Liberty.

### Expected result

- Request status `PENDING_CBP` then `APPROVED`.
- Shared `firms_facility` row for E364.
- CSV export includes Port Liberty.

### Alternate / exception flows

- Invalid code (`E36`, `E36-`) → preview blocked, submit disabled.
- ACE `012` → rejection card, status `REJECTED`.

### Acceptance criteria

- [ ] E364 returns the Port Liberty card
- [ ] Password is hidden in the API and shown in the outbox file
- [ ] Automated: `test_acceptance_e364_port_liberty_card`

---

## UC-02 — Look up a list of FIRMS codes

| | |
| --- | --- |
| **Actor** | Operator |
| **Priority** | Must |
| **Trigger** | Paste or type codes split on space, comma, or semicolon. |

### Main flow

1. Tokens are de-duplicated and uppercased.
2. Invalid tokens are listed and block submit.
3. One F111 per valid code. Lists longer than `EXTRACT_MAX_BODY_RECORDS` become a job.

### Expected result

- Valid list submits. CSV has one row per facility or rejection.

### Acceptance criteria

- [ ] Invalid tokens listed and blocking
- [ ] Export CSV for the list
- [ ] Automated: `test_acceptance_list_and_csv`, `test_list_over_cap_becomes_a_job`

---

## UC-03 — Whole-file pull since a date

| | |
| --- | --- |
| **Actor** | Admin |
| **Priority** | Must |
| **Trigger** | F111 → Everything since a date. |

### Main flow

1. Operator is refused (403).
2. Admin enters MMDDYY not in the future.
3. Response updates the shared table and the change log.

### Alternate / exception flows

- Future date → `Begin date cannot be in the future`.
- Operator role → 403.

### Acceptance criteria

- [ ] Operator cannot start the pull
- [ ] Stored count and change log update
- [ ] Automated: `test_acceptance_whole_file_updates_change_log`

---

## UC-04 — District sweep after F101

| | |
| --- | --- |
| **Actor** | Admin |
| **Priority** | Must |
| **Preconditions** | Region/district/port file loaded. |
| **Trigger** | F111 → District by district. |

### Main flow

1. One F111 per unique 2-digit district from stored ports.
2. Job screen shows progress (pending / approved / failed).

### Alternate / exception flows

- No F101 rows → 409 “Load the region/district/port file before a district sweep”.

### Acceptance criteria

- [ ] Sweep refused until F101 is stored
- [ ] Job has one request per district
- [ ] Automated: `test_sweep_requires_f101`, `test_district_sweep_creates_one_request_per_district`

---

## UC-05 — Read the ACE response

| | |
| --- | --- |
| **Actor** | Operator (own request) / Admin (any) |
| **Priority** | Must |

### Main flow

1. Ten or fewer rows → cards.
2. More than ten → table with search.
3. Rejections show F411 code and message.
4. Raw EDI tab. Control ID echo chip.

### Acceptance criteria

- [ ] Cards at ≤10, table at >10
- [ ] Automated UI: `RequestScreen` tests

---

## UC-06 — Admin vault, retry, unmatched responses

| | |
| --- | --- |
| **Actor** | Admin |
| **Priority** | Must |

### Main flow

1. Admin finds a request by control ID or KN number.
2. Failed sends appear as dead letters. Admin retries.
3. Unmatched control IDs stay in the orphan list. Operators do not see orphans.

### Acceptance criteria

- [ ] Search by control ID
- [ ] Failed send is listed; retry moves it to SENT
- [ ] Orphans hidden from operators
- [ ] Automated: `test_acceptance_admin_find_retry_and_dead_letter`

---

## UC-07 — Phase 2 entry validation

| | |
| --- | --- |
| **Actor** | Entry filing / KlearAssist / API |
| **Priority** | Must (service). Wiring into AE/SE11/X10 screens is Engine follow-up. |
| **Trigger** | `POST /api/extract/reference/firms/validate` with AE20, SE11, X10, SE20 CES/LOC. |

### Main flow

1. Unknown or invalid code → block.
2. Deactivated (`D`) → block.
3. Types 07 and 08 → allow with warning.
4. Active 01–06, 09, 10 → allow.

### Acceptance criteria

- [ ] Automated: `test_entry.py`, frontend `entry.test.ts`

---

## Traceability

| UC-ID | Ships / Deferred | Tests |
| --- | --- | --- |
| UC-01 | Ships | TP-SMK-01, TP-UT golden + parse, UI QueryScreen |
| UC-02 | Ships | TP-SMK-02, list validation, chunked job |
| UC-03 | Ships | TP-SMK-03, admin 403, change log |
| UC-04 | Ships | TP-UT jobs, JobScreen UI |
| UC-05 | Ships | RequestScreen cards/table, timeline, axe |
| UC-06 | Ships (local DLQ stand-in) | vault + retry. Engine transmitter DLQ deferred |
| UC-07 | Ships as API | entry validation. Entry-form wiring deferred |
