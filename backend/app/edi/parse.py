"""Response parser. Raw text is always kept by the caller.

Multi-facility FIRMS responses are treated as one F211/F311/F411 set per
facility. The June 25, 2018 draft and the verified sample only show a single
facility, so that grouping is an assumption and is flagged in the tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.edi.layout import (
    A_APP,
    A_DATE,
    A_KN,
    B_APP,
    B_CONTROL,
    F101_OUT,
    F102_OUT,
    F104_OUT,
    F106_OUT,
    F110,
    F201,
    F202,
    F301,
    F401,
    F411,
    F906,
    FACILITY_TYPES,
    RECORD_LEN,
    F211,
    F311,
    take,
)


@dataclass
class ParsedResponse:
    kn_number: str = ""
    control_id: str = ""
    app_id: str = ""
    transmission_date: str = ""
    facilities: list[dict] = field(default_factory=list)
    rejections: list[dict] = field(default_factory=list)
    districts: list[dict] = field(default_factory=list)
    countries: list[dict] = field(default_factory=list)
    foreign_ports: list[dict] = field(default_factory=list)
    carriers: list[dict] = field(default_factory=list)
    hts_notices: list[dict] = field(default_factory=list)
    unrecognized: list[str] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        file_code = ""
        if self.facilities or any((item.get("echo") or "").startswith("F111") for item in self.rejections):
            file_code = "F111"
        elif self.districts:
            file_code = "F101"
        elif self.countries:
            file_code = "F102"
        elif self.foreign_ports:
            file_code = "F104"
        elif self.carriers or any((item.get("echo") or "").startswith("F106") for item in self.rejections):
            file_code = "F106"
        elif self.hts_notices:
            file_code = "F110"
        return {
            "kn_number": self.kn_number,
            "control_id": self.control_id,
            "application_id": self.app_id,
            "app_id": self.app_id,
            "file_code": file_code,
            "transmission_date": self.transmission_date,
            "rows": self.rows,
            "warnings": self.warnings,
            "facilities": self.facilities,
            "rejections": self.rejections,
            "districts": self.districts,
            "countries": self.countries,
            "foreign_ports": self.foreign_ports,
            "carriers": self.carriers,
            "hts_notices": self.hts_notices,
            "unrecognized": self.unrecognized,
            "parse_errors": self.parse_errors,
        }

    @property
    def application_id(self) -> str:
        return self.app_id

    @property
    def warnings(self) -> list[str]:
        notes = list(self.parse_errors)
        if len(self.facilities) > 1:
            notes.append(
                "Multi-facility response read as one F211/F311/F411 set per facility. "
                "The June 25, 2018 chapter only shows a single-facility sample."
            )
        if self.unrecognized:
            notes.append(f"{len(self.unrecognized)} unrecognized record(s) kept with the raw text.")
        return notes

    @property
    def rows(self) -> list[dict]:
        out: list[dict] = []
        for facility in self.facilities:
            status = facility.get("status", "")
            type_code = facility.get("facility_type", "")
            out.append({
                "kind": "facility",
                "district_port": facility.get("district_port", ""),
                "firms_code": facility.get("firms_code", ""),
                "status": status,
                "status_label": "Active" if status == "A" else "Deactivated" if status == "D" else status,
                "facility_type_code": type_code,
                "facility_type": facility.get("facility_type_name", ""),
                "facility_name": facility.get("name", ""),
                "last_update": facility.get("last_update", ""),
                "address": facility.get("address", ""),
                "city": facility.get("city", ""),
                "state": facility.get("state", ""),
                "zip": facility.get("zip", ""),
                "country": facility.get("country", ""),
                "error_code": "",
                "error_message": "",
                "entry_warning": (
                    "Facility types 07 and 08 must not be used for entry purposes."
                    if type_code in {"07", "08"} else ""
                ),
            })
        for rejection in self.rejections:
            echo = rejection.get("echo") or ""
            firms = echo[4:8].strip() if echo.startswith("F111") else ""
            out.append({
                "kind": "carrier_rejection" if echo.startswith("F106") else "rejection",
                "district_port": "",
                "firms_code": firms,
                "carrier_code": echo[39:43].strip() if echo.startswith("F106") else "",
                "carrier_name": echo[4:39].strip() if echo.startswith("F106") else "",
                "status": "",
                "status_label": "",
                "facility_type_code": "",
                "facility_type": "",
                "facility_name": "",
                "last_update": "",
                "address": "",
                "city": "",
                "state": "",
                "zip": "",
                "country": "",
                "error_code": rejection.get("error_code", ""),
                "error_message": rejection.get("error_message", ""),
                "entry_warning": "",
            })
        for district in self.districts:
            out.append({
                "kind": "district_port",
                "code": district.get("code", ""),
                "name": district.get("name", ""),
                "address1": district.get("address1", ""),
                "address2": district.get("address2", ""),
                "address3": district.get("address3", ""),
                "carrier_type": district.get("carrier_type", ""),
                "primary_team_location": district.get("primary_team", ""),
                "secondary_team_location": district.get("secondary_team", ""),
                "port_of_unlading": district.get("port_of_unlading", ""),
                "city": district.get("city", ""),
                "state": district.get("state", ""),
                "zip": district.get("zip", ""),
                "subport_code": district.get("subport", ""),
            })
        for country in self.countries:
            item = {"kind": "country", "iso": country.get("country", ""), "programs": country.get("programs") or []}
            item.update({key: country.get(key, "") for key in (
                "name", "rate_column", "restriction", "gsp", "gsp_begin", "gsp_end", "spi",
                "currency_name", "currency_code", "drawback", "schedule_c", "agoa_spi", "agoa_ldd",
            )})
            out.append(item)
        for port in self.foreign_ports:
            out.append({"kind": "foreign_port", "code": port.get("code", ""), "name": port.get("name", "")})
        for carrier in self.carriers:
            out.append({
                "kind": "carrier",
                "carrier_code": carrier.get("code", ""),
                "carrier_name": carrier.get("name", ""),
                "mode": carrier.get("mode", ""),
                "mode_name": "",
                "address": carrier.get("address", ""),
                "airway_bill_prefix": carrier.get("awb_prefix", ""),
                "error_code": "",
                "error_message": "",
            })
        for notice in self.hts_notices:
            out.append({
                "kind": "hts_update",
                "update_number": notice.get("update_number", ""),
                "from_number": notice.get("from_hts", ""),
                "to_number": notice.get("to_hts", ""),
                "narrative": notice.get("narrative", ""),
            })
        return out


def normalize_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.strip("\n")
        if not line.strip():
            continue
        if line.startswith("[") and line.endswith("]") and len(line) >= 2:
            line = line[1:-1]
        line = line.rstrip()
        if len(line) > RECORD_LEN:
            line = line[:RECORD_LEN]
        lines.append(line.ljust(RECORD_LEN))
    return lines


def _grab(line: str, spans: dict[str, tuple[int, int]]) -> dict[str, str]:
    return {name: take(line, span) for name, span in spans.items()}


def parse_response(text: str) -> ParsedResponse:
    parsed = ParsedResponse()
    lines = normalize_lines(text)
    if not lines:
        parsed.parse_errors.append("Response was empty")
        return parsed

    body: list[str] = []
    for line in lines:
        kind = line[0]
        if kind == "A":
            parsed.kn_number = take(line, A_KN)
            parsed.transmission_date = take(line, A_DATE)
            parsed.app_id = take(line, A_APP) or parsed.app_id
        elif kind == "B":
            parsed.control_id = take(line, B_CONTROL)
            parsed.app_id = take(line, B_APP) or parsed.app_id
        elif kind in {"Y", "Z"}:
            continue
        else:
            body.append(line)

    facility: dict | None = None
    district: dict | None = None
    country: dict | None = None
    echo: str | None = None

    for index, line in enumerate(body):
        record = line[:4]
        nxt = body[index + 1][:4] if index + 1 < len(body) else ""
        if record == "F211":
            facility = _grab(line, F211)
            facility["facility_type_name"] = FACILITY_TYPES.get(facility["facility_type"], "")
            facility["address"] = ""
            facility["city"] = ""
            facility["state"] = ""
            facility["zip"] = ""
            facility["country"] = ""
            facility["raw"] = line
            parsed.facilities.append(facility)
            echo = None
        elif record == "F311":
            if facility is None:
                parsed.unrecognized.append(line)
                parsed.parse_errors.append("F311 without a preceding F211")
                continue
            facility.update({key: value for key, value in _grab(line, F311).items()})
        elif record == "F411":
            error = take(line, F411["error_code"])
            if error:
                parsed.rejections.append(
                    {
                        "echo": echo or "",
                        "error_code": error,
                        "error_message": take(line, F411["error_message"]),
                        "raw": line,
                    }
                )
                facility = None
                echo = None
            elif facility is not None:
                facility["zip"] = take(line, F411["zip"])
                facility["country"] = take(line, F411["country"])
            else:
                parsed.unrecognized.append(line)
        elif record == "F111":
            echo = line
            facility = None
        elif record == "F101":
            if not take(line, F101_OUT["code"]):
                echo = line
                continue
            district = _grab(line, F101_OUT)
            district["address2"] = ""
            district["address3"] = ""
            district["city"] = ""
            district["state"] = ""
            district["zip"] = ""
            district["subport"] = ""
            district["raw"] = line
            parsed.districts.append(district)
        elif record == "F201" and district is not None:
            district["address2"] = take(line, F201["address2"])
            district["address3"] = take(line, F201["address3"])
        elif record == "F301" and district is not None:
            district.update(_grab(line, F301))
        elif record == "F401" and district is not None:
            district["subport"] = take(line, F401["subport"])
        elif record == "F102":
            if not take(line, F102_OUT["country"]):
                echo = line
                continue
            country = _grab(line, F102_OUT)
            country["programs"] = []
            country["raw"] = line
            parsed.countries.append(country)
        elif record == "F202" and country is not None:
            country["programs"].append(_grab(line, F202))
        elif record == "F104":
            code = take(line, F104_OUT["code"])
            if not code:
                echo = line
                continue
            parsed.foreign_ports.append(_grab(line, F104_OUT) | {"raw": line})
        elif record == "F106":
            if nxt == "F906":
                echo = line
                continue
            code = take(line, F106_OUT["code"])
            if not code:
                echo = line
                continue
            parsed.carriers.append(_grab(line, F106_OUT) | {"raw": line})
        elif record == "F906":
            parsed.rejections.append(
                {
                    "echo": echo or "",
                    "error_code": take(line, F906["error_code"]),
                    "error_message": take(line, F906["error_message"]),
                    "raw": line,
                }
            )
            echo = None
        elif record == "F110":
            notice = _grab(line, F110)
            notice["raw"] = line
            parsed.hts_notices.append(notice)
        else:
            parsed.unrecognized.append(line)
    return parsed
