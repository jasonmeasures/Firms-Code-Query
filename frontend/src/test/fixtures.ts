import type { ExtractRequest, FileSpec } from '../api';

export const F111: FileSpec = {
  file_code: 'F111',
  title: 'FIRMS codes',
  summary: 'CBP facility where the goods are located.',
  spec: 'ERF-30 to ERF-35',
  app_in: 'FQ',
  app_out: 'FO',
  modes: [
    {
      id: 'CODE',
      label: 'One code',
      admin_only: false,
      help: '4 letters or digits, positions 5-8.',
      fields: [{ name: 'firms_code', label: 'FIRMS code', positions: '5-8', max_length: 4 }],
    },
    {
      id: 'LIST',
      label: 'List of codes',
      admin_only: false,
      help: 'Split on spaces, commas or semicolons.',
      fields: [{ name: 'codes', label: 'FIRMS codes', positions: '5-8 on each F111', max_length: 4000, multiline: true }],
    },
    {
      id: 'ALL_DATE',
      label: 'Everything since a date',
      admin_only: true,
      help: 'Begin date alone.',
      fields: [{ name: 'begin_date', label: 'Begin date', positions: '46-51', max_length: 6 }],
    },
  ],
};

export function request(overrides: Partial<ExtractRequest> = {}): ExtractRequest {
  return {
    id: 'req-1',
    control_id: '2TGFEC9WQDMLKMFSFASI',
    kn_number: '',
    file_code: 'F111',
    query_type: 'CODE',
    params: { firms_code: 'E364' },
    status: 'PENDING_CBP',
    mq_send_state: 'SENT',
    mq_send_error: null,
    requested_by: 'operator',
    job_id: null,
    created_at: '2026-10-23T12:00:00.000Z',
    submitted_at: '2026-10-23T12:00:01.000Z',
    updated_at: '2026-10-23T12:00:01.000Z',
    timeline: [],
    edi: 'A2809S1F      101826     FQ                                                     ',
    response: null,
    ...overrides,
  };
}

export function facilityRow(index: number) {
  return {
    kind: 'facility',
    firms_code: `E${String(index).padStart(3, '0')}`,
    facility_name: `FACILITY ${index}`,
    status: 'A',
    status_label: 'Active',
    facility_type: 'Pier',
    district_port: '4601',
    address: '1 MAIN',
    city: 'JERSEY CITY',
    state: 'NJ',
    zip: '07305',
    country: 'US',
  };
}
