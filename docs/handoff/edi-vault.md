# EDI vault — CBP reference files (not 5106)

> **Use this file as the Cursor prompt** when changing the vault, the EDI editor, or the MQ tools tab.
> Paste from **Prompt** downward. Do not open the 5106 repo and copy records, queues, or envelope fields.

---

## Prompt

You are changing the **EDI vault** in **CBP reference files** (`Firms-Code-Query`). This is its own program. The 5106 Importer tool was only the **screen pattern**: Tools tabs, add / check / save, 80-character ruler, lock after send, hide the communication password.

**5106 is not the source of truth for this vault.** Do not import 5106 records (`T1`…`TM`, `E0`, `E1`), queues, JMS types, application IDs, A/B user-data fields, PII masking, broker/company tenancy, or `/api/5106/*` routes.

This vault stores **ACE Extract Reference** queries and responses: F101, F102, F104, F106, F110, F111 (and FO/HZ body records F211 / F311 / F411, F201 / F301 / F401, F202, F906). Spec: ACE Extract Reference, June 25 2018 (ERF-9 to ERF-36), plus ABI Batch and Block Control for A/B/Y/Z.

### Hard rules

1. Local ports stay **UI 3002 / API 8081**. Leave 3000/3001/8080 for 5106.
2. API prefix is `/api/extract/vault`. Queues are `CBP.OUT.EXTRACT.QUERY` and `CBP.IN.EXTRACT.RESPONSE`.
3. Application ID is **FQ / FO** (extract) or **HB / HZ** (HTS). Never `TP` / `TT`.
4. JMSType is `CBP_EXTRACT_{file_code}`. Correlation ID is the **B-record control ID** (positions 60–80, 20 letters or digits).
5. **A positions 60–80 are blank.** These queries are not a shipment. Do not write a 5106 transaction number or a KN shipment number there.
6. A valid vault paste must contain one of `F101`, `F102`, `F104`, `F106`, `F110`, `F111`. Reject a `T1` 5106 block.
7. Vault edit may not change the **communication password** (A 9–14) or the **control ID** (B 60–80).
8. There is **no importer PII** here: no SSN / passport mask, no `?reveal_pii=`, no `unmask_edi`. Hide only the password.
9. Operators see their own requests. Admins also see unmatched FO orphans, dead letters, and orphan outbox files. Do not add 5106 `company_id` / broker context.
10. Field positions live in `backend/app/edi/layout.py` and `frontend/src/lib/ediPositions.ts`. Keep them in sync. Do not copy `5106/.../ediPositions.ts`.

### What you may copy from 5106 (pattern only)

- Tools tabs: MQ connection, EDI vault, Usage, CATAIR reference
- Add EDI → Check EDI → Save EDI; pad short lines to 80; reject length > 80
- Brackets optional on paste; storage is bare 80-character lines
- Password shown as blanks / stars; restore the stored password if the editor sends blanks
- Read-only after a successful send; 409 on edit
- Audit vault edits by SHA digest, never the EDI text
- Safe item id: `^[A-Za-z0-9._-]{1,80}$`, reject `..`
- Mock outbox under `backend/mq_outbox/`; live mode does not write EDI to disk
- Delivery: persistent, priority 5, TTL 24 hours

### What you must not copy from 5106

| 5106 | This vault |
| --- | --- |
| `/api/5106/vault` | `/api/extract/vault` |
| `CBP.OUT.5106.SUBMIT` / `CBP.IN.5106.RESPONSE` | `CBP.OUT.EXTRACT.QUERY` / `CBP.IN.EXTRACT.RESPONSE` |
| JMSType `CBP_5106_{A\|U\|N}` | `CBP_EXTRACT_F111` (or F101 / F102 / F104 / F106 / F110) |
| App ID `TP` / `TT` | `FQ` / `FO` or `HB` / `HZ` |
| Required record `T1` | Required record `F101`–`F111` |
| A 60–80 = transaction number (`KN-0B1H-1`), locked | A 60–80 = unused user data, **space-filled** |
| B 60–80 = request ID, locked | B 60–80 = **control ID**, correlation key, locked |
| B is port + filer only | B also has preparer port 47–50, filer 51–53, flag 56 |
| Lock: only `DRAFT` + send `None`/`FAILED` | Lock: `SENT` and status `PENDING_CBP` / `APPROVED` / `REJECTED` |
| SSN / passport mask + admin reveal | Password mask only |
| `Form5106Submission` + `company_id` + broker roles | `ExtractRequest` + `query_type=VAULT` + demo ADMIN / operator |
| `outbox` = unmatched outbox files | `outbox` = unmatched outbox files; **`orphans` = unmatched FO responses** (different list) |
| Usage rows `edi_view` / `edi_edit` / `pii_reveal` | Derived counts `extract_query` / `extract_job` / `vault_edi` |
| Envelope title “CBP Form 5106”, `KN_COMPANY_ID`, E0/E1 | Envelope title “CBP reference files”, `KN_REQUEST_ID`, FO or HZ |
| Download wraps `[80-char]` | Download is the masked bare lines (`text/plain`) |
| Ports 3000/3001 → 8080 | Ports **3002 → 8081** |

### After you change code

Run:

```bash
cd backend && .venv/bin/pytest -q tests/test_vault.py
cd frontend && npm test -- src/pages/VaultScreen.test.tsx src/lib/ediPositions.test.ts
```

Do not point `VITE_API_PROXY` at 8080. Do not add 5106 record labels to the CATAIR reference tab.

