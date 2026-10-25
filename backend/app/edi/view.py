"""Annotated EDI and MQ envelope for the extract vault, same shape as 5106."""

from __future__ import annotations

from app.edi.envelope import unbracket
from app.edi.layout import RECORD_LEN
from app.mq.outbound import DELIVERY, PRIORITY, TTL_MS

RECORD_LABELS = {
    "A": "Batch control header (site / sender / date / application id)",
    "B": "Block control header (port / filer / control ID)",
    "Y": "Block control trailer",
    "Z": "Batch control trailer",
    "F101": "Region / district / port query or response",
    "F201": "District address lines 2 and 3",
    "F301": "District city / state / ZIP",
    "F401": "Subport",
    "F102": "Country codes query or response",
    "F202": "Country program dates",
    "F104": "Foreign port (Schedule K)",
    "F106": "Carrier query or response",
    "F906": "Carrier rejection",
    "F110": "HTS update request or narrative",
    "F111": "FIRMS query",
    "F211": "FIRMS facility",
    "F311": "FIRMS street / city / state",
    "F411": "FIRMS ZIP / country or rejection",
}

QUERY_MARKERS = ("F101", "F102", "F104", "F106", "F110", "F111")


def normalize_and_validate_edi(edi: str) -> tuple[str, list[str]]:
    errors: list[str] = []
    lines: list[str] = []
    for index, raw in enumerate(unbracket(edi or "").split("\n"), 1):
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        line = line.upper()
        rec = line[:4] if line[:4] in RECORD_LABELS else line[:1]
        if len(line) > RECORD_LEN:
            errors.append(f"Line {index} ({rec}) length={len(line)}, expected 80")
            continue
        lines.append(line.ljust(RECORD_LEN))
    if not lines:
        errors.append("EDI is empty")
    elif not any(line[:4] in QUERY_MARKERS for line in lines):
        errors.append("An extract query or response record is required (F101, F102, F104, F106, F110 or F111)")
    elif not lines[0].startswith("A"):
        errors.append("A batch header is required")
    return ("\n".join(lines) + ("\n" if lines else ""), errors)


def infer_file_code(edi: str) -> str:
    for line in unbracket(edi).split("\n"):
        marker = line[:4]
        if marker in QUERY_MARKERS:
            return marker
    return ""


def annotate(edi: str) -> list[dict]:
    rows = []
    for line in unbracket(edi or "").split("\n"):
        if not line:
            continue
        rec = line[:4] if line[:4] in RECORD_LABELS else line[:1]
        rows.append({
            "id": rec,
            "label": RECORD_LABELS.get(rec, rec),
            "text": line,
            "length": len(line),
            "ok": len(line) == RECORD_LEN,
        })
    return rows


def mq_envelope(*, edi: str, file_code: str, control_id: str, filename: str, request_id: str = "") -> str:
    from app.config import get_settings

    settings = get_settings()
    return f"""CBP reference files — MQ Message
File              : {file_code}
JMSCorrelationID  : {control_id}
JMSDestination    : queue://{settings.outbound_queue}
JMSReplyTo        : queue://{settings.inbound_queue}
JMSDeliveryMode   : {DELIVERY}
JMSPriority       : {PRIORITY}
JMSExpiration     : {TTL_MS} ms (24-hour TTL)
JMSType           : CBP_EXTRACT_{file_code}
KN_SOURCE         : KLEARNOW-ENGINE
KN_REQUEST_ID     : {request_id}
Filename          : {filename}
Records           : {len([line for line in edi.split(chr(10)) if line])}

── TRANSACTION DATA ──
{edi}

── EXPECTED RESPONSE ──
Reply Queue       : {settings.inbound_queue}
Application ID    : FO (FQ queries) or HZ (HTS)
"""
