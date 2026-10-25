const API = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

const ROLE_KEY = 'extract-demo-user';

export function demoUser(): string {
  return sessionStorage.getItem(ROLE_KEY) || 'operator';
}

export function setDemoUser(id: string) {
  sessionStorage.setItem(ROLE_KEY, id);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set('X-Demo-User', demoUser());
  if (init?.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const res = await fetch(`${API}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = Array.isArray(body.detail) ? body.detail.join(' ') : body.detail || detail;
    } catch {
      /* keep status text */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  const type = res.headers.get('content-type') || '';
  if (type.includes('text/csv') || type.includes('text/plain')) return (await res.text()) as T;
  return res.json() as Promise<T>;
}

async function downloadVaultItem(id: string): Promise<void> {
  const headers = new Headers();
  headers.set('X-Demo-User', demoUser());
  const res = await fetch(`${API}/api/extract/vault/${encodeURIComponent(id)}/download`, { headers });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const detail = (data as { detail?: unknown }).detail;
    throw new Error(Array.isArray(detail) ? detail.join(' ') : String(detail || res.statusText));
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  const disposition = res.headers.get('Content-Disposition') || '';
  const match = /filename="([^"]+)"/.exec(disposition);
  link.href = url;
  link.download = match?.[1] || `${id}.edi`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  files: () => request<{ files: FileSpec[] }>('/api/extract/files'),
  me: () => request<Me>('/api/extract/me'),
  preview: (body: QueryPayload) => request<Preview>('/api/extract/preview', { method: 'POST', body: JSON.stringify(body) }),
  submit: (body: QueryPayload) => request<{ request: ExtractRequest; job?: Job }>('/api/extract/queries', { method: 'POST', body: JSON.stringify(body) }),
  requests: (q = '') => request<{ requests: ExtractRequest[] }>(`/api/extract/requests?q=${encodeURIComponent(q)}`),
  request: (id: string) => request<ExtractRequest>(`/api/extract/requests/${id}`),
  csv: (id: string) => request<string>(`/api/extract/requests/${id}/csv`),
  retry: (id: string, confirm = false) =>
    request<ExtractRequest>(`/api/extract/requests/${id}/retry?confirm_possible_duplicate=${confirm}`, { method: 'POST' }),
  devResponse: (id: string, message: string) =>
    request<ExtractRequest>(`/api/extract/requests/${id}/dev-response`, { method: 'POST', body: JSON.stringify({ message }) }),
  job: (id: string) => request<Job>(`/api/extract/jobs/${id}`),
  resume: (id: string) => request<Job>(`/api/extract/jobs/${id}/resume`, { method: 'POST' }),
  summary: () => request<Summary>('/api/extract/reference/summary'),
  firms: (query: string) => request<{ rows: Facility[] }>(`/api/extract/reference/firms?${query}`),
  changes: () => request<{ changes: Change[] }>('/api/extract/reference/firms/changes'),
  ports: (q = '') => request<{ rows: Named[] }>(`/api/extract/reference/ports?q=${encodeURIComponent(q)}`),
  countries: (q = '') => request<{ rows: Country[] }>(`/api/extract/reference/countries?q=${encodeURIComponent(q)}`),
  foreignPorts: (q = '') => request<{ rows: Named[] }>(`/api/extract/reference/foreign-ports?q=${encodeURIComponent(q)}`),
  carriers: (q = '') => request<{ rows: Carrier[] }>(`/api/extract/reference/carriers?q=${encodeURIComponent(q)}`),
  vault: () => request<Vault>('/api/extract/vault'),
  vaultItem: (id: string) => request<VaultItem>(`/api/extract/vault/${encodeURIComponent(id)}`),
  addVaultItem: (edi: string) =>
    request<VaultItem>('/api/extract/vault', { method: 'POST', body: JSON.stringify({ edi }) }),
  checkVaultItem: (edi: string) =>
    request<VaultCheck>('/api/extract/vault/check', { method: 'POST', body: JSON.stringify({ edi }) }),
  saveVaultItem: (id: string, edi: string) =>
    request<VaultItem>(`/api/extract/vault/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify({ edi }) }),
  downloadVaultItem: (id: string) => downloadVaultItem(id),
  mq: () => request<MqStatus>('/api/extract/mq/status'),
  mqTest: (body: Partial<MqStatus> = {}) =>
    request<{ ok: boolean; status: MqStatus }>('/api/extract/mq/test', { method: 'POST', body: JSON.stringify(body) }),
  usage: () => request<UsageSummary>('/api/extract/usage'),
  validateFirms: (locations: { firms_code: string; source: string }[]) =>
    request<EntryValidation>('/api/extract/reference/firms/validate', {
      method: 'POST',
      body: JSON.stringify({ locations }),
    }),
};

