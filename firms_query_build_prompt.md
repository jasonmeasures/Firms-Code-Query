# Build prompt: FIRMS Code Query in Engine (screens, EDI, MQ management)

Paste everything below the line into Cursor or Claude Code at the repo root. Attach `firms_query_prototype.html` (working prototype of the builder, response reader and CSV export) and the ACE Extract Reference PDF.

---

## Role and goal

You are building the **FIRMS Code Query** feature for KlearNow Engine, the US CHB platform. It must follow the same path as the **5106 Importer feature**: a screen, an EDI builder, an outbound message on MQ, an inbound response from MQ, parsing, persistence, and an operator view of message state.

The feature lets users and agents:

1. Look up one FIRMS code.
2. Look up a list of FIRMS codes.
3. Pull the whole FIRMS file.
4. Pull the region/district/port list that the whole-file pull needs.
5. Read the ACE response as human-readable output.
6. Export any response, single, list or whole, as CSV.

A FIRMS code (Facilities Information and Resources Management System) identifies the CBP facility where goods are located. It is reported on the AE 20-record, the X10 record and the SE11 record.

## Step 0: study the 5106 build before writing code

Do not start coding until you have read the existing 5106 implementation and written a short summary of it (file paths, one line each). Find and list:

- the 5106 screen, form schema and validation
- the EDI builder, including the A/B/Y/Z envelope
- the MQ publisher and the response consumer
- how a request is correlated with its response
- the persistence model and migrations
- status tracking, audit trail, retries and error handling
- the tests and fixtures
- the config or secrets mechanism for the transmission identity

**Mirror the 5106 structure, naming, layering, error handling and test style.** Reuse its modules for the envelope, MQ client, status model and audit log instead of writing parallel ones. If something I describe below does not exist in the 5106 code, or conflicts with it, stop and list the questions. Do not guess. Section 9 lists the questions I already know about.

Known defect to avoid: the 5106 EDI builder writes an extra `1` after the password in the A record, which shifts the date and application ID by one position. Do not copy it. Report it, and fix it in the shared envelope code only if you can do so without changing the 5106 output unexpectedly. Ask first.

## 1. Transmission identity (KlearNow only, for now)

All transmissions use KlearNow's own identity. No other broker is supported yet, but keep the values in config so that can change later.

| Item | Value | Where it goes |
|---|---|---|
| Site code | `2809` | A and Z, positions 2-5 |
| Sender ID | `S1F` | A and Z, positions 6-8 |
| Communication password | `KLEAR1` | A, positions 9-14 |
| Processing port / filer | `2809` / `S1F` | B and Y, positions 4-7 and 8-10 |
| Preparer port / filer | `2809` / `S1F` | B, positions 47-50 and 51-53, indicator `1` at position 56 |
| Application ID, request | `FQ` | A positions 26-27, B and Y positions 11-12 |
| Application ID, response | `FO` | same positions in the response |

Read these from the same config or secret mechanism the 5106 builder uses. Do not hard-code the password in source. The values above are the dev defaults.

## 2. EDI specification (verified against CBP documents)

All records are exactly **80 characters**, space-padded, uppercase. Positions are 1-based. Sources: ACE CATAIR ABI Batch and Block Control V20, and ACE CATAIR Extract Reference File (June 25, 2018 draft, ERF-9 to ERF-36). The Extract Reference chapter is a draft: check it against the current CATAIR version on cbp.gov and tell me if it differs.

### Envelope