Keep the **same chrome** as 5106 Tools: tabs, ADD EDI, EDIT EDI, CHECK EDI, SAVE EDI, CANCEL, COPY EDI, DOWNLOAD. Extract-only extras (OPEN REQUEST, RETRY, unmatched FO orphans) sit in that same outlined-button row. Labels live in `frontend/src/lib/ediVaultChrome.ts`.

---

## Built behaviour (this repo)

### Routes

| Method | Path | Who | What |
| --- | --- | --- | --- |
| GET | `/api/extract/vault` | signed-in | List filings (visible requests with EDI), admin outbox leftovers, admin FO orphans, admin dead letters |
| POST | `/api/extract/vault/check` | signed-in | Validate only. Does not save |
| POST | `/api/extract/vault` | signed-in | Add. Creates `ExtractRequest` `query_type=VAULT`, `status=DRAFT` |
| GET | `/api/extract/vault/{id}` | owner or admin | View + annotated records + MQ envelope |
| PUT | `/api/extract/vault/{id}` | owner or admin | Edit if unlocked |
| GET | `/api/extract/vault/{id}/download` | owner or admin | `text/plain` attachment `{control_id}.edi` |
| GET | `/api/extract/mq/status` | signed-in | Mode, queues, TTL, outbox count |
| POST | `/api/extract/mq/test` | admin | Reachability check. Body host/port is **not** applied |
| GET | `/api/extract/usage` | signed-in | Counts of visible queries / jobs / vault adds |

`{id}` is the request UUID or the control ID. Admin may also open an unmatched `{control_id}.edi` in the outbox.

### Add / check rules

`backend/app/edi/view.py` → `normalize_and_validate_edi`:

- Unbracket, uppercase, skip blank lines
- Pad to 80; reject any line longer than 80
- Must include one query/response marker: `F101`, `F102`, `F104`, `F106`, `F110`, `F111`
- First line must be `A` if any lines exist
- Infer `file_code` from the first of those markers (default F111)

Add also:

- Restores the configured password if A 9–14 is blank; 422 if the caller typed a different password
- Reads or generates a control ID; 409 if that control ID already exists
- Writes the control ID into B 60–80

### Edit lock

`edit_lock_reason` in `backend/app/services/vault.py`:

- Unsent draft / failed send / orphan outbox file → editable
- `mq_send_state == SENT` and status in `PENDING_CBP`, `APPROVED`, `REJECTED` → 409 “This EDI is read-only after a successful send.”

### Password and control ID

- API never returns the real password (`mask_password`)
- Editor blanks are filled from the stored (or configured) password
- A different password → 422 `Communication password cannot be changed in the vault`
- A different B control ID → 422 `Control ID cannot be changed in the vault`

### Envelope positions the editor must show

From `frontend/src/lib/ediPositions.ts` (1-based):

| Record | Field | Positions | 5106 difference |
| --- | --- | --- | --- |
| A | Password | 9–14 | Same column; still hidden |
| A | Application ID | 26–27 | `FQ` or `HB`, not `TP` |
| A | KN / user data | 60–80 | **Blank.** 5106 puts the transaction number here |
| B | Application ID | 11–12 | `FQ` or `HB`, not `TP` |
| B | Preparer port / filer / flag | 47–50 / 51–53 / 56 | **Not on 5106 B** |
| B | Control ID | 60–80 | 5106 puts request ID here |
| F111 | FIRMS / name / district / begin date | 5–8 / 9–43 / 44–45 / 46–51 | 5106 has no F111 |

### Screen (`/vault`)

Four tabs, same chrome as 5106 Tools, different copy and data:

1. **MQ connection** — extract queues, mock outbox, admin Test connection
2. **EDI vault** — list + add/edit/check/copy/download; Open request; admin Retry on `FAILED`
3. **Usage** — event log only, no invoices
4. **CATAIR reference** — extract record ids only (A/B/Y/Z and F101…F411)

### Files

| File | Role |
| --- | --- |
| `backend/app/services/vault.py` | List / add / edit / download / lock |
| `backend/app/edi/view.py` | Normalize, annotate, MQ envelope text |
| `backend/app/edi/layout.py` | Authority for 1-based positions |
| `backend/app/routes/extract.py` | HTTP routes |
| `backend/tests/test_vault.py` | Add, lock, password, control ID, orphans, usage |
| `frontend/src/pages/VaultScreen.tsx` | Tools + vault UI |
| `frontend/src/components/EdiEditor.tsx` | Ruler + caret field legend |
| `frontend/src/lib/ediPositions.ts` | Client positions (must match layout.py) |
| `frontend/src/pages/VaultScreen.test.tsx` | Operator vs admin, add/edit chrome |

### Tests that must keep passing

- Add F111 sample → `file_code=F111`, `status=DRAFT`, password not in JSON
- Check does not create a row
- Sent query EDI is 409 on PUT
- Password or control ID change is 422
- Operator `orphans` is `[]`; admin sees unmatched FO
- MQ test is 403 for operator; 200 for admin with extract queue names

---

## Why the two vaults look alike but are not interchangeable

Both are “paste 80-character CATAIR, hide the password, lock after ACE has the message.” The **message is a different chapter**.

5106 is a **filing**: importer identity, T-records, a transaction number ACE echoes, broker port/filer, PII. This vault is a **reference query**: one or more F1xx records, a control ID ACE echoes, no shipment, no SSN. Copying 5106 positions into this editor will shift F111 FIRMS, write a transaction number into unused A user data, and send the block to the wrong queue.
