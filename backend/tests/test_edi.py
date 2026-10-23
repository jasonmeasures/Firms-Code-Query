"""Golden EDI and parser tests against the June 25, 2018 chapter and a real FO response."""

from datetime import datetime

import pytest

from app.edi.build import (
    build_block,
    build_queries,
    f101,
    f102,
    f104,
    f106,
    f110,
    f111_code,
    f111_date,
    f111_district,
    f111_name,
    split_codes,
)
from app.edi.csv_export import render_csv
from app.edi.envelope import Identity, bracket
from app.edi.parse import parse_response
from app.edi.record import RECORD_LEN, cut

WHEN = "101826"
IDENTITY = Identity(
    site_code="2809",
    sender_id="S1F",
    password="KLEAR1",
    port="2809",
    filer="S1F",
    preparer_port="2809",
    preparer_filer="S1F",
)

REQUEST = """\
[A2809S1FKLEAR1101826     FQ                                KN-09PC-11:EE        ]
[B  2809S1FFQ                                  2809S1F  1   2TGFEC9WQDMLKMFSFASI ]
[F111E364                                                                        ]
[Y  2809S1FFQ                                                                    ]
[Z2809S1F      101826                                                            ]
"""

RESPONSE = """\
[A2809S1F      101826     FO                                KN-Y3B0-90:EE        ]
[B  2809S1FFO                                               EY7JUKTAIZNHYEGA5BBL ]
[F2114601E364A03PORT LIBERTY - BAYONNE             101726                        ]
[F311302 PORT JERSEY BLVD               JERSEY CITY                        NJ    ]
[F411073054569US                                                                 ]
[Y  2809S1FFO                                                                    ]
[Z2809S1F      101826                                                            ]
"""


def _lines(text: str) -> list[str]:
    return [ln[1:-1] if ln.startswith('[') else ln for ln in text.strip().split('\n')]


def test_verified_request_matches_byte_for_byte():
    edi = build_block(
        IDENTITY,
        when=WHEN,
        kn_number="KN-09PC-11:EE",
        control_id="2TGFEC9WQDMLKMFSFASI",
        file_code="FIRMS",
        query_type="CODE",
        params={"code": "E364"},
    )
    assert bracket(edi) == REQUEST.strip()
    assert all(len(ln) == RECORD_LEN for ln in edi.split("\n"))


def test_a_record_positions():
    line = _lines(REQUEST)[0]
    assert len(line) == 80
    assert cut(line, 1, 1) == 'A'
    assert cut(line, 2, 5) == '2809'
    assert cut(line, 6, 8) == 'S1F'
    assert cut(line, 9, 14) == 'KLEAR1'
    assert cut(line, 15, 20) == '101826'
    assert cut(line, 21, 25) == '     '
    assert cut(line, 26, 27) == 'FQ'
    assert cut(line, 60, 80).startswith('KN-09PC-11:EE')


def test_a_record_user_data_may_be_blank():
    edi = build_block(
        IDENTITY,
        when=WHEN,
        kn_number="",
        control_id="2TGFEC9WQDMLKMFSFASI",
        file_code="FIRMS",
        query_type="CODE",
        params={"code": "E364"},
    )
    line = edi.split("\n")[0]
    assert cut(line, 60, 80) == " " * 21


def test_b_record_preparer_and_control():
    line = _lines(REQUEST)[1]
    assert cut(line, 1, 3) == 'B  '
    assert cut(line, 4, 7) == '2809'
    assert cut(line, 8, 10) == 'S1F'
    assert cut(line, 11, 12) == 'FQ'
    assert cut(line, 47, 50) == '2809'
    assert cut(line, 51, 53) == 'S1F'
    assert cut(line, 56, 56) == '1'
    assert cut(line, 60, 79) == '2TGFEC9WQDMLKMFSFASI'
    assert cut(line, 80, 80) == ' '


def test_yz_records():
    lines = _lines(REQUEST)
    assert cut(lines[3], 1, 12) == 'Y  2809S1FFQ'
    assert cut(lines[4], 1, 8) == 'Z2809S1F'
    assert cut(lines[4], 9, 14) == '      '
    assert cut(lines[4], 15, 20) == '101826'


@pytest.mark.parametrize('builder, head', [
    (f101, 'F101'),
    (f102, 'F102'),
    (f104, 'F104'),
])
def test_parameterless_queries(builder, head):
    line = builder()
    assert len(line) == 80
    assert line[:4] == head
    assert line[4:] == ' ' * 76


def test_f111_modes():
    by_code = f111_code("E364")
    assert by_code == "F111E364".ljust(80)
    assert cut(by_code, 9, 80).strip() == ""

    by_name = f111_name("PORT LIBERTY", "46")
    assert cut(by_name, 1, 8) == "F111    "
    assert cut(by_name, 9, 20) == "PORT LIBERTY"
    assert cut(by_name, 44, 45) == "46"
    assert cut(by_name, 46, 51).strip() == ""

    by_district = f111_district("46")
    assert cut(by_district, 5, 43).strip() == ""
    assert cut(by_district, 44, 45) == "46"

    both = f111_district("46", "010126", today=datetime(2026, 10, 23))
    assert cut(both, 44, 51) == "46010126"

    date_only = f111_date("010100", today=datetime(2026, 10, 23))
    assert cut(date_only, 5, 45).strip() == ""
    assert cut(date_only, 46, 51) == "010100"


