/** Phase 2 client mirror of backend/app/services/entry.py */

import { firmsCodeValid } from './validation';

export const ENTRY_SOURCES = {
  AE20: 'AE 20-record location',
  SE11: 'SE11 FIRMS',
  X10: 'X10 FIRMS',
  SE20_CES: 'SE20 qualifier CES',
  SE20_LOC: 'SE20 qualifier LOC',
} as const;

export type EntrySource = keyof typeof ENTRY_SOURCES;

export interface EntryFacility {
  status: string;
  facility_type: string;
  name?: string;
}

export interface EntryCheck {
  source: string;
  source_label: string;
  firms_code: string;
  allowed: boolean;
  severity: 'ok' | 'warning' | 'error';
  code: 'OK' | 'INVALID' | 'NOT_ON_FILE' | 'DEACTIVATED' | 'ENTRY_TYPE' | 'UNKNOWN_SOURCE';
  message: string;
}

export function validateFacilityForEntry(
  facility: EntryFacility | null,
  firmsCode: string,
  source: string = 'AE20',
): EntryCheck {
  const code = firmsCode.trim().toUpperCase();
  const key = source.toUpperCase() as EntrySource;
  const label = ENTRY_SOURCES[key];
  if (!label) {
    return {
      source: key,
      source_label: key,
      firms_code: code,
      allowed: false,
      severity: 'error',
      code: 'UNKNOWN_SOURCE',
      message: `Unknown entry source ${key}`,
    };
  }
  if (!firmsCodeValid(code)) {
    return {
      source: key,
      source_label: label,
      firms_code: code,
      allowed: false,
      severity: 'error',
      code: 'INVALID',
      message: 'FIRMS code must be 4 letters or digits',
    };
  }
  if (!facility) {
    return {
      source: key,
      source_label: label,
      firms_code: code,
      allowed: false,
      severity: 'error',
      code: 'NOT_ON_FILE',
      message: `${label}: FIRMS ${code} is not on the local reference file`,
    };
  }
  const deactivated = facility.status === 'D' || facility.status === 'Deactivated';
  if (deactivated) {
    return {
      source: key,
      source_label: label,
      firms_code: code,
      allowed: false,
      severity: 'error',
      code: 'DEACTIVATED',
      message: `${label}: FIRMS ${code} is deactivated and cannot be used on an entry`,
    };
  }
  if (facility.facility_type === '07' || facility.facility_type === '08') {
    return {
      source: key,
      source_label: label,
      firms_code: code,
      allowed: true,
      severity: 'warning',
      code: 'ENTRY_TYPE',
      message: `${label}: Facility types 07 and 08 must not be used for entry purposes.`,
    };
  }
  return {
    source: key,
    source_label: label,
    firms_code: code,
    allowed: true,
    severity: 'ok',
    code: 'OK',
    message: `${label}: FIRMS ${code} is active`,
  };
}