| Record | Positions | Content |
|---|---|---|
| **A** | 1 | `A` |
| | 2-5 | site code |
| | 6-8 | sender ID |
| | 9-14 | communication password |
| | 15-20 | transmission date MMDDYY |
| | 21-25 | spaces |
| | 26-27 | application ID (`FQ`) |
| | 28-59 | spaces |
| | 60-80 | **KN number** (user data, echoed back by ACE) |
| **B** | 1-3 | `B` and two spaces |
| | 4-7 | processing port |
| | 8-10 | processing filer |
| | 11-12 | application ID |
| | 13-46 | spaces |
| | 47-50 / 51-53 | preparer port / filer |
| | 54-55 | spaces |
| | 56 | `1` when preparer data is present |
| | 57-59 | spaces |
| | 60-80 | **control ID** (user data, echoed back by ACE) |
| **Y** | 1-3, 4-7, 8-10, 11-12 | `Y`, two spaces, port, filer, application ID. Rest spaces. |
| **Z** | 1-8 | `Z`, site code, sender ID |
| | 9-14 | spaces |
| | 15-20 | date MMDDYY |

KN number and control ID are free text, up to 21 characters each. The control ID is a unique 20-character uppercase alphanumeric string generated per request. It is the correlation key between request and response.

### F111 FIRMS code query (input)

| Element | Positions | Rule |
|---|---|---|
| Control ID, type, file code | 1-4 | `F111` |
| FIRMS code | 5-8 | 4AN. If present, positions 9-45 must be blank. |
| Name of facility | 9-43 | Left-justified prefix match. Requires a district code. |
| District code | 44-45 | First two digits of the district/port code. |
| Begin date | 46-51 | MMDDYY, not in the future. Returns codes added or updated on or after it. Allowed alone or with a district code only. Never with a FIRMS code or a name. |
| Filler | 52-80 | spaces |

Four query modes:

```
By code:           [F111E364                                                                        ]
By name+district:  [F111    PORT LIBERTY                       46                                   ]
By district:       [F111                                       46                                   ]
District + date:   [F111                                       46010126                             ]
Date only:         [F111                                         010100                             ]
```

Any number of F111 records may be sent in one block. Each query transaction carries one F111.

### F101 region/district/port list (input)

`F101` followed by spaces to 80. It takes no parameters and returns every region, district and port. Application ID `FQ` in, `FO` out.

### Response records

**F211** (facility): 5-8 district/port (4N), 9-12 FIRMS code, 13 status (`A` active, `D` deactivated), 14-15 facility type, 16-50 name, 51-56 last update MMDDYY.

Facility types: 01 Container Freight Station, 02 Foreign Trade Zone, 03 Pier, 04 Bonded Warehouse, 05 Inspection Facility, 06 Importer's Premises, 07 Data Processing Site, 08 CBP Administrative Site, 09 CES, 10 Multi Use Bonded. Types 07 and 08 must not be used for entry purposes.

**F311**: 5-39 street address, 40-74 city, 75-76 state or province.

**F411**: 5-13 ZIP, 14-15 ISO country, 33-35 error code, 36-75 error message. On rejection ACE returns the F111 exactly as sent, followed by an F411 with the error code.

F411 error codes: `001` name given with FIRMS code, `002` port given with FIRMS code, `003` name and port given with FIRMS code, `004` port required if facility name given, `005` street address not on file, `012` FIRMS code not on file, `0D6` facility name not on file, `F15` invalid FIRMS code, `F31` invalid or future date.

**F101 response group:** F101 (5-9 region/district/port code 5N, 10-33 name, 34-65 address line 1, 66 carrier type, 67-70 primary team location), F201 (10-41 address line 2, 42-73 address line 3), F301 (10-24 city, 25-26 state, 27-35 ZIP), F401 (10-14 subport code, conditional).

**A and B in the response:** `FO` as application ID, the password blanked in A, and the KN number and control ID echoed unchanged in positions 60-80.

### Verified examples

Request:

```
[A2809S1FKLEAR1101826     FQ                                KN-09PC-11:EE        ]
[B  2809S1FFQ                                  2809S1F  1   2TGFEC9WQDMLKMFSFASI ]
[F111E364                                                                        ]
[Y  2809S1FFQ                                                                    ]
[Z2809S1F      101826                                                            ]
```

Response (a real one, for use as a test fixture):

