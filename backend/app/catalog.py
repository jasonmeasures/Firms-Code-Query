"""Reference files in the June 25, 2018 Extract Reference chapter.

F105 and F112 were removed by that revision and are not offered.
"""

from __future__ import annotations

FILES = [
    {
        'file_code': 'F101',
        'title': 'Region, district and port',
        'summary': 'Every CBP region, district and port. The FIRMS district sweep reads the first two digits of these codes.',
        'spec': 'ERF-9 to ERF-14',
        'app_in': 'FQ',
        'app_out': 'FO',
        'modes': [
            {
                'id': 'FULL',
                'label': 'Load the file',
                'admin_only': True,
                'help': 'F101 positions 1-4, then spaces through 80. No parameters.',
                'fields': [],
            },
        ],
    },
    {
        'file_code': 'F102',
        'title': 'Country codes',
        'summary': 'ISO country codes, duty column, GSP, special programs and currency.',
        'spec': 'ERF-15 to ERF-22',
        'app_in': 'FQ',
        'app_out': 'FO',
        'modes': [
            {
                'id': 'FULL',
                'label': 'Load the file',
                'admin_only': True,
                'help': 'F102 positions 1-4, then spaces through 80.',
                'fields': [],
            },
        ],
    },
    {
        'file_code': 'F104',
        'title': 'Foreign ports (Schedule K)',
        'summary': 'Foreign port of lading codes and names.',
        'spec': 'ERF-23 to ERF-24',
        'app_in': 'FQ',
        'app_out': 'FO',
        'modes': [
            {
                'id': 'FULL',
                'label': 'Load the file',
                'admin_only': True,
                'help': 'F104 positions 1-4, then spaces through 80.',
                'fields': [],
            },
        ],
    },
    {
        'file_code': 'F106',
        'title': 'Carriers',
        'summary': 'Air and vessel carriers. A blank query returns the air-carrier list.',
        'spec': 'ERF-25 to ERF-27',
        'app_in': 'FQ',
        'app_out': 'FO',
        'modes': [
            {
                'id': 'CODE',
                'label': 'One carrier code',
                'admin_only': False,
                'help': 'Carrier code, positions 40-43. 2, 3, or 4 characters.',
                'fields': [
                    {'name': 'carrier_code', 'label': 'Carrier code', 'positions': '40-43', 'max_length': 4},
                ],
            },
            {
                'id': 'NAME',
                'label': 'Carrier name',
                'admin_only': False,
                'help': 'Name, positions 5-39. ACE returns the first exact match.',
                'fields': [
                    {'name': 'carrier_name', 'label': 'Carrier name', 'positions': '5-39', 'max_length': 35},
                ],
            },
            {
                'id': 'AIR',
                'label': 'All air carriers',
                'admin_only': True,
                'help': 'Leave the name and code blank. ACE returns every air carrier.',
                'fields': [],
            },
        ],
    },
    {
        'file_code': 'F110',
        'title': 'Harmonized tariff updates',
        'summary': 'Asks ACE for HTS changes. The line-level tariff records are in the Harmonized Tariff Schedule chapter, not this one. A CSMS message announces updates.',
        'spec': 'ERF-28 to ERF-29',
        'app_in': 'HB',
        'app_out': 'HZ',
        'modes': [
            {
                'id': 'RANGE',
                'label': 'Update range',
                'admin_only': True,
                'help': 'Blank fields mean the latest update, from the start of the file through the end.',
                'fields': [
                    {'name': 'update_number', 'label': 'Update number', 'positions': '5-8', 'max_length': 4},
                    {'name': 'from_number', 'label': 'From HTS number', 'positions': '9-18', 'max_length': 10},
                    {'name': 'to_number', 'label': 'To HTS number', 'positions': '19-28', 'max_length': 10},
                ],
            },
        ],
    },
    {
        'file_code': 'F111',
        'title': 'FIRMS codes',
        'summary': 'CBP facility where the goods are located. Reported on the entry summary 20-record, the X10 record and the SE11 record.',
        'spec': 'ERF-30 to ERF-35',
        'app_in': 'FQ',
        'app_out': 'FO',
        'modes': [
            {
                'id': 'CODE',
                'label': 'One code',
                'admin_only': False,
                'help': '4 letters or digits, positions 5-8. Positions 9-51 stay blank.',
                'fields': [
                    {'name': 'firms_code', 'label': 'FIRMS code', 'positions': '5-8', 'max_length': 4},
                ],
            },
            {
                'id': 'LIST',
                'label': 'List of codes',
                'admin_only': False,
                'help': 'One F111 per code. Split on spaces, commas or semicolons.',
                'fields': [
                    {'name': 'codes', 'label': 'FIRMS codes', 'positions': '5-8 on each F111', 'max_length': 4000, 'multiline': True},
                ],
            },
            {
                'id': 'NAME',
                'label': 'Name and district',
                'admin_only': False,
                'help': 'Name is a left-justified prefix, positions 9-43. District is required, positions 44-45.',
                'fields': [
                    {'name': 'facility_name', 'label': 'Facility name', 'positions': '9-43', 'max_length': 35},
                    {'name': 'district', 'label': 'District code', 'positions': '44-45', 'max_length': 2},
                ],
            },
            {
                'id': 'ALL_DATE',
                'label': 'Everything since a date',
                'admin_only': True,
                'help': 'Begin date alone, positions 46-51, MMDDYY, not in the future.',
                'fields': [
                    {'name': 'begin_date', 'label': 'Begin date', 'positions': '46-51', 'max_length': 6},
                ],
            },
            {
                'id': 'ALL_DISTRICT',
                'label': 'District by district',
                'admin_only': True,
                'help': 'One F111 per district already stored from the F101 load. Optional begin date on every district.',
                'fields': [
                    {'name': 'begin_date', 'label': 'Begin date (optional)', 'positions': '46-51', 'max_length': 6},
                ],
            },
        ],
    },
]


def file_catalog() -> list[dict]:
    return FILES


def find_file(file_code: str) -> dict | None:
    code = file_code.upper()
    return next((item for item in FILES if item['file_code'] == code), None)
