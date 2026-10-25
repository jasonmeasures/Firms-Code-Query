# Test Plan — CBP reference files

> **Document Type:** Test Plan  
> **Feature:** CBP reference files  

> **Version:** 1.0  
> **Date:** 2026-10-23  
> **Parent Use Cases:** `docs/handoff/use-cases.md`  
> **Epic:** not created

---

## 1. Scope

### In scope (this release)

- Golden EDI and parser tests for F111 / F101 / envelope
- F411 catalog (all published codes)
- Mock MQ round trip, CSV, RLS
- District sweep and chunked-list jobs
- Phase 2 FIRMS entry validation API
- Frontend regression (query rules, F411, entry)
- UI tests: form validation, preview, timeline, cards vs table, keyboard, axe
- Acceptance paths in `backend/tests/test_acceptance.py`

### Out of scope (deferred)

- Live ACE / production identity confirmation
- Engine transmitter DLQ, backoff, timeouts, queue-depth console
- Wiring entry validation into AE 20 / SE11 / X10 / SE20 screens
- Entra production sign-in
- Performance / load

---

## 2. Environments

| Env | Purpose | Notes |
| --- | --- | --- |
| Local | Dev + unit tests | `MQ_MODE=mock`, SQLite |
| Dev / Playground | End-to-end with mocks | Paste FO on the request screen (admin) |
| UAT | Sign-off against a response ACE has accepted | Do not send until identity is confirmed |

---

## 3. Smoke Tests

| ID | Linked UC | Steps | Expected |
| --- | --- | --- | --- |
| TP-SMK-01 | UC-01 | Query `E364`, apply Port Liberty FO, open request | Card: PORT LIBERTY - BAYONNE, Active, Pier |
| TP-SMK-02 | UC-02 | Paste `E364, e364; NO; AB` then `E364 E999` | First blocked; second submits; CSV downloads |
| TP-SMK-03 | UC-03 | Operator tries date pull; admin runs `010100` | Operator 403; admin stored count + change log |
| TP-SMK-04 | UC-04 | Sweep with no ports; load F101; sweep | 409 then a job with one block per district |
| TP-SMK-05 | UC-05 | 1-row vs 11-row response | Cards then table |
| TP-SMK-06 | UC-06 | Search control ID; fail a send; retry; unknown FO | Admin finds it, dead letter, retry SENT, orphan hidden from operator |
| TP-SMK-07 | UC-07 | Validate E364 / deactivated / type 07 / unknown | allow / block / warn / block |

---

## 4. Unit / Automated Tests

Run:

```bash
cd backend && .venv/bin/pytest -q
cd frontend && npm test
cd frontend && npm run test:regression
```

| ID | Area | Description | File |
| --- | --- | --- | --- |
| TP-UT-01 | Golden EDI | Verified A/B/Y/Z and F111 modes, length 80 | `tests/test_edi.py` |
| TP-UT-02 | Parser | Port Liberty, rejection, deactivated, multi, empty | `tests/test_edi.py` |
| TP-UT-03 | F411 catalog | 001, 002, 003, 004, 005, 012, 0D6, F15, F31 | `tests/test_f411.py` |
| TP-UT-04 | CSV | Quotes, commas, CRLF, one row per rejection | `tests/test_edi.py` |
| TP-UT-05 | Round trip | Mock outbox, idempotent apply, callback secret | `tests/test_api.py` |
| TP-UT-06 | Jobs | Sweep requires F101; chunked list; progress | `tests/test_jobs.py` |
| TP-UT-07 | Entry | Block D, warn 07/08, sources AE20/SE11/X10/SE20 | `tests/test_entry.py` |
| TP-UT-08 | Acceptance | UC-01 through UC-06 API paths | `tests/test_acceptance.py` |
| TP-REG-01 | Query rules | Client mirrors builder: code, list, date, mixed | `validation.regression.test.ts` |
| TP-UI-01 | Query | Validation, preview, admin-only | `QueryScreen.test.tsx` |
| TP-UI-02 | Timeline | Built → Sent → Parsed | `StatusTimeline.test.tsx` |
| TP-UI-03 | Response | Cards ≤10, table >10 | `RequestScreen.test.tsx` |
| TP-UI-04 | A11y | Keyboard on mode tabs; axe on query + timeline | `*.test.tsx` |

---

## 5. UAT Script

**Participants:** SME + ops user  
**Duration:** ~25 minutes  
**Nothing is sent to ACE.**

1. **E364 card.** Operator, F111 One code, `E364`, submit. Admin pastes the verified FO. Confirm Port Liberty card and CSV.
2. **List + CSV.** Paste `E364, BAD, AB`. Confirm block. Paste two valid codes, export CSV, open in a spreadsheet (CRLF, quoted commas).
3. **Whole-file.** Switch to operator — date pull is refused. Switch to admin, `010100`, apply a two-facility FO. Tables → FIRMS count and Change log.
4. **District sweep.** Admin loads F101 (or confirm ports exist), then District by district. Job progress ticks as each FO is applied.
5. **Admin vault.** Search the control ID. Confirm unmatched paste lands in Unmatched responses. Operator does not see it.
6. **Entry check.** `POST /api/extract/reference/firms/validate` with E364, a deactivated code, and a type 07. Confirm allow / block / warn.
7. Sign-off: [ ] SME [ ] Ops

---

## 6. Definition of Done (release)

- [x] Required unit tests exist for golden EDI, parser, F411, jobs, entry
- [x] UI regression and axe checks exist
- [ ] All smoke tests pass in Dev
- [ ] UAT signed off
- [ ] Production identity, queues, and A/B layout confirmed against an ACE-accepted response
- [ ] Nothing sent to production before that confirmation

---

## 7. Deferred Regression

| ID | Description | Why deferred |
| --- | --- | --- |
| TP-REG-02 | Live MQ publish + consumer | Engine transmitter |
| TP-REG-03 | Timed-out request reopened by a late FO | Timeouts not built |
| TP-REG-04 | Entry-form field wiring (AE 20, SE11, X10, SE20) | CHB screens not in this repo |
| TP-REG-05 | Multi-facility FO confirmed by ACE | Chapter only shows one facility |

---

## 8. Traceability

| UC-ID | Smoke | Unit | UAT |
| --- | --- | --- | --- |
| UC-01 | TP-SMK-01 | TP-UT-01, TP-UT-08 | Step 1 |
| UC-02 | TP-SMK-02 | TP-UT-06, TP-UT-08 | Step 2 |
| UC-03 | TP-SMK-03 | TP-UT-08 | Step 3 |
| UC-04 | TP-SMK-04 | TP-UT-06 | Step 4 |
| UC-05 | TP-SMK-05 | TP-UI-03 | Step 1 |
| UC-06 | TP-SMK-06 | TP-UT-08 | Step 5 |
| UC-07 | TP-SMK-07 | TP-UT-07 | Step 6 |