```
[A2809S1F      101826     FO                                KN-Y3B0-90:EE        ]
[B  2809S1FFO                                               EY7JUKTAIZNHYEGA5BBL ]
[F2114601E364A03PORT LIBERTY - BAYONNE             101726                        ]
[F311302 PORT JERSEY BLVD               JERSEY CITY                        NJ    ]
[F411073054569US                                                                 ]
[Y  2809S1FFO                                                                    ]
[Z2809S1F      101826                                                            ]
```

Decoded: district/port 4601, FIRMS code E364, active, type 03 Pier, name PORT LIBERTY - BAYONNE, last update 10/17/26, 302 PORT JERSEY BLVD, JERSEY CITY, NJ, ZIP 073054569, US.

## 3. Screens (follow the 5106 screen's layout, components and patterns)

Place the screen in the same navigation group as the 5106 screen. Use the Engine design system tokens and the React component library (SCSS Modules). Add no new colors or fonts. Meet WCAG 2.2 AA and use the 4px spacing scale. Show every field's position range as helper text, as the 5106 form does.

**FIRMS Lookup** with four modes:

1. **One code**: a 4-character input, uppercase, validated `^[A-Z0-9]{4}$`.
2. **List of codes**: paste or upload; split on whitespace, comma or semicolon; de-duplicate; invalid tokens listed and blocking.
3. **Whole list**: two methods.
   - Everything since a date (begin date alone).
   - District by district (one F111 per 2-digit district, built from the stored district list).
   Whole-list pulls run as a background job with progress, chunked by district, resumable and idempotent. A date-only pull is the cheap option. The district sweep is the fallback if it comes back short, or when splitting a large pull.
4. **District list (F101)**: sends the F101 query, stores the result, and feeds the district sweep.

Every mode shows:

- a live **EDI preview** with a position ruler, an all-80-characters check, and the KN number and control ID fields (control ID auto-generated, with a regenerate button)
- a **Submit** action that writes the request, publishes to MQ, and moves to the status view
- a **Request status** timeline: Built, Queued, Sent, Response received, Parsed, or Failed / Timed out, with timestamps and the control ID

**Response view:** the same screen shows the response for any request.

- 10 or fewer facilities: one card each, with name, active or deactivated pill, facility type, FIRMS code, district/port, address and last update.
- More than 10: a virtualized table with filters (district, status, type, state) and search.
- Rejections: a red card or row with the error code and message from the F411 table.
- KN number and control ID chips that show whether the echo matches the request.
- **Raw EDI** tab with the request and response text.
- **Export CSV**: a server-generated file download of all rows, not just the visible page.

CSV columns, in order: `kn_number, control_id, district_port, firms_code, status, facility_type_code, facility_type, facility_name, last_update, address, city, state, zip, country, error_code, error_message`. Use RFC 4180 quoting and CRLF line endings. Status is `Active` or `Deactivated`. Dates are MM/DD/YY.

**Admin: FIRMS Reference** (read-only table of stored facilities): search, filters, last pull date, counts, and a change log (new, updated, deactivated since the last pull).

## 4. MQ management (mirror the 5106 path)

Follow the 5106 design for queues, naming, message envelope and acknowledgements. In outline:

- **Outbound:** the builder publishes the full EDI block to the outbound queue with the control ID as the correlation ID and the request ID in message properties.
- **Inbound:** a consumer reads the response queue, matches by the control ID echoed in B positions 60-80, parses, and updates the request and the reference tables in one transaction.
- **Idempotency:** processing the same response twice must not duplicate rows. Key facilities by FIRMS code and responses by control ID.
- **Retries:** exponential backoff on publish failures, with a bounded retry count. Poison messages go to a dead-letter queue with the reason.
- **Timeouts:** a configurable response timeout moves a request to Timed out and raises an alert. A late response is still accepted and re-opens the request.
- **Unmatched responses:** any response with an unknown or missing control ID is held in an orphan list. It is visible to admins only, never shown to other users, and never discarded silently.
- **Batching:** the whole-list district sweep sends several blocks. Do not exceed the block size that 5106 uses. If you cannot find that limit, ask.
- **Operator view:** an MQ messages screen with queue depth, per-message state, replay, cancel and DLQ inspection, reusing the 5106 one if it exists.
- **Observability:** structured logs keyed by control ID and request ID, metrics for sent, matched, failed, timed out and round-trip time, and an audit entry for every submit, replay and cancel with the user and time.

