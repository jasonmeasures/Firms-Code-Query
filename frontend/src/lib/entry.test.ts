import { describe, expect, it } from 'vitest';
import { ENTRY_SOURCES, validateFacilityForEntry } from './entry';

describe('phase 2 entry validation', () => {
  it('exposes the five entry sources', () => {
    expect(Object.keys(ENTRY_SOURCES)).toEqual(['AE20', 'SE11', 'X10', 'SE20_CES', 'SE20_LOC']);
  });

  it('blocks unknown and deactivated codes', () => {
    expect(validateFacilityForEntry(null, 'ZZZZ', 'SE11').code).toBe('NOT_ON_FILE');
    expect(validateFacilityForEntry({ status: 'D', facility_type: '03' }, 'E364', 'AE20').allowed).toBe(false);
    expect(validateFacilityForEntry({ status: 'Deactivated', facility_type: '03' }, 'E364', 'X10').code).toBe('DEACTIVATED');
  });

  it('warns on types 07 and 08 without blocking', () => {
    const warn = validateFacilityForEntry({ status: 'A', facility_type: '07' }, 'DATA', 'SE20_CES');
    expect(warn.allowed).toBe(true);
    expect(warn.severity).toBe('warning');
    expect(warn.code).toBe('ENTRY_TYPE');
  });

  it('allows an active pier on AE20', () => {
    const ok = validateFacilityForEntry({ status: 'A', facility_type: '03' }, 'e364', 'AE20');
    expect(ok).toMatchObject({ allowed: true, severity: 'ok', code: 'OK', firms_code: 'E364' });
  });
});
