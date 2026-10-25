/** 1-based CATAIR positions for vault add/edit. Mirrors backend/app/edi/layout.py. */

export interface FieldSpan {
  name: string;
  start: number;
  end: number;
}

export const RECORD_LEN = 80;

export const RECORD_FIELDS: Record<string, FieldSpan[]> = {
  A: [
    { name: 'Record', start: 1, end: 1 },
    { name: 'Site', start: 2, end: 5 },
    { name: 'Sender', start: 6, end: 8 },
    { name: 'Password', start: 9, end: 14 },
    { name: 'Date', start: 15, end: 20 },
    { name: 'Application ID', start: 26, end: 27 },
    { name: 'KN / user data', start: 60, end: 80 },
  ],
  B: [
    { name: 'Record', start: 1, end: 1 },
    { name: 'Port', start: 4, end: 7 },
    { name: 'Filer', start: 8, end: 10 },
    { name: 'Application ID', start: 11, end: 12 },
    { name: 'Preparer port', start: 47, end: 50 },
    { name: 'Preparer filer', start: 51, end: 53 },
    { name: 'Preparer flag', start: 56, end: 56 },
    { name: 'Control ID', start: 60, end: 80 },
  ],
  Y: [
    { name: 'Record', start: 1, end: 1 },
    { name: 'Port', start: 4, end: 7 },
    { name: 'Filer', start: 8, end: 10 },
    { name: 'Application ID', start: 11, end: 12 },
  ],
  Z: [
    { name: 'Record', start: 1, end: 1 },
    { name: 'Site', start: 2, end: 5 },
    { name: 'Sender', start: 6, end: 8 },
    { name: 'Date', start: 15, end: 20 },
  ],
  F101: [{ name: 'Record', start: 1, end: 4 }, { name: 'District / port', start: 5, end: 9 }],
  F102: [{ name: 'Record', start: 1, end: 4 }, { name: 'Country', start: 5, end: 6 }],
  F104: [{ name: 'Record', start: 1, end: 4 }, { name: 'Schedule K', start: 5, end: 9 }],
  F106: [
    { name: 'Record', start: 1, end: 4 },
    { name: 'Carrier name', start: 5, end: 39 },
    { name: 'Carrier code', start: 40, end: 43 },
  ],
  F110: [
    { name: 'Record', start: 1, end: 4 },
    { name: 'Update number', start: 5, end: 8 },
    { name: 'From HTS', start: 9, end: 18 },
    { name: 'To HTS', start: 19, end: 28 },
    { name: 'Narrative', start: 29, end: 80 },
  ],
  F111: [
    { name: 'Record', start: 1, end: 4 },
    { name: 'FIRMS code', start: 5, end: 8 },
    { name: 'Facility name', start: 9, end: 43 },
    { name: 'District', start: 44, end: 45 },
    { name: 'Begin date', start: 46, end: 51 },
  ],
  F211: [
    { name: 'Record', start: 1, end: 4 },
    { name: 'District / port', start: 5, end: 8 },
    { name: 'FIRMS code', start: 9, end: 12 },
    { name: 'Status', start: 13, end: 13 },
    { name: 'Facility type', start: 14, end: 15 },
    { name: 'Name', start: 16, end: 50 },
    { name: 'Last update', start: 51, end: 56 },
  ],
  F311: [
    { name: 'Record', start: 1, end: 4 },
    { name: 'Address', start: 5, end: 39 },
    { name: 'City', start: 40, end: 74 },
    { name: 'State', start: 75, end: 76 },
  ],
  F411: [
    { name: 'Record', start: 1, end: 4 },
    { name: 'ZIP', start: 5, end: 13 },
    { name: 'Country', start: 14, end: 15 },
    { name: 'Error code', start: 33, end: 35 },
    { name: 'Error message', start: 36, end: 75 },
  ],
};

const KNOWN_FOUR = Object.keys(RECORD_FIELDS).filter((id) => id.length === 4);

export function recordId(line: string): string {
  const text = unbracketLine(line);
  const four = text.slice(0, 4);
  if (KNOWN_FOUR.includes(four)) return four;
  return text.slice(0, 1);
}

export function unbracketLine(line: string): string {
  return line.replace(/^\s*\[/, '').replace(/\]\s*$/, '');
}

export function fieldsFor(record: string): FieldSpan[] {
  return RECORD_FIELDS[record] || [{ name: 'Record', start: 1, end: RECORD_LEN }];
}

export function fieldAt(record: string, position: number): FieldSpan | null {
  return fieldsFor(record).find((field) => position >= field.start && position <= field.end) || null;
}

export function fieldLegend(record: string): string {
  return fieldsFor(record).map((field) => `${field.start}-${field.end} ${field.name}`).join(' · ');
}

export function rulerText(indent = 0): string {
  const pad = ' '.repeat(indent);
  const nums = Array.from({ length: 8 }, (_, i) => String((i + 1) * 10).padStart(10)).join('');
  const ticks = ('.'.repeat(9) + '|').repeat(8);
  return `${pad}${nums}\n${pad}${ticks}`;
}

export interface CursorInfo {
  line: number;
  position: number;
  length: number;
  record: string;
  field: FieldSpan | null;
}

export function cursorInfo(text: string, caret: number): CursorInfo {
  const safe = Math.max(0, Math.min(caret, text.length));
  const before = text.slice(0, safe);
  const line = before.split('\n').length;
  const rawLine = text.split('\n')[line - 1] || '';
  const offset = safe - (before.lastIndexOf('\n') + 1);
  const skip = rawLine.match(/^\s*\[/)?.[0].length || 0;
  const contentLen = unbracketLine(rawLine).length;
  let position = Math.max(1, offset - skip);
  if (rawLine.trimEnd().endsWith(']') && position > contentLen) position = Math.max(1, contentLen);
  const record = recordId(rawLine);
  return {
    line,
    position,
    length: contentLen,
    record,
    field: fieldAt(record, position),
  };
}

export function formatCursor(info: CursorInfo): string {
  const field = info.field ? `${info.field.name} (${info.field.start}-${info.field.end})` : 'unmapped';
  return `Line ${info.line} · Position ${info.position} of ${RECORD_LEN} · ${info.record} ${field} · line length ${info.length}`;
}
