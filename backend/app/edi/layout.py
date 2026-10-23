"""Shared 1-based positions for the builder and the parser.

ACE Extract Reference File, June 25, 2018 draft (ERF-9 through ERF-36),
plus the A/B/Y/Z user-data columns from the verified FQ block. The batch
envelope itself is the ABI Batch and Block Control chapter; this file only
fixes the columns that chapter leaves as user data and the extract records.
"""

RECORD_LEN = 80

# Envelope. Application id is FQ/FO for every extract except HTS (HB/HZ, ERF-8).
A_SITE = (2, 5)
A_SENDER = (6, 8)
A_PASSWORD = (9, 14)
A_DATE = (15, 20)
A_APP = (26, 27)
A_KN = (60, 80)  # user data, echoed, up to 21

B_PORT = (4, 7)
B_FILER = (8, 10)
B_APP = (11, 12)
B_PREPARER_PORT = (47, 50)
B_PREPARER_FILER = (51, 53)
B_PREPARER_FLAG = (56, 56)
B_CONTROL = (60, 80)  # user data, echoed, up to 21. Correlation key.

Y_PORT = (4, 7)
Y_FILER = (8, 10)
Y_APP = (11, 12)

Z_SITE = (2, 5)
Z_SENDER = (6, 8)
Z_DATE = (15, 20)

# F101 input ERF-9. Output ERF-10. F201 ERF-12. F301 ERF-13. F401 ERF-14.
F101_IN = {"marker": (1, 4)}  # F101
F101_OUT = {
    "code": (5, 9),
    "name": (10, 33),
    "address1": (34, 65),
    "carrier_type": (66, 66),
    "primary_team": (67, 70),
    "secondary_team": (71, 74),
    "port_of_unlading": (75, 75),
}
F201 = {"code": (5, 9), "address2": (10, 41), "address3": (42, 73)}
F301 = {"code": (5, 9), "city": (10, 24), "state": (25, 26), "zip": (27, 35)}
F401 = {"code": (5, 9), "subport": (10, 14)}

# F102 input ERF-15. Output ERF-16. F202 ERF-19.
F102_OUT = {
    "country": (5, 6),
    "rate_column": (7, 7),
    "restriction": (8, 8),
    "gsp": (9, 9),
    "gsp_begin": (10, 15),
    "gsp_end": (16, 21),
    "spi": (22, 22),
    "name": (23, 52),
    "currency_name": (53, 67),
    "currency_code": (68, 70),
    "drawback": (71, 71),
    "schedule_c": (72, 75),
    "agoa_spi": (76, 76),
    "agoa_ldd": (77, 77),
}
F202 = {
    "country": (5, 6),
    "rate_column": (7, 7),
    "rate_begin": (8, 13),
    "rate_end": (14, 19),
    "restriction": (20, 20),
    "restriction_begin": (21, 26),
    "restriction_end": (27, 32),
    "spi": (33, 33),
    "spi_begin": (34, 39),
    "spi_end": (40, 45),
    "agoa_spi": (46, 46),
    "agoa_ldd": (47, 47),
    "agoa_begin": (48, 53),
    "agoa_end": (54, 59),
    "misc_spi": (60, 61),
    "misc_begin": (62, 67),
    "misc_end": (68, 73),
}

# F104 input ERF-23. Output ERF-24.
F104_OUT = {"code": (5, 9), "name": (10, 39)}

# F106 input ERF-25. Output ERF-26. F906 ERF-27.
F106_IN = {"name": (5, 39), "code": (40, 43)}
F106_OUT = {
    "code": (5, 8),
    "name": (9, 43),
    "mode": (44, 45),
    "address": (46, 77),
    "awb_prefix": (78, 80),
}
F906 = {"error_code": (33, 35), "error_message": (36, 75)}

# F110 input/output ERF-28 and ERF-29. Narrative is output only.
F110 = {
    "update_number": (5, 8),
    "from_hts": (9, 18),
    "to_hts": (19, 28),
    "narrative": (29, 80),
}

# F111 input ERF-30. F211 ERF-32. F311 ERF-34. F411 ERF-35.
F111 = {"firms_code": (5, 8), "name": (9, 43), "district": (44, 45), "begin_date": (46, 51)}
F211 = {
    "district_port": (5, 8),
    "firms_code": (9, 12),
    "status": (13, 13),
    "facility_type": (14, 15),
    "name": (16, 50),
    "last_update": (51, 56),
}
F311 = {"address": (5, 39), "city": (40, 74), "state": (75, 76)}
F411 = {"zip": (5, 13), "country": (14, 15), "error_code": (33, 35), "error_message": (36, 75)}

FACILITY_TYPES = {
    "01": "Container Freight Station",
    "02": "Foreign Trade Zone",
    "03": "Pier",
    "04": "Bonded Warehouse",
    "05": "Inspection Facility",
    "06": "Importer's Premises",
    "07": "Data Processing Site",
    "08": "CBP Administrative Site",
    "09": "CES",
    "10": "Multi Use Bonded",
}

# ERF-36. 003 keeps the source spelling SPEICIFIED.
F411_ERRORS = {
    "001": "NAME SPECIFIED WITH FIRMS CODE",
    "002": "PORT SPECIFIED WITH FIRMS CODE",
    "003": "NAME AND PORT SPEICIFIED WITH FIRMS CODE",
    "004": "PORT REQUIRED IF FACILITY NAME SPECIFIED",
    "005": "STREET ADDRESS NOT ON FILE",
    "012": "FIRMS CODE NOT ON FILE",
    "0D6": "FACILITY NAME NOT ON FILE",
    "F15": "INVALID FIRMS CODE",
    "F31": "INVALID OR FUTURE DATE",
}

F906_ERRORS = {
    "C01": "INVALID CARRIER CODE",
    "C02": "CARRIER NAME NOT ON FILE",
    "C03": "CARRIER NOT ACTIVE",
}

APP_REQUEST = {"FQ", "HB"}
APP_RESPONSE = {"FO", "HZ"}


def blank() -> list[str]:
    return [" "] * RECORD_LEN


def place(buf: list[str], span: tuple[int, int], value: str) -> None:
    start, end = span
    width = end - start + 1
    text = (value or "").upper()
    if len(text) > width:
        raise ValueError(f"Value {text!r} exceeds columns {start}-{end}")
    text = text.ljust(width)
    for offset, ch in enumerate(text):
        buf[start - 1 + offset] = ch


def freeze(buf: list[str]) -> str:
    line = "".join(buf)
    if len(line) != RECORD_LEN:
        raise ValueError(f"Record is {len(line)} characters, expected {RECORD_LEN}")
    return line


def take(line: str, span: tuple[int, int]) -> str:
    start, end = span
    return line[start - 1 : end].strip()


def marker(record_id: str) -> list[str]:
    buf = blank()
    place(buf, (1, len(record_id)), record_id)
    return buf
