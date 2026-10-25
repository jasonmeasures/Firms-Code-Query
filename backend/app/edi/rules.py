"""ACE Extract Reference (ERF-9 to ERF-36) checks for vault Check / edit / retry.

This is not the 5106 submit validator. Query field rules reuse build.py.
"""

from __future__ import annotations

import re

from app.edi.build import CODE_RE, HTS_RE, _mmddyy
from app.edi.envelope import unbracket
from app.edi.layout import (
    A_APP,
    A_DATE,
    APP_REQUEST,
    APP_RESPONSE,
    B_APP,
    B_CONTROL,
    F106_IN,
    F110,
    F111,
    Y_APP,
    Z_DATE,
    take,
)

_CONTROL = re.compile(r"^[A-Z0-9]{1,21}$")
_DISTRICT = re.compile(r"^\d{2}$")
_CARRIER = re.compile(r"^[A-Z0-9]{2,4}$")
_UPDATE = re.compile(r"^\d{1,4}$")
_QUERY_MARKERS = ("F101", "F102", "F104", "F106", "F110", "F111")
_FULL_FILE = ("F101", "F102", "F104")


def _lines(edi: str) -> list[str]:
    return [line for line in unbracket(edi or "").split("\n") if line.strip()]


def validate_extract_envelope(edi: str) -> list[str]:
    """A/B/Y/Z order and extract application IDs (FQ/HB, or FO/HZ on a response)."""
    lines = _lines(edi)
    if not lines or not lines[0].startswith("A"):
        return []
    if len(lines) < 5:
        return ["Envelope is incomplete"]
    a, b, y, z = lines[0], lines[1], lines[-2], lines[-1]
    errors: list[str] = []
    if a[:1] != "A" or b[:1] != "B" or y[:1] != "Y" or z[:1] != "Z":
        return ["A, B, Y and Z records are missing or out of order"]
    for label, app in (("A", take(a, A_APP)), ("B", take(b, B_APP)), ("Y", take(y, Y_APP))):
        if app in {"TP", "TT"}:
            errors.append(f"{label} application ID {app} is a 5106 id; extract uses FQ/HB (FO/HZ on a response)")
        elif app and app not in APP_REQUEST | APP_RESPONSE:
            errors.append(f"{label} application ID must be FQ, FO, HB or HZ")
    app_a, app_b, app_y = take(a, A_APP), take(b, B_APP), take(y, Y_APP)
    if app_a and app_b and app_a != app_b:
        errors.append("A and B application IDs do not match")
    if app_b and app_y and app_b != app_y:
        errors.append("B and Y application IDs do not match")
    if b[3:10] != y[3:10]:
        errors.append("B and Y port/filer codes do not match")
    if a[1:8] != z[1:8]:
        errors.append("A and Z transmitter IDs do not match")
    if take(a, A_DATE) != take(z, Z_DATE):
        errors.append("A and Z dates do not match")
    control = take(b, B_CONTROL)
    if control and not _CONTROL.match(control):
        errors.append("B record control ID must be 1 to 21 letters or digits")
    return errors


def _f111_issues(line: str, index: int) -> list[str]:
    code = take(line, F111["firms_code"])
    name = take(line, F111["name"])
    district = take(line, F111["district"])
    begin = take(line, F111["begin_date"])
    prefix = f"Line {index} (F111): "
    if code and name and district:
        return [prefix + "NAME AND PORT specified with FIRMS code (ERF-36 003)"]
    if code and name:
        return [prefix + "NAME specified with FIRMS code (ERF-36 001)"]
    if code and district:
        return [prefix + "PORT specified with FIRMS code (ERF-36 002)"]
    if name and not district:
        return [prefix + "District is required when facility name is specified (ERF-36 004)"]
    issues: list[str] = []
    if code:
        if not CODE_RE.match(code):
            issues.append(prefix + "FIRMS code must be 4 letters or digits")
    elif name:
        if len(name) > 35:
            issues.append(prefix + "Facility name is longer than 35 characters")
        if not _DISTRICT.match(district):
            issues.append(prefix + "District code must be 2 digits")
    elif district:
        if not _DISTRICT.match(district):
            issues.append(prefix + "District code must be 2 digits")
        if begin:
            try:
                _mmddyy(begin)
            except ValueError as exc:
                issues.append(prefix + str(exc))
    elif begin:
        try:
            _mmddyy(begin)
        except ValueError as exc:
            issues.append(prefix + str(exc))
    else:
        issues.append(prefix + "needs a FIRMS code, facility name, district, or begin date")
    return issues


def _full_file_issues(line: str, index: int, rec: str) -> list[str]:
    extra = (line[4:] if len(line) > 4 else "").strip()
    if extra:
        return [f"Line {index} ({rec}): positions 5–80 must be spaces for a full-file query"]
    return []


def _f106_issues(line: str, index: int) -> list[str]:
    code = take(line, F106_IN["code"])
    name = take(line, F106_IN["name"])
    prefix = f"Line {index} (F106): "
    if code and not _CARRIER.match(code):
        return [prefix + "Carrier code must be 2 to 4 letters or digits"]
    if name and len(name) > 35:
        return [prefix + "Carrier name is longer than 35 characters"]
    return []


def _f110_issues(line: str, index: int) -> list[str]:
    issues: list[str] = []
    update = take(line, F110["update_number"])
    from_hts = take(line, F110["from_hts"])
    to_hts = take(line, F110["to_hts"])
    prefix = f"Line {index} (F110): "
    if update and not _UPDATE.match(update):
        issues.append(prefix + "HTS update number must be 1 to 4 digits")
    if from_hts and not HTS_RE.match(from_hts):
        issues.append(prefix + "From HTS number must be 1 to 10 letters or digits")
    if to_hts and not HTS_RE.match(to_hts):
        issues.append(prefix + "To HTS number must be 1 to 10 letters or digits")
    return issues


def extract_rule_errors(edi: str) -> list[str]:
    """Envelope + ERF query-field errors. Empty when there is no extract body to judge."""
    errors = validate_extract_envelope(edi)
    lines = _lines(edi)
    apps = {take(line, A_APP) for line in lines if line.startswith("A")}
    apps |= {take(line, B_APP) for line in lines if line.startswith("B")}
    if apps & APP_RESPONSE and not (apps & APP_REQUEST):
        return errors
    markers = {line[:4] for line in lines if line[:4] in _QUERY_MARKERS}
    if len(markers) > 1:
        errors.append("A paste may contain one extract file type. Do not mix " + ", ".join(sorted(markers)))
    if "F110" in markers and apps & {"FQ", "FO"}:
        errors.append("HTS (F110) uses application ID HB/HZ, not FQ/FO")
    if markers & {"F101", "F102", "F104", "F106", "F111"} and apps & {"HB", "HZ"}:
        errors.append("F101–F106 and F111 use application ID FQ/FO, not HB/HZ")
    for index, line in enumerate(lines, 1):
        rec = line[:4]
        if rec in _FULL_FILE:
            errors.extend(_full_file_issues(line, index, rec))
        elif rec == "F111":
            errors.extend(_f111_issues(line, index))
        elif rec == "F106":
            errors.extend(_f106_issues(line, index))
        elif rec == "F110":
            errors.extend(_f110_issues(line, index))
    return errors