export interface FieldSpec {
  name: string;
  label: string;
  positions: string;
  max_length: number;
  multiline?: boolean;
}

export interface ModeSpec {
  id: string;
  label: string;
  admin_only: boolean;
  help: string;
  fields: FieldSpec[];
}

export interface FileSpec {
  file_code: string;
  title: string;
  summary: string;
  spec: string;
  app_in: string;
  app_out: string;
  modes: ModeSpec[];
}

export interface Me { id: string; name: string; role: 'ADMIN' | 'OPERATOR' }

export interface QueryPayload {
  file_code: string;
  query_type: string;
  params: Record<string, string>;
  kn_number?: string;
  control_id?: string;
}

export interface Preview {
  edi: string;
  line_count: number;
  all_80: boolean;
  kn_number: string;
  control_id: string;
  app_id: string;
}

export interface TimelineItem {
  from_status: string | null;
  to_status: string;
  changed_at: string | null;
  changed_by: string | null;
  notes: string | null;
}

export interface ExtractRequest {
  id: string;
  control_id: string;
  kn_number: string;
  file_code: string;
  query_type: string;
  params: Record<string, string>;
  status: string;
  mq_send_state: string | null;
  mq_send_error: string | null;
  requested_by: string;
  job_id: string | null;
  created_at: string | null;
  submitted_at: string | null;
  updated_at: string | null;
  timeline: TimelineItem[];
  edi?: string;
  response?: {
    raw_text: string;
    parsed: Parsed | null;
    received_at: string | null;
    parse_errors: string | null;
  } | null;
}

export interface Parsed {
  kn_number: string;
  control_id: string;
  application_id: string;
  file_code: string;
  rows: Array<Record<string, unknown>>;
  unrecognized: string[];
  warnings: string[];
}

export interface Job {
  id: string;
  file_code: string;
  query_type: string;
  status: string;
  total: number;
  pending: number;
  approved: number;
  rejected: number;
  failed: number;
  requests: ExtractRequest[];
}

export interface Summary {
  role: string;
  files: { file_code: string; count: number; last_pull: string | null; last_control_id: string | null }[];
}

export interface Facility {
  firms_code: string;
  district_port: string;
  status: string;
  facility_type: string;
  name: string;
  last_update: string;
  address: string;
  city: string;
  state: string;
  zip: string;
  country: string;
}

export interface Change {
  firms_code: string;
  change_type: string;
  field_name: string;
  old_value: string;
  new_value: string;
  changed_at: string | null;
  source_control_id: string | null;
}

export interface Named { code: string; name: string; city?: string; state?: string; zip?: string }
export interface Country { iso: string; name: string; spi: string }
export interface Carrier { code: string; name: string; mode: string; mode_name: string }
export interface VaultCheck {
  ok: boolean;
  errors: string[];
  rule_errors: string[];
  edi: string;
  records: VaultRecord[];
  line_count: number;
  all_80: boolean;
}
export interface VaultRecord {
  id: string;
  label: string;
  text: string;
  length: number;
  ok: boolean;
}

export interface VaultItem {
  id: string;
  filename: string;
  edi_filename?: string;
  status: string;
  action: string;
  file_code: string;
  query_type: string;
  control_id: string;
  kn_number: string;
  mq_send_state: string | null;
  mq_send_error: string | null;
  request_id: string | null;
  editable: boolean;
  edit_locked_reason: string | null;
  edi?: string;
  edi_raw?: string;
  records?: VaultRecord[];
  envelope?: string;
  /** ERF findings. Scratch/orphan saves still succeed; sendable edits are blocked. */
  warnings?: string[];
}

export interface Vault {
  filings: VaultItem[];
  outbox: VaultItem[];
  requests: VaultItem[];
  orphans: { id: string; control_id: string | null; kn_number: string | null; raw_text: string; received_at: string | null }[];
  dead_letters: VaultItem[];
}
export interface EntryValidation {
  ok: boolean;
  blocked: Array<Record<string, unknown>>;
  warnings: Array<Record<string, unknown>>;
  results: Array<Record<string, unknown>>;
}
export interface UsageSummary {
  events: { event_type: string; unit: string; count: number; quantity: number }[];
  total_events: number;
  total_quantity: number;
}
export interface MqStatus {
  mode: string;
  outbound_queue: string;
  inbound_queue: string;
  reachable: boolean;
  detail: string;
  host?: string;
  port?: string;
  queue_manager?: string;
  channel?: string;
  priority?: number;
  ttl_ms?: number;
  outbox_count?: number;
}
