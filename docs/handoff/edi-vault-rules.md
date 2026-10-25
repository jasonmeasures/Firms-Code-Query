# EDI vault rules — all ACE Extract reference files (not 5106, not FIRMS-only)

> **Use this file as the Cursor prompt** when changing Check EDI, Save EDI, retry, or extract field validation.
> Paste from **Prompt** downward. Do not open the 5106 repo and copy records, queues, or envelope fields.
> Companion to [`edi-vault.md`](edi-vault.md) (screen, routes, lock). This file is the **rules** for every reference file.

---

## Prompt

You are changing **Check EDI / Save EDI / retry** in **CBP reference files** (`Firms-Code-Query`). This is its own program. The 5106 vault was only the screen pattern.

**5106 is not the source of truth.** Do not import `T1`…`TM`, `E0`/`E1`, `validate_for_submit`, `TP`/`TT`, 5106 queues, PII unmask, or `/api/5106/*`.

This vault holds **every ACE Extract Reference file**, not FIRMS only:

| File | Title | App in / out | Query modes | Spec |
|---|---|---|---|---|
| F101 | Region, district and port | FQ / FO | FULL (admin): marker only, positions 5–80 spaces | ERF-9–14 |
| F102 | Country codes | FQ / FO | FULL (admin): marker only | ERF-15–22 |
| F104 | Foreign ports (Schedule K) | FQ / FO | FULL (admin): marker only | ERF-23–24 |
| F106 | Carriers | FQ / FO | CODE (40–43, 2–4 AN), NAME (5–39, max 35), AIR (name and code blank) | ERF-25–27 |
| F110 | HTS updates | **HB / HZ** | RANGE: update 5–8 (1–4 digits), from HTS 9–18, to HTS 19–28; all blank = latest full update | ERF-28–29 |
| F111 | FIRMS | FQ / FO | CODE, LIST (one F111 per code), NAME+district, ALL_DATE, ALL_DISTRICT | ERF-30–36 |

F105 and F112 were removed in the June 25 2018 chapter. Do not add them.

Authority for positions: `backend/app/edi/layout.py` and `frontend/src/lib/ediPositions.ts` (keep in sync). Authority for query builds: `backend/app/edi/build.py` and `backend/app/catalog.py`. Client mirror: `frontend/src/lib/validation.ts` (`queryIssues` must cover **every** file/mode, not only F111). Shared server function: `backend/app/edi/rules.py` → `extract_rule_errors`.

Local ports stay **UI 3002 / API 8081**. Leave 3000/3001/8080 for 5106. API prefix is `/api/extract/vault`.

### What Check must mean

`CHECK EDI` is not “80 characters and an F1xx marker.” It must mean: this block would be a valid extract query for **the file that is actually in the paste**.

Reuse / extend `backend/app/edi/rules.py` → `extract_rule_errors`. Do not write a second validator. Form submit, vault Check, sendable edit, and retry all call the same function.

Split (same idea as 5106, extract rules only):

| Action | Format / envelope | ERF rules for that file |
|---|---|---|
| Check EDI | block | report; do not say “checks out” unless these pass |
| Add scratch (`query_type=VAULT`) / orphan outbox | block | warn, still save (`warnings` on the vault item) |
| Edit of a real query (CODE, LIST, NAME, FULL, AIR, RANGE, …) | block | block (422) |
| Retry / send | block | block (422) |

`ok` on `/api/extract/vault/check` is false if `errors` **or** `rule_errors` is non-empty.

### Envelope rules (every file)

- A, B, body, Y, Z. Incomplete envelope is a rule error, not a silent pass.
- App ID is **FQ/FO** for F101/F102/F104/F106/F111 and **HB/HZ** for F110. Reject `TP`/`TT`.
- F110 in an FQ/FO envelope is an error. F101–F106/F111 in an HB/HZ envelope is an error.
- B and Y port+filer match. A and Z transmitter and date match.
- B 60–80 control ID, if present: 1–21 letters/digits.
- A 60–80 is extract user data, not a 5106 transaction number. Do not require a KN shipment number.
- FO/HZ **response** bodies (F201/F301/F401, F202, F211/F311/F411, F906): check envelope only; do not apply query-field rules.

