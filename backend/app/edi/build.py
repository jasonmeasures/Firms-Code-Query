"""Query-record builders. One function per extract file in the June 25, 2018 draft."""

from __future__ import annotations

import re
from datetime import datetime

from app.edi.envelope import Identity, wrap_block
from app.edi.layout import F106_IN, F110, F111, freeze, marker, place

CODE_RE = re.compile(r"^[A-Z0-9]{4}$")
DATE_RE = re.compile(r"^\d{6}$")
HTS_RE = re.compile(r"^[A-Z0-9]{1,10}$")


def _mmddyy(value: str, *, today: datetime | None = None) -> str:
    if not DATE_RE.match(value or ""):
        raise ValueError("Begin date must be MMDDYY")
    month, day, year = int(value[0:2]), int(value[2:4]), 2000 + int(value[4:6])
    try:
        parsed = datetime(year, month, day)
    except ValueError as exc:
        raise ValueError("Begin date is not a real calendar date") from exc
    clock = today or datetime.now()
    if parsed.date() > clock.date():
        raise ValueError("Begin date cannot be in the future")
    return value


def f101() -> str:
    """Region/district/port. No parameters. ERF-9."""
    return freeze(marker("F101"))


def f102() -> str:
    """Country codes. No parameters. ERF-15."""
    return freeze(marker("F102"))


def f104() -> str:
    """Foreign port (Schedule K). No parameters. ERF-23."""
    return freeze(marker("F104"))


def f106(*, name: str = "", code: str = "") -> str:
    """Carrier. Blank name and code asks for the air-carrier list. ERF-25."""
    buf = marker("F106")
    if name:
        place(buf, F106_IN["name"], name[:35])
    if code:
        if not re.fullmatch(r"[A-Z0-9]{2,4}", code.upper()):
            raise ValueError("Carrier code must be 2 to 4 letters or digits")
        place(buf, F106_IN["code"], code)
    return freeze(buf)


def f110(*, update_number: str = "", from_hts: str = "", to_hts: str = "") -> str:
    """HTS update range. Blank fields ask for the latest full update. ERF-28."""
    buf = marker("F110")
    if update_number:
        if not re.fullmatch(r"\d{1,4}", update_number):
            raise ValueError("HTS update number must be 1 to 4 digits")
        place(buf, F110["update_number"], update_number)
    if from_hts:
        if not HTS_RE.match(from_hts.upper()):
            raise ValueError("From HTS number must be 1 to 10 letters or digits")
        place(buf, F110["from_hts"], from_hts)
    if to_hts:
        if not HTS_RE.match(to_hts.upper()):
            raise ValueError("To HTS number must be 1 to 10 letters or digits")
        place(buf, F110["to_hts"], to_hts)
    return freeze(buf)


def f111_code(code: str) -> str:
    if not CODE_RE.match((code or "").upper()):
        raise ValueError("FIRMS code must be 4 letters or digits")
    buf = marker("F111")
    place(buf, F111["firms_code"], code)
    return freeze(buf)


def f111_name(name: str, district: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        raise ValueError("Facility name is required")
    if len(cleaned) > 35:
        raise ValueError("Facility name is longer than 35 characters")
    if not re.fullmatch(r"\d{2}", district or ""):
        raise ValueError("District code must be 2 digits")
    buf = marker("F111")
    place(buf, F111["name"], cleaned)
    place(buf, F111["district"], district)
    return freeze(buf)


def f111_district(district: str, begin_date: str = "", *, today: datetime | None = None) -> str:
    if not re.fullmatch(r"\d{2}", district or ""):
        raise ValueError("District code must be 2 digits")
    buf = marker("F111")
    place(buf, F111["district"], district)
    if begin_date:
        place(buf, F111["begin_date"], _mmddyy(begin_date, today=today))
    return freeze(buf)


def f111_date(begin_date: str, *, today: datetime | None = None) -> str:
    buf = marker("F111")
    place(buf, F111["begin_date"], _mmddyy(begin_date, today=today))
    return freeze(buf)


def split_codes(raw: str) -> tuple[list[str], list[str]]:
    tokens = [part.strip().upper() for part in re.split(r"[\s,;]+", raw or "") if part.strip()]
    seen: set[str] = set()
    valid: list[str] = []
    invalid: list[str] = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        if CODE_RE.match(token):
            valid.append(token)
        else:
            invalid.append(token)
    return valid, invalid


def build_queries(file_code: str, query_type: str, params: dict, *, today: datetime | None = None) -> tuple[str, list[str]]:
    """Return (application id, query records) for one block."""
    file_code = file_code.upper()
    if file_code == "FIRMS":
        app = "FQ"
        if query_type == "CODE":
            records = [f111_code(params["code"])]
        elif query_type == "LIST":
            records = [f111_code(code) for code in params["codes"]]
        elif query_type == "NAME":
            records = [f111_name(params["name"], params["district"])]
        elif query_type == "DISTRICT":
            records = [f111_district(params["district"], params.get("begin_date") or "", today=today)]
        elif query_type == "ALL_DATE":
            records = [f111_date(params["begin_date"], today=today)]
        elif query_type == "ALL_DISTRICT":
            records = [
                f111_district(code, params.get("begin_date") or "", today=today)
                for code in params["districts"]
            ]
        else:
            raise ValueError(f"Unknown FIRMS query {query_type}")
    elif file_code == "DISTRICT":
        app, records = "FQ", [f101()]
    elif file_code == "COUNTRY":
        app, records = "FQ", [f102()]
    elif file_code == "FOREIGN_PORT":
        app, records = "FQ", [f104()]
    elif file_code == "CARRIER":
        app = "FQ"
        if query_type == "AIR_ALL":
            records = [f106()]
        else:
            records = [f106(name=params.get("name") or "", code=params.get("code") or "")]
    elif file_code == "HTS":
        app = "HB"
        records = [
            f110(
                update_number=params.get("update_number") or "",
                from_hts=params.get("from_hts") or "",
                to_hts=params.get("to_hts") or "",
            )
        ]
    else:
        raise ValueError(f"Unknown extract file {file_code}")
    if not records:
        raise ValueError("Query produced no records")
    return app, records


def build_block(
    identity: Identity,
    *,
    when: str,
    kn_number: str,
    control_id: str,
    file_code: str,
    query_type: str,
    params: dict,
    today: datetime | None = None,
) -> str:
    app, records = build_queries(file_code, query_type, params, today=today)
    return wrap_block(identity, when, app, kn_number, control_id, records)


def chunked(items: list[str], size: int) -> list[list[str]]:
    if size < 1:
        raise ValueError("Block size must be at least 1")
    return [items[index : index + size] for index in range(0, len(items), size)]
