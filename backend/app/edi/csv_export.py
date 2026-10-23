"""RFC 4180 CSV with CRLF line endings. One row per parsed result or rejection."""

from __future__ import annotations

import csv
import io

FIRMS_COLUMNS = [
    'kn_number', 'control_id', 'district_port', 'firms_code', 'status',
    'facility_type_code', 'facility_type', 'facility_name', 'last_update',
    'address', 'city', 'state', 'zip', 'country', 'error_code', 'error_message',
]

COLUMNS = {
    'F111': FIRMS_COLUMNS,
    'F101': [
        'kn_number', 'control_id', 'code', 'name', 'address1', 'address2', 'address3',
        'carrier_type', 'primary_team_location', 'secondary_team_location',
        'port_of_unlading', 'city', 'state', 'zip', 'subport_code',
    ],
    'F102': [
        'kn_number', 'control_id', 'iso', 'name', 'rate_column', 'restriction', 'gsp',
        'gsp_begin', 'gsp_end', 'spi', 'currency_name', 'currency_code', 'drawback',
        'schedule_c', 'agoa_spi', 'agoa_ldd', 'program_count',
    ],
    'F104': ['kn_number', 'control_id', 'code', 'name'],
    'F106': [
        'kn_number', 'control_id', 'carrier_code', 'carrier_name', 'mode', 'mode_name',
        'address', 'airway_bill_prefix', 'error_code', 'error_message',
    ],
    'F110': ['kn_number', 'control_id', 'update_number', 'from_number', 'to_number', 'narrative'],
}


def _mmddyy(value: str) -> str:
    text = (value or '').strip()
    if len(text) == 6 and text.isdigit():
        return f'{text[0:2]}/{text[2:4]}/{text[4:6]}'
    return text


def _firms_row(kn: str, control: str, row: dict) -> dict:
    status = row.get('status_label') or (
        'Active' if row.get('status') == 'A' else 'Deactivated' if row.get('status') == 'D' else row.get('status', '')
    )
    return {
        'kn_number': kn,
        'control_id': control,
        'district_port': row.get('district_port', ''),
        'firms_code': row.get('firms_code', ''),
        'status': status,
        'facility_type_code': row.get('facility_type_code', ''),
        'facility_type': row.get('facility_type', ''),
        'facility_name': row.get('facility_name', ''),
        'last_update': _mmddyy(row.get('last_update', '')),
        'address': row.get('address', ''),
        'city': row.get('city', ''),
        'state': row.get('state', ''),
        'zip': row.get('zip', ''),
        'country': row.get('country', ''),
        'error_code': row.get('error_code', ''),
        'error_message': row.get('error_message', ''),
    }


def rows_for_csv(parsed: dict) -> list[dict]:
    kn = parsed.get('kn_number', '')
    control = parsed.get('control_id', '')
    file_code = parsed.get('file_code') or 'F111'
    out: list[dict] = []
    for row in parsed.get('rows') or []:
        kind = row.get('kind')
        if kind == 'carrier_query':
            continue
        if file_code == 'F111' and kind in {'facility', 'rejection'}:
            out.append(_firms_row(kn, control, row))
        elif kind == 'district_port':
            out.append({'kn_number': kn, 'control_id': control, **{k: row.get(k, '') for k in COLUMNS['F101'] if k not in {'kn_number', 'control_id'}}})
        elif kind == 'country':
            item = {'kn_number': kn, 'control_id': control}
            for key in COLUMNS['F102']:
                if key in {'kn_number', 'control_id'}:
                    continue
                if key == 'program_count':
                    item[key] = str(len(row.get('programs') or []))
                else:
                    item[key] = row.get(key, '')
            out.append(item)
        elif kind == 'foreign_port':
            out.append({'kn_number': kn, 'control_id': control, 'code': row.get('code', ''), 'name': row.get('name', '')})
        elif kind in {'carrier', 'carrier_rejection'}:
            out.append({
                'kn_number': kn,
                'control_id': control,
                'carrier_code': row.get('carrier_code', ''),
                'carrier_name': row.get('carrier_name', ''),
                'mode': row.get('mode', ''),
                'mode_name': row.get('mode_name', ''),
                'address': row.get('address', ''),
                'airway_bill_prefix': row.get('airway_bill_prefix', ''),
                'error_code': row.get('error_code', ''),
                'error_message': row.get('error_message', ''),
            })
        elif kind == 'hts_update':
            out.append({
                'kn_number': kn,
                'control_id': control,
                'update_number': row.get('update_number', ''),
                'from_number': row.get('from_number', ''),
                'to_number': row.get('to_number', ''),
                'narrative': row.get('narrative', ''),
            })
    return out


def render_csv(parsed: dict) -> str:
    file_code = parsed.get('file_code') or 'F111'
    columns = COLUMNS.get(file_code, FIRMS_COLUMNS)
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator='\r\n', quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    for row in rows_for_csv(parsed):
        writer.writerow({key: row.get(key, '') for key in columns})
    return buffer.getvalue()