### Per-file query rules (must all work)

**F101 / F102 / F104**  
FULL load: record id in 1–4, positions 5–80 space-filled. Extra data in those columns is an error. No FIRMS/carrier/HTS fields.

**F106**  
- CODE: positions 40–43 are 2–4 letters/digits.
- NAME: positions 5–39 required, max 35.
- AIR: name and code blank (valid).
- Do not allow a 1-character or non-alphanumeric code.

**F110**  
- Application must be HB (request).
- Update number, if present: 1–4 digits.
- From/to HTS, if present: 1–10 letters/digits.
- All three blank is valid (latest update).

**F111**  
- CODE: 4 AN in 5–8; 9–51 blank.
- LIST: each F111 is a CODE line.
- NAME: 9–43 required; district 44–45 is 2 digits (ERF-36 004 if name without district).
- ALL_DATE: begin date 46–51 MMDDYY, real calendar date, not future (F31).
- ALL_DISTRICT: district 2 digits; optional begin date same as ALL_DATE.
- ERF-36 combos: 001 name+code, 002 port+code, 003 name+port+code.
- Empty F111 (no code, name, district, or date) is an error.

A paste may contain **one file type**. Mixing F111 with F106 (or F110 with F101) in the same block is a rule error unless the spec for that paste is a single extract file.

### UI

`frontend/src/pages/VaultScreen.tsx`: Check lists format `errors` and `rule_errors`. “Checks out” only when both are empty. After a scratch save, show `warnings` in marigold. Do not mention 5106, T-records, certifier, or mailing address.

### Tests (required — every file, not only F111)

Add or extend `backend/tests/test_extract_rules.py` and `backend/tests/test_vault.py`:

1. Valid FULL F101, F102, F104 → `rule_errors == []` and Check `ok`.
2. F101/F102/F104 with junk in 5–80 → rule error.
3. Valid F106 CODE, NAME, and blank AIR → pass; 1-char code → fail.
4. Valid blank F110 with HB envelope → pass; F110 with FQ → fail; bad HTS shape → fail.
5. Valid F111 CODE (existing sample) → pass; `F111XXX` → fail.
6. Scratch add of a bad F106/F110 still 200 with `warnings`.
7. Edit of a real (non-VAULT) request with a bad body → 422.
8. Retry of stored EDI that fails that file’s rules → 422.
9. A 5106 `T1` block still fails format (needs F101–F111).

Run:

```bash
cd backend && .venv/bin/pytest -q tests/test_extract_rules.py tests/test_vault.py tests/test_hardening.py
cd frontend && npm test -- src/pages/VaultScreen.test.tsx src/lib/validation.ts src/lib/ediPositions.test.ts
```

Do not point `VITE_API_PROXY` at 8080. Do not add 5106 record labels to the CATAIR reference tab.

---

## Already in this repo

`extract_rule_errors` runs from vault Check, scratch add (warnings), sendable edit (422), and retry (422). Envelope, F101/F102/F104 marker-only, F106 CODE/NAME/AIR, F110 HB, F111, mixed-file, and T1 rejection are tested. `queryIssues` covers F101–F111 modes.

Files:

| File | Role |
|---|---|
| `backend/app/edi/rules.py` | `extract_rule_errors` / envelope |
| `backend/app/edi/build.py` | Query builders (reuse, do not fork) |
| `backend/app/catalog.py` | Modes and help for every file |
| `backend/app/services/vault.py` | Check / add / edit wiring |
| `backend/app/services/workflow.py` | Retry wiring |
| `backend/tests/test_extract_rules.py` | ERF unit tests |
| `frontend/src/lib/validation.ts` | Client `queryIssues` |
| `frontend/src/pages/VaultScreen.tsx` | Check / warnings UI |
