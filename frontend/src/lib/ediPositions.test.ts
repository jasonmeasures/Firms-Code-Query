import { describe, expect, it } from 'vitest';
import { cursorInfo, fieldAt, fieldLegend, recordId } from './ediPositions';

describe('ediPositions', () => {
  it('maps an F111 FIRMS code column', () => {
    expect(recordId('[F111E364]')).toBe('F111');
    expect(fieldAt('F111', 6)?.name).toBe('FIRMS code');
    expect(fieldLegend('F111')).toContain('5-8 FIRMS code');
  });

  it('reports the caret against 1-based record positions', () => {
    const line = 'F111E364                                                                        ';
    const info = cursorInfo(line, 6);
    expect(info.line).toBe(1);
    expect(info.position).toBe(6);
    expect(info.record).toBe('F111');
    expect(info.field?.name).toBe('FIRMS code');
  });

  it('skips a leading bracket so pasted blocks stay on CATAIR columns', () => {
    const info = cursorInfo('[F111E364]', 6);
    expect(info.position).toBe(5);
    expect(info.field?.name).toBe('FIRMS code');
  });

  it('does not count a closing bracket as position 81', () => {
    const line = `[${'F111E364'.padEnd(80)}]`;
    const info = cursorInfo(line, line.length);
    expect(info.position).toBe(80);
    expect(info.length).toBe(80);
  });
});