def test_f111_rejects_mixed_modes():
    with pytest.raises(Exception):
        f111_name("PORT LIBERTY", "")
    with pytest.raises(Exception):
        f111_date("123199", today=datetime(2026, 10, 23))


def test_list_blocks_invalid_tokens():
    valid, invalid = split_codes("E364, e364; NO; AB")
    assert valid == ["E364"]
    assert invalid == ["NO", "AB"]
    with pytest.raises(Exception):
        build_queries("FIRMS", "LIST", {"codes": ["NO"]})


def test_f106_and_f110_positions():
    air = f106()
    assert air == "F106".ljust(80)
    named = f106(name="MAERSK", code="MAEU")
    assert cut(named, 5, 11) == "MAERSK "
    assert cut(named, 40, 43) == "MAEU"
    hts = f110(update_number="0002", from_hts="0101", to_hts="0102")
    assert cut(hts, 1, 4) == "F110"
    assert cut(hts, 5, 8) == "0002"
    assert cut(hts, 9, 18).strip() == "0101"
    assert cut(hts, 19, 28).strip() == "0102"
    assert len(hts) == 80


def test_hts_application_id_is_hb():
    edi = build_block(
        IDENTITY,
        when=WHEN,
        kn_number="KN-F110-1",
        control_id="ABCDE12345ABCDE12345",
        file_code="HTS",
        query_type="RANGE",
        params={},
    )
    assert cut(edi.split("\n")[0], 26, 27) == "HB"
    assert cut(edi.split("\n")[1], 11, 12) == "HB"


def test_parse_port_liberty_response():
    parsed = parse_response(RESPONSE)
    assert parsed.kn_number == 'KN-Y3B0-90:EE'
    assert parsed.control_id == 'EY7JUKTAIZNHYEGA5BBL'
    assert parsed.application_id == 'FO'
    assert len(parsed.rows) == 1
    row = parsed.rows[0]
    assert row['district_port'] == '4601'
    assert row['firms_code'] == 'E364'
    assert row['status'] == 'A'
    assert row['status_label'] == 'Active'
    assert row['facility_type_code'] == '03'
    assert row['facility_type'] == 'Pier'
    assert row['facility_name'] == 'PORT LIBERTY - BAYONNE'
    assert row['last_update'] == '101726'
    assert row['address'] == '302 PORT JERSEY BLVD'
    assert row['city'] == 'JERSEY CITY'
    assert row['state'] == 'NJ'
    assert row['zip'] == '073054569'
    assert row['country'] == 'US'
    assert parsed.warnings == []


def test_parse_rejection_echoes_f111():
    echoed = 'F111ZZZZ'.ljust(80)
    error = 'F411'.ljust(32) + '012' + 'FIRMS CODE NOT ON FILE'.ljust(40) + ' ' * 5
    assert len(error) == 80
    parsed = parse_response(f'{echoed}\n{error}')
    assert len(parsed.rows) == 1
    assert parsed.rows[0]['kind'] == 'rejection'
    assert parsed.rows[0]['firms_code'] == 'ZZZZ'
    assert parsed.rows[0]['error_code'] == '012'
    assert 'NOT ON FILE' in parsed.rows[0]['error_message']


def test_parse_deactivated_and_entry_warning():
    line = 'F2111001ABCDD07DATA SITE'.ljust(80)
    parsed = parse_response(line)
    row = parsed.rows[0]
    assert row['status_label'] == 'Deactivated'
    assert row['facility_type_code'] == '07'
    assert 'must not be used for entry' in row['entry_warning']


def test_parse_multi_facility_is_flagged():
    one = 'F2114601E364A03PORT LIBERTY - BAYONNE'.ljust(80)
    two = 'F2114601E999A01OTHER FACILITY'.ljust(80)
    addr = 'F311' + '1 MAIN ST'.ljust(35) + 'NEWARK'.ljust(35) + 'NJ' + ' ' * 4
    assert len(addr) == 80
    parsed = parse_response('\n'.join([one, addr, two]))
    assert len([r for r in parsed.rows if r['kind'] == 'facility']) == 2
    assert parsed.rows[0]['address'] == '1 MAIN ST'
    assert any('Multi-facility' in w for w in parsed.warnings)


def test_parse_no_facility_rows():
    parsed = parse_response('A'.ljust(80) + '\n' + 'B'.ljust(80))
    assert parsed.rows == []


def test_unrecognized_record_is_kept():
    parsed = parse_response('F999SOMETHING'.ljust(80))
    assert parsed.unrecognized
    assert parsed.rows == []


def test_csv_quotes_commas_and_uses_crlf():
    parsed = parse_response(RESPONSE).as_dict()
    parsed['rows'][0]['facility_name'] = 'PORT, LIBERTY'
    text = render_csv(parsed)
    assert '\r\n' in text
    assert '"PORT, LIBERTY"' in text
    body = text.strip().split('\r\n')
    assert len(body) == 2
    assert body[0].split(',')[0] == 'kn_number'
    assert 'Active' in body[1]
    assert '10/17/26' in body[1]


def test_csv_one_row_per_rejection():
    echoed = 'F111ZZZZ'.ljust(80)
    error = 'F411'.ljust(32) + '012' + 'FIRMS CODE NOT ON FILE'.ljust(40) + ' ' * 5
    text = render_csv(parse_response(f'{echoed}\n{error}').as_dict())
    assert text.count('\r\n') == 2
    assert '012' in text
