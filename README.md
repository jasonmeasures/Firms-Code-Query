# CBP reference files

Reference-file loads for the CHB platform. A user or agent can query one code.
An admin can load a whole file. Responses are parsed, stored, and shown in the
same status words on every file.

This is its own program. The 5106 tool was the pattern for the PrimeReact
screens and for the mock MQ path (outbox, callback, admin retry, vault). Its
repository is not modified and its envelope is not reused. Vault add/edit
rules, and where they must not follow 5106, are in
[`docs/handoff/edi-vault.md`](docs/handoff/edi-vault.md).

## Files in the June 25, 2018 chapter

CBP still publishes that draft as the current "Query: Extract Reference File"
chapter: [ACE Extract Reference_20180625.pdf](https://www.cbp.gov/sites/default/files/assets/documents/2018-Jun/ACE%20Extract%20Reference_20180625.pdf)
([CATAIR index](https://www.cbp.gov/trade/automated/catair)).

| File | What it loads | Request | Response |
| --- | --- | --- | --- |
| F101 | Region, district, port | FQ | FO |
| F102 | Country codes | FQ | FO |
| F104 | Foreign ports, Schedule K | FQ | FO |
| F106 | Carriers | FQ | FO |
| F110 | HTS update request | HB | HZ |
| F111 | FIRMS facilities | FQ | FO |

F105 (ZIP) and F112 (import specialist team) were removed in that revision and
are not built. F110 returns a narrative. The tariff line records live in the
Harmonized Tariff Schedule chapter, which is not in this draft.

The chapter does not state a maximum block size. It does say each FIRMS
transaction carries one F111, and that any number of F111 records may sit in
one batch or block. A list longer than `EXTRACT_MAX_BODY_RECORDS` (default 50)
is split into separate messages. A district sweep sends one F111 per message.
That cap is local until CBP confirms a limit.

## Identifiers

The extract chapter points A and B at the ABI Batch and Block Control chapter.
A positions 60-80 are Transmitter's User Data Text (21X, optional). These
queries are not a shipment, so that field is space-filled. The control ID is
20 letters or digits in B positions 60-80, and it is the MQ correlation id.
ACE echoes both when present.
The communication password is A positions 9-14 and comes from
`KN_TRANSMITTER_PASSWORD`. It is not hard-coded. API screens mask it. The mock
outbox file keeps the real record.

Queues, separate from 5106: `CBP.OUT.EXTRACT.QUERY` and `CBP.IN.EXTRACT.RESPONSE`.

## Who can do what

Operators see only their own requests. Admins see every request, the vault,
unmatched responses, and the FIRMS change log. Whole-file loads (F101, F102,
F104, the air-carrier list, HTS, and a FIRMS date or district sweep) are admin
only. Reference rows are shared: an individual query updates the shared table,
and both roles can read it. `tenant_id` is on the request for a later policy.
Production sign-in is refused until Entra is connected. Locally, the demo role
switcher sends `X-Demo-User`.

Status words match the 5106 filing: `DRAFT`, `PENDING_CBP`, `APPROVED`,
`REJECTED`, with send state `PENDING`, `SENT`, `FAILED`.

## Run locally

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --host 0.0.0.0 --port 8081

cd frontend
npm install
npm run dev
```

This program is not the 5106 tool. It uses its own ports so both can run at once:

| App | UI | API |
| --- | --- | --- |
| CBP reference files (this repo) | http://localhost:3002 | http://127.0.0.1:8081 |
| 5106 Importer | http://localhost:3000 or 3001 | http://127.0.0.1:8080 |

`APP_ENV` defaults to `prod`, which refuses demo sign-in. `.env.example` sets `APP_ENV=dev` for local runs. A non-dev start also refuses the dev password, the dev callback secret and a `*` CORS list; set `CORS_ORIGINS` to the UI origin.

Open http://localhost:3002. `GET http://127.0.0.1:8081/health` returns `{"status": "ok"}`.

Nothing is sent to ACE. `MQ_MODE=mock` writes `backend/mq_outbox/`. Paste a
response on the request screen (admin, dev only) or post it to
`POST /api/extract/callback` with `X-Callback-Secret`.

## Tests

Scenarios and the UAT script live in `docs/handoff/test-plan.md` and `docs/handoff/use-cases.md`.

```bash
cd backend && .venv/bin/pytest -q
cd frontend && npm test
cd frontend && npm run test:regression
```

Backend: golden EDI, F411 catalog, mock MQ, jobs/sweep, phase-2 entry validation, and acceptance paths.
Frontend: query-rule regression, entry checks, preview/timeline/cards, keyboard, axe, and vault chrome (EDIT / COPY / DOWNLOAD / OPEN REQUEST).

## For engineering

Postgres DDL is generated from the models: `cd backend && python -m app.migrations.generate_ddl > migrations/001_extract_reference.sql` (a test fails if the file is stale). It is provisional and has not been run against a live Postgres.

Parsed rows are written through `ReferenceSink` in `backend/app/repository.py`. To land them in the CHB tables, add a sink and return it from `get_reference_sink()`.

Install `requirements-dev.txt` for tests; `requirements-live.txt` adds `pymqi` for `MQ_MODE=live`. The stored EDI has the password blanked; it is restored only for the queue PUT.

The provisional note:
Point it at the CHB tables when that repository is available. Dead-letter,
backoff, response timeouts, and a queue-depth console are waiting on the
Engine transmitter.
