"""F411 catalog from ERF-36. Every published code must parse."""

import pytest

from app.edi.layout import F411_ERRORS
from app.edi.parse import parse_response

REQUIRED = ['001', '002', '003', '004', '005', '012', '0D6', 'F15', 'F31']


def _rejection(code: str, echo: str = 'F111ZZZZ', message: str = '') -> str:
    echoed = echo.ljust(80)
    text = message or F411_ERRORS[code]
    error = ('F411'.ljust(32) + code + text.ljust(40))[:80].ljust(80)
    assert len(error) == 80
    return f'{echoed}\n{error}'


def test_catalog_has_every_published_code():
    assert list(F411_ERRORS) == REQUIRED
    assert F411_ERRORS['003'] == 'NAME AND PORT SPEICIFIED WITH FIRMS CODE'


@pytest.mark.parametrize('code', REQUIRED)
def test_parse_each_f411_code(code):
    parsed = parse_response(_rejection(code))
    assert len(parsed.rows) == 1
    row = parsed.rows[0]
    assert row['kind'] == 'rejection'
    assert row['error_code'] == code
    assert row['firms_code'] == 'ZZZZ'
    assert F411_ERRORS[code] in row['error_message']
    assert row['error_label'] == F411_ERRORS[code]


def test_blank_ace_message_uses_catalog():
    parsed = parse_response(_rejection('F15', message=' '))
    assert parsed.rows[0]['error_code'] == 'F15'
    assert parsed.rows[0]['error_message'] == F411_ERRORS['F15']
