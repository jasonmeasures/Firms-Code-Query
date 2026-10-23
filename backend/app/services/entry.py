"""Phase 2: validate FIRMS codes that will appear on an entry.

Sources match the build prompt: AE 20-record location, SE11, X10, and
SE20 qualifiers CES and LOC. This module is the CHB hook. The extract
screens do not file entries.
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.edi.layout import FACILITY_TYPES
from app.models import FirmsFacility

CODE_RE = re.compile(r"^[A-Z0-9]{4}$")

ENTRY_SOURCES = {
    "AE20": "AE 20-record location",
    "SE11": "SE11 FIRMS",
    "X10": "X10 FIRMS",
    "SE20_CES": "SE20 qualifier CES",
    "SE20_LOC": "SE20 qualifier LOC",
}

ENTRY_BLOCKED_TYPES = {"07", "08"}


def normalize_firms_code(value: str) -> str:
    return (value or "").strip().upper()


def validate_firms_for_entry(session: Session, firms_code: str, source: str = "AE20") -> dict:
    code = normalize_firms_code(firms_code)
    source = (source or "AE20").strip().upper()
    if source not in ENTRY_SOURCES:
        return {
            "source": source,
            "source_label": source,
            "firms_code": code,
            "allowed": False,
            "severity": "error",
            "code": "UNKNOWN_SOURCE",
            "message": f"Unknown entry source {source}. Use {', '.join(ENTRY_SOURCES)}.",
            "facility": None,
        }
    if not CODE_RE.match(code):
        return {
            "source": source,
            "source_label": ENTRY_SOURCES[source],
            "firms_code": code,
            "allowed": False,
            "severity": "error",
            "code": "INVALID",
            "message": "FIRMS code must be 4 letters or digits",
            "facility": None,
        }
    row = session.get(FirmsFacility, code)
    if row is None:
        return {
            "source": source,
            "source_label": ENTRY_SOURCES[source],
            "firms_code": code,
            "allowed": False,
            "severity": "error",
            "code": "NOT_ON_FILE",
            "message": f"{ENTRY_SOURCES[source]}: FIRMS {code} is not on the local reference file",
            "facility": None,
        }
    facility = {
        "firms_code": row.firms_code,
        "name": row.name,
        "status": row.status,
        "status_label": "Active" if row.status == "A" else "Deactivated" if row.status == "D" else row.status,
        "facility_type": row.facility_type,
        "facility_type_name": FACILITY_TYPES.get(row.facility_type, ""),
        "district_port": row.district_port,
    }
    if row.status == "D":
        return {
            "source": source,
            "source_label": ENTRY_SOURCES[source],
            "firms_code": code,
            "allowed": False,
            "severity": "error",
            "code": "DEACTIVATED",
            "message": f"{ENTRY_SOURCES[source]}: FIRMS {code} is deactivated and cannot be used on an entry",
            "facility": facility,
        }
    if row.facility_type in ENTRY_BLOCKED_TYPES:
        kind = FACILITY_TYPES.get(row.facility_type, row.facility_type)
        return {
            "source": source,
            "source_label": ENTRY_SOURCES[source],
            "firms_code": code,
            "allowed": True,
            "severity": "warning",
            "code": "ENTRY_TYPE",
            "message": (
                f"{ENTRY_SOURCES[source]}: FIRMS {code} is {kind}. "
                "Facility types 07 and 08 must not be used for entry purposes."
            ),
            "facility": facility,
        }
    return {
        "source": source,
        "source_label": ENTRY_SOURCES[source],
        "firms_code": code,
        "allowed": True,
        "severity": "ok",
        "code": "OK",
        "message": f"{ENTRY_SOURCES[source]}: FIRMS {code} is active",
        "facility": facility,
    }


def validate_entry_locations(session: Session, locations: list[dict]) -> dict:
    results = [
        validate_firms_for_entry(session, item.get("firms_code", ""), item.get("source", "AE20"))
        for item in locations
    ]
    return {
        "ok": all(item["allowed"] and item["severity"] != "error" for item in results),
        "blocked": [item for item in results if not item["allowed"]],
        "warnings": [item for item in results if item["severity"] == "warning"],
        "results": results,
    }
