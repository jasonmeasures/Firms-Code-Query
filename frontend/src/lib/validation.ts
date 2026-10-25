/** Client rules that mirror backend/app/edi/build.py and ERF-36. */

export const FIRMS_CODE_RE = /^[A-Z0-9]{4}$/;
export const DISTRICT_RE = /^\d{2}$/;
export const DATE_RE = /^\d{6}$/;
export const CARD_TABLE_THRESHOLD = 10;

export const F411_ERRORS: Record<string, string> = {
  '001': 'NAME SPECIFIED WITH FIRMS CODE',
  '002': 'PORT SPECIFIED WITH FIRMS CODE',
  '003': 'NAME AND PORT SPEICIFIED WITH FIRMS CODE',
  '004': 'PORT REQUIRED IF FACILITY NAME SPECIFIED',
  '005': 'STREET ADDRESS NOT ON FILE',
  '012': 'FIRMS CODE NOT ON FILE',
  '0D6': 'FACILITY NAME NOT ON FILE',
  'F15': 'INVALID FIRMS CODE',
  'F31': 'INVALID OR FUTURE DATE',
};

export function firmsCodeValid(value: string): boolean {
  return FIRMS_CODE_RE.test(value.trim().toUpperCase());
}

export function districtValid(value: string): boolean {
  return DISTRICT_RE.test(value.trim());
}

export function splitCodes(raw: string): { valid: string[]; invalid: string[] } {
  const tokens = (raw || '').split(/[\s,;]+/).map((part) => part.trim().toUpperCase()).filter(Boolean);
  const seen = new Set<string>();
  const valid: string[] = [];
  const invalid: string[] = [];
  for (const token of tokens) {
    if (seen.has(token)) continue;
    seen.add(token);
    if (FIRMS_CODE_RE.test(token)) valid.push(token);
    else invalid.push(token);
  }
  return { valid, invalid };
}

export function beginDateIssues(value: string, today = new Date()): string[] {
  const text = (value || '').trim();
  if (!DATE_RE.test(text)) return ['Begin date must be MMDDYY'];
  const month = Number(text.slice(0, 2));
  const day = Number(text.slice(2, 4));
  const year = 2000 + Number(text.slice(4, 6));
  const parsed = new Date(year, month - 1, day);
  if (parsed.getFullYear() !== year || parsed.getMonth() !== month - 1 || parsed.getDate() !== day) {
    return ['Begin date is not a real calendar date'];
  }
  const clock = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  if (parsed > clock) return ['Begin date cannot be in the future'];
  return [];
}

export function queryIssues(fileCode: string, queryType: string, params: Record<string, string>, today = new Date()): string[] {
  if (fileCode === 'F111' && queryType === 'CODE') {
    const code = (params.firms_code || '').trim();
    if (!firmsCodeValid(code)) return ['FIRMS code must be 4 letters or digits'];
    return [];
  }
  if (fileCode === 'F111' && queryType === 'LIST') {
    const { valid, invalid } = splitCodes(params.codes || '');
    if (invalid.length) return [`Not valid FIRMS codes: ${invalid.slice(0, 8).join(', ')}`];
    if (!valid.length) return ['Enter at least one FIRMS code'];
    return [];
  }
  if (fileCode === 'F111' && queryType === 'NAME') {
    const issues: string[] = [];
    if (!(params.facility_name || '').trim()) issues.push('Facility name is required');
    if ((params.facility_name || '').trim().length > 35) issues.push('Facility name is longer than 35 characters');
    if (!districtValid(params.district || '')) issues.push('District code must be 2 digits');
    return issues;
  }
  if (fileCode === 'F111' && queryType === 'DISTRICT') {
    const issues: string[] = [];
    if (!districtValid(params.district || '')) issues.push('District code must be 2 digits');
    if ((params.begin_date || '').trim()) issues.push(...beginDateIssues(params.begin_date, today));
    return issues;
  }
  if (fileCode === 'F111' && (queryType === 'ALL_DATE')) {
    return beginDateIssues(params.begin_date || '', today);
  }
  if (fileCode === 'F111' && queryType === 'ALL_DISTRICT' && (params.begin_date || '').trim()) {
    return beginDateIssues(params.begin_date, today);
  }
  if (fileCode === 'F106' && queryType === 'CODE') {
    const code = (params.carrier_code || '').trim().toUpperCase();
    if (!/^[A-Z0-9]{2,4}$/.test(code)) return ['Carrier code must be 2 to 4 letters or digits'];
    return [];
  }
  if (fileCode === 'F106' && queryType === 'NAME') {
    const name = (params.carrier_name || '').trim();
    if (!name) return ['Carrier name is required'];
    if (name.length > 35) return ['Carrier name is longer than 35 characters'];
    return [];
  }
  if (fileCode === 'F106' && (queryType === 'AIR' || queryType === 'AIR_ALL')) {
    return [];
  }
  if (fileCode === 'F110' && queryType === 'RANGE') {
    const issues: string[] = [];
    const update = (params.update_number || '').trim();
    const fromHts = (params.from_number || params.from_hts || '').trim().toUpperCase();
    const toHts = (params.to_number || params.to_hts || '').trim().toUpperCase();
    if (update && !/^\d{1,4}$/.test(update)) issues.push('HTS update number must be 1 to 4 digits');
    if (fromHts && !/^[A-Z0-9]{1,10}$/.test(fromHts)) issues.push('From HTS number must be 1 to 10 letters or digits');
    if (toHts && !/^[A-Z0-9]{1,10}$/.test(toHts)) issues.push('To HTS number must be 1 to 10 letters or digits');
    return issues;
  }
  if ((fileCode === 'F101' || fileCode === 'F102' || fileCode === 'F104') && queryType === 'FULL') {
    return [];
  }
  return [];
}

export function f411Message(code: string): string {
  return F411_ERRORS[code] || '';
}

export function useCards(rowCount: number): boolean {
  return rowCount > 0 && rowCount <= CARD_TABLE_THRESHOLD;
}
