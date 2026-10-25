/**
 * Regression: query validation + F411 catalog.
 * Run: npm run test:regression
 */
import { describe, expect, it } from 'vitest';
import {
  F411_ERRORS,
  beginDateIssues,
  f411Message,
  queryIssues,
  splitCodes,
  useCards,
} from './validation';

describe('REG — FIRMS query modes', () => {
  it('requires a 4 character code and lists invalid tokens', () => {
    expect(queryIssues('F111', 'CODE', { firms_code: 'E36' })).toEqual(['FIRMS code must be 4 letters or digits']);
    expect(queryIssues('F111', 'CODE', { firms_code: 'e364' })).toEqual([]);
    const listed = splitCodes('E364, e364; NO; AB');
    expect(listed.valid).toEqual(['E364']);
    expect(listed.invalid).toEqual(['NO', 'AB']);
    expect(queryIssues('F111', 'LIST', { codes: 'E364, NO' })[0]).toContain('NO');
  });

  it('requires name + district together and rejects a future date', () => {
    expect(queryIssues('F111', 'NAME', { facility_name: 'PORT LIBERTY', district: '' })[0]).toMatch(/District/);
    expect(queryIssues('F111', 'NAME', { facility_name: '', district: '46' })[0]).toMatch(/name/i);
    const today = new Date(2026, 9, 23);
    expect(beginDateIssues('123199', today)[0]).toMatch(/future/);
    expect(beginDateIssues('013200', today)[0]).toMatch(/real calendar/);
    expect(queryIssues('F111', 'ALL_DATE', { begin_date: '010100' }, today)).toEqual([]);
  });
});

describe('REG — F411 catalog', () => {
  it('keeps the ERF-36 spelling for 003', () => {
    expect(F411_ERRORS['003']).toBe('NAME AND PORT SPEICIFIED WITH FIRMS CODE');
    expect(Object.keys(F411_ERRORS)).toEqual(['001', '002', '003', '004', '005', '012', '0D6', 'F15', 'F31']);
    expect(f411Message('012')).toBe('FIRMS CODE NOT ON FILE');
    expect(f411Message('F31')).toBe('INVALID OR FUTURE DATE');
  });
});

describe('REG — every extract file, not FIRMS only', () => {
  it('accepts full-file F101/F102/F104 and F106 air', () => {
    expect(queryIssues('F101', 'FULL', {})).toEqual([]);
    expect(queryIssues('F102', 'FULL', {})).toEqual([]);
    expect(queryIssues('F104', 'FULL', {})).toEqual([]);
    expect(queryIssues('F106', 'AIR', {})).toEqual([]);
    expect(queryIssues('F106', 'CODE', { carrier_code: 'X' })[0]).toMatch(/Carrier code/);
    expect(queryIssues('F106', 'NAME', { carrier_name: '' })[0]).toMatch(/Carrier name/);
  });

  it('accepts a blank F110 range and rejects a bad HTS shape', () => {
    expect(queryIssues('F110', 'RANGE', {})).toEqual([]);
    expect(queryIssues('F110', 'RANGE', { from_number: '!!' })[0]).toMatch(/HTS/);
  });
});

describe('REG — response layout switch', () => {
  it('uses cards at 10 rows and a table at 11', () => {
    expect(useCards(1)).toBe(true);
    expect(useCards(10)).toBe(true);
    expect(useCards(11)).toBe(false);
    expect(useCards(0)).toBe(false);
  });
});
