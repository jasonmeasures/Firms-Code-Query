"""ERF query-field and extract envelope checks for vault Check / edit.

Covers every extract file, not FIRMS only.
"""

import pytest

from app.edi.build import f101, f102, f104, f106, f110
from app.edi.envelope import unbracket
from app.edi.rules import extract_rule_errors
from tests.test_vault import SAMPLE


def wrap(body: str, app: str = "FQ") -> str:
    text = unbracket(SAMPLE).replace("FQ", app)
    return text.replace("F111E364".ljust(80), body.ljust(80)[:80])


def wrap_two(first: str, second: str, app: str = "FQ") -> str:
    lines = unbracket(SAMPLE).replace("FQ", app).split("\n")
    insert = next(i for i, line in enumerate(lines) if line.startswith("F111"))
    lines[insert] = first.ljust(80)[:80]
    lines.insert(insert + 1, second.ljust(80)[:80])
    return "\n".join(lines)


@pytest.mark.parametrize("body", [f101(), f102(), f104()])
def test_full_file_marker_only_passes(body):
    assert extract_rule_errors(wrap(body)) == []


@pytest.mark.parametrize("marker", ["F101", "F102", "F104"])
def test_full_file_rejects_junk_in_5_80(marker):
    errors = extract_rule_errors(wrap((marker + "JUNK").ljust(80)))
    assert any("5–80" in e or "5-80" in e for e in errors)


def test_f106_code_name_and_air():
    assert extract_rule_errors(wrap(f106(code="AA"))) == []
    assert extract_rule_errors(wrap(f106(name="DELTA AIR LINES"))) == []
    assert extract_rule_errors(wrap(f106())) == []
    errors = extract_rule_errors(wrap(("F106" + " " * 35 + "X").ljust(80)))
    assert any("Carrier code" in e for e in errors)


def test_f110_blank_needs_hb_and_rejects_bad_hts():
    assert extract_rule_errors(wrap(f110(), app="HB")) == []
    assert any("HB/HZ" in e for e in extract_rule_errors(wrap(f110(), app="FQ")))
    bad = ("F110" + " " * 4 + "!!NOT-HTS!").ljust(80)
    assert any("HTS" in e for e in extract_rule_errors(wrap(bad, app="HB")))


def test_sample_f111_code_passes():
    assert extract_rule_errors(unbracket(SAMPLE)) == []


def test_invalid_firms_code():
    edi = unbracket(SAMPLE).replace("F111E364", "F111XXX ")
    errors = extract_rule_errors(edi)
    assert any("FIRMS code must be 4" in e for e in errors)


def test_name_without_district():
    line = "F111    PORT LIBERTY" + " " * (80 - 20)
    edi = "\n".join(unbracket(SAMPLE).split("\n")[:2] + [line.ljust(80)] + unbracket(SAMPLE).split("\n")[-2:])
    errors = extract_rule_errors(edi)
    assert any("District is required" in e for e in errors)


def test_future_begin_date():
    line = "F111" + " " * 41 + "123199" + " " * 29
    edi = "\n".join(unbracket(SAMPLE).split("\n")[:2] + [line] + unbracket(SAMPLE).split("\n")[-2:])
    errors = extract_rule_errors(edi)
    assert any("future" in e.lower() or "MMDDYY" in e or "calendar" in e for e in errors)


def test_bad_carrier_code():
    f106_line = ("F106" + " " * 35 + "X").ljust(80)
    edi = unbracket(SAMPLE).replace("F111E364".ljust(80), f106_line)
    errors = extract_rule_errors(edi)
    assert any("Carrier code" in e for e in errors)


def test_5106_app_id_rejected():
    edi = unbracket(SAMPLE).replace("FQ", "TP", 1)
    errors = extract_rule_errors(edi)
    assert any("5106" in e or "FQ" in e for e in errors)


def test_empty_f111_needs_a_key():
    edi = unbracket(SAMPLE).replace("F111E364", "F111    ")
    errors = extract_rule_errors(edi)
    assert any("needs a FIRMS code" in e for e in errors)


def test_mixed_file_types_are_a_rule_error():
    errors = extract_rule_errors(wrap_two(f111 := "F111E364".ljust(80), f106()))
    del f111
    assert any("one extract file" in e or "mix" in e.lower() for e in errors)
