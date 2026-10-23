import { describe, expect, it } from 'vitest';
import { echoMatches, firmsCodeValid, statusClass } from './status';

describe('status words', () => {
  it('uses the same status classes for every reference file', () => {
    expect(statusClass('APPROVED')).toBe('kn-status-APPROVED');
    expect(statusClass('PENDING_CBP')).toBe('kn-status-PENDING_CBP');
    expect(statusClass('DRAFT')).toBe('kn-status-DRAFT');
  });

  it('compares the echoed control id', () => {
    expect(echoMatches('ABC', 'ABC')).toBe('match');
    expect(echoMatches('ABC', 'ABD')).toBe('differ');
    expect(echoMatches('', 'ABC')).toBe('empty');
  });

  it('requires a 4 character FIRMS code', () => {
    expect(firmsCodeValid('E364')).toBe(true);
    expect(firmsCodeValid('e364')).toBe(true);
    expect(firmsCodeValid('E36')).toBe(false);
    expect(firmsCodeValid('E36-')).toBe(false);
  });
});