## 5. Data model (use the 5106 module's stack and migration tooling)

- `firms_request`: id, control_id (unique), kn_number, type (`CODE`, `LIST`, `ALL_DATE`, `ALL_DISTRICT`, `DISTRICTS`), params (JSON), edi_text, status, requested_by, mq_message_id, timestamps.
- `firms_response`: id, request_id, raw_text, parsed_json, received_at, parse_errors.
- `firms_facility`: firms_code (PK), district_port, status, facility_type, name, last_update, address, city, state, zip, country, first_seen, last_seen, source_control_id. Keep a history table for status and name changes.
- `district_port`: code, name, address, city, state, zip, carrier_type, primary_team_location, subport_code.

## 6. Parser rules

- Strip optional surrounding brackets. Pad each line to 80. Never fail on trailing whitespace.
- A response group starts at F211. F311 and F411 attach to the most recent F211. An F411 with an error code attaches to the most recent echoed F111 and closes the group.
- I only have a single-match example. Treat a multi-facility response as one F211/F311/F411 set per facility, and flag it in tests and in the open questions.
- Keep the raw text with every parsed result. Record unrecognized records instead of dropping them.
- Positions come from one table in code, shared by the builder and the parser, with a comment citing the spec page for each record.

## 7. Phase 2: use the data

- Validate FIRMS codes on entries against `firms_facility` (AE 20-record location, SE11, X10, and SE20 qualifiers `CES` and `LOC`).
- Block deactivated codes. Warn on facility types 07 and 08.
- Scheduled incremental pull: begin date set to the last successful pull. CSMS bulletins announce updates to this file.
- Expose a FIRMS lookup tool to KlearAssist v2 and agents.

## 8. Tests and acceptance

- **Golden EDI tests** for every F111 mode, F101, and the A, B, Y and Z records: exact string match, length 80, field positions asserted.
- **Parser tests** using the real response above, a rejection (F111 echo plus F411 `012`), a deactivated facility, a multi-facility response, and a response with no matches.
- **Round trip:** build, publish to a local broker, feed a canned response, assert the persisted rows and CSV.
- **CSV test:** quotes, commas and CRLF handled; row count equals facility count; one row per rejection.
- **UI tests:** form validation, preview updates, status timeline, cards versus table switch at 10 rows, keyboard operation, axe checks.
- **Acceptance:** a user can look up E364 and see the Port Liberty card; paste a list and export a CSV; run a whole-list pull and see progress, the stored count and the change log; and an admin can find a request by control ID or KN number, replay it and see the DLQ. Nothing is sent to production until I confirm the identity, queues and the A/B record layout against a response that ACE has accepted.

## 9. Questions to answer before coding

Answer from the 5106 code where you can. Ask me for the rest.

1. Which queue manager, queue names and message format does 5106 use, and does a FIRMS request go on the same queues or its own?
2. How does the response come back, and is it routed by application ID `FO`, by control ID, or both?
3. What is the maximum block or message size?
4. Which navigation group and route should the screen live under?
5. Which stack, ORM and migration tool does the 5106 module use?
6. Should the whole-list pull be restricted to certain roles, and should it run on a schedule?
7. How does ACE return a multi-facility response? Is there one F411 per facility or one per query?
8. Does the 5106 envelope really include the extra `1` after the password in production, and has ACE accepted those files? (Layout says no.)

Deliver in phases: (1) EDI builder, parser and tests; (2) persistence and MQ; (3) screens; (4) whole-list job and admin screens; (5) phase 2 integrations. Commit after each phase with a short summary of what changed and how it was verified.
