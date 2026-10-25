import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { EDI_VAULT_CHROME, EDI_VAULT_EXTRACT, EDI_VAULT_TABS } from '../lib/ediVaultChrome';

const vault = vi.fn();
const vaultItem = vi.fn();
const mq = vi.fn();
const usage = vi.fn();
const checkVaultItem = vi.fn();
const downloadVaultItem = vi.fn();
const { copyEdi } = vi.hoisted(() => ({ copyEdi: vi.fn() }));

vi.mock('../lib/ediVaultChrome', async () => {
  const actual = await vi.importActual<typeof import('../lib/ediVaultChrome')>('../lib/ediVaultChrome');
  return {
    ...actual,
    copyEdi: (...args: unknown[]) => copyEdi(...args),
  };
});

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api');
  return {
    ...actual,
    api: {
      ...actual.api,
      vault: (...args: unknown[]) => vault(...args),
      vaultItem: (...args: unknown[]) => vaultItem(...args),
      mq: (...args: unknown[]) => mq(...args),
      usage: (...args: unknown[]) => usage(...args),
      checkVaultItem: (...args: unknown[]) => checkVaultItem(...args),
      downloadVaultItem: (...args: unknown[]) => downloadVaultItem(...args),
    },
  };
});

import VaultScreen from './VaultScreen';

const filing = {
  id: 'req-1',
  filename: '2TGFEC9WQDMLKMFSFASI.edi',
  status: 'DRAFT',
  action: 'F111',
  file_code: 'F111',
  query_type: 'VAULT',
  control_id: '2TGFEC9WQDMLKMFSFASI',
  kn_number: '',
  mq_send_state: 'FAILED',
  mq_send_error: 'queue down',
  request_id: 'req-1',
  editable: true,
  edit_locked_reason: null,
  edi: 'A2809S1F      101826     FQ                                                     ',
  records: [{ id: 'A', label: 'Batch', text: 'A2809S1F', length: 80, ok: true }],
  envelope: 'queue://CBP.OUT.EXTRACT.QUERY',
};

describe('VaultScreen', () => {
  beforeEach(() => {
    mq.mockResolvedValue({
      mode: 'mock',
      outbound_queue: 'CBP.OUT.EXTRACT.QUERY',
      inbound_queue: 'CBP.IN.EXTRACT.RESPONSE',
      reachable: true,
      detail: 'ok',
      ttl_ms: 86400000,
      priority: 5,
    });
    vault.mockResolvedValue({
      filings: [filing],
      outbox: [],
      requests: [filing],
      orphans: [{ id: 'o1', control_id: 'ORPHANCONTROLID00001', kn_number: '', raw_text: 'FO', received_at: null }],
      dead_letters: [filing],
    });
    vaultItem.mockResolvedValue(filing);
    usage.mockResolvedValue({ events: [], total_events: 0, total_quantity: 0 });
    checkVaultItem.mockResolvedValue({
      ok: true,
      errors: [],
      rule_errors: [],
      edi: filing.edi,
      records: filing.records,
      line_count: 1,
      all_80: true,
    });
    downloadVaultItem.mockReset();
    downloadVaultItem.mockResolvedValue(undefined);
    copyEdi.mockReset();
    copyEdi.mockResolvedValue(undefined);
  });

  async function openEdiTab(user = userEvent.setup()) {
    await user.click(await screen.findByRole('button', { name: 'EDI vault' }));
    return user;
  }

  it('opens on the 5106-style MQ connection tab', async () => {
    sessionStorage.setItem('extract-demo-user', 'operator');
    render(<MemoryRouter><VaultScreen /></MemoryRouter>);
    expect(await screen.findByRole('button', { name: 'TEST CONNECTION' })).toBeInTheDocument();
    expect(screen.getByText('REACHABLE')).toBeInTheDocument();
    expect(screen.getByText(/mock · CBP\.OUT\.EXTRACT\.QUERY/)).toBeInTheDocument();
    expect(screen.getByText('Host')).toBeInTheDocument();
    expect(screen.queryByText('ADD EDI')).not.toBeInTheDocument();
  });

  it('hides unmatched responses from an operator and lists vault EDI', async () => {
    sessionStorage.setItem('extract-demo-user', 'operator');
    render(<MemoryRouter><VaultScreen /></MemoryRouter>);
    await openEdiTab();
    expect(await screen.findByText('2TGFEC9WQDMLKMFSFASI.edi')).toBeInTheDocument();
    expect(screen.getByText('ADD EDI')).toBeInTheDocument();
    expect(screen.queryByText('Unmatched responses')).not.toBeInTheDocument();
  });

  it('shows unmatched responses to an admin', async () => {
    sessionStorage.setItem('extract-demo-user', 'admin');
    render(<MemoryRouter><VaultScreen /></MemoryRouter>);
    await openEdiTab();
    expect(await screen.findByText('Unmatched responses')).toBeInTheDocument();
    expect(screen.getByText('ORPHANCONTROLID00001')).toBeInTheDocument();
  });

  it('opens the editor when adding EDI', async () => {
    sessionStorage.setItem('extract-demo-user', 'admin');
    render(<MemoryRouter><VaultScreen /></MemoryRouter>);
    const user = await openEdiTab();
    await user.click(await screen.findByText('ADD EDI'));
    expect(screen.getByText('EDI add')).toBeInTheDocument();
    expect(screen.getByText('CHECK EDI')).toBeInTheDocument();
    expect(screen.getByText('SAVE EDI')).toBeInTheDocument();
    expect(screen.getByText(/Position 1 of 80/)).toBeInTheDocument();
    await user.click(screen.getByText('CHECK EDI'));
    expect(checkVaultItem).toHaveBeenCalled();
    expect(await screen.findByText(/EDI checks out/)).toBeInTheDocument();
  });

  it('edits an existing vault item', async () => {
    sessionStorage.setItem('extract-demo-user', 'admin');
    render(<MemoryRouter><VaultScreen /></MemoryRouter>);
    const user = await openEdiTab();
    await user.click(await screen.findByText('2TGFEC9WQDMLKMFSFASI.edi'));
    expect(await screen.findByText('EDIT EDI')).toBeInTheDocument();
    await user.click(screen.getByText('EDIT EDI'));
    expect(screen.getByText('EDI edit')).toBeInTheDocument();
    expect(screen.getByText('CHECK EDI')).toBeInTheDocument();
    expect(screen.getByText('SAVE EDI')).toBeInTheDocument();
    expect(screen.getByText(/Position /)).toBeInTheDocument();
  });

  it('shows the shared 5106 chrome plus OPEN REQUEST on a vault filing', async () => {
    sessionStorage.setItem('extract-demo-user', 'admin');
    render(<MemoryRouter><VaultScreen /></MemoryRouter>);
    const user = await openEdiTab();
    await user.click(await screen.findByText('2TGFEC9WQDMLKMFSFASI.edi'));
    expect(await screen.findByText(EDI_VAULT_CHROME.edit)).toBeInTheDocument();
    expect(screen.getByText(EDI_VAULT_CHROME.copy)).toBeInTheDocument();
    expect(screen.getByText(EDI_VAULT_CHROME.download)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: EDI_VAULT_EXTRACT.openRequest })).toHaveAttribute('href', '/requests/req-1');
    expect(screen.getByText(EDI_VAULT_EXTRACT.retry)).toBeInTheDocument();
  });

  it('copies the masked EDI and downloads the vault file', async () => {
    sessionStorage.setItem('extract-demo-user', 'operator');
    render(<MemoryRouter><VaultScreen /></MemoryRouter>);
    const user = await openEdiTab();
    await user.click(await screen.findByText('2TGFEC9WQDMLKMFSFASI.edi'));
    expect(await screen.findByRole('button', { name: EDI_VAULT_CHROME.edit })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: EDI_VAULT_CHROME.copy }));
    expect(copyEdi).toHaveBeenCalledWith(filing.edi);
    await user.click(screen.getByRole('button', { name: EDI_VAULT_CHROME.download }));
    expect(downloadVaultItem).toHaveBeenCalledWith('req-1');
  });

  it('keeps copy, download, and open request when the sent EDI is locked', async () => {
    vaultItem.mockResolvedValue({
      ...filing,
      status: 'PENDING_CBP',
      mq_send_state: 'SENT',
      editable: false,
      edit_locked_reason: 'This EDI is read-only after a successful send.',
    });
    sessionStorage.setItem('extract-demo-user', 'operator');
    render(<MemoryRouter><VaultScreen /></MemoryRouter>);
    const user = await openEdiTab();
    await user.click(await screen.findByText('2TGFEC9WQDMLKMFSFASI.edi'));
    expect(await screen.findByText(/read-only after a successful send/)).toBeInTheDocument();
    expect(screen.queryByText(EDI_VAULT_CHROME.edit)).not.toBeInTheDocument();
    expect(screen.getByText(EDI_VAULT_CHROME.copy)).toBeInTheDocument();
    expect(screen.getByText(EDI_VAULT_CHROME.download)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: EDI_VAULT_EXTRACT.openRequest })).toBeInTheDocument();
    expect(screen.queryByText(EDI_VAULT_EXTRACT.retry)).not.toBeInTheDocument();
  });

  it('hides OPEN REQUEST on an unmatched outbox file', async () => {
    vault.mockResolvedValue({
      filings: [],
      outbox: [{ ...filing, id: 'outbox-1', request_id: null, status: 'OUTBOX', query_type: 'OUTBOX' }],
      requests: [],
      orphans: [],
      dead_letters: [],
    });
    vaultItem.mockResolvedValue({
      ...filing,
      id: 'outbox-1',
      request_id: null,
      status: 'OUTBOX',
      query_type: 'OUTBOX',
    });
    sessionStorage.setItem('extract-demo-user', 'admin');
    render(<MemoryRouter><VaultScreen /></MemoryRouter>);
    const user = await openEdiTab();
    await user.click(await screen.findByText('2TGFEC9WQDMLKMFSFASI.edi'));
    expect(await screen.findByText(EDI_VAULT_CHROME.copy)).toBeInTheDocument();
    expect(screen.getByText(EDI_VAULT_CHROME.download)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: EDI_VAULT_EXTRACT.openRequest })).not.toBeInTheDocument();
  });

  it('lists extract records, not 5106 T-records, on the CATAIR tab', async () => {
    sessionStorage.setItem('extract-demo-user', 'operator');
    render(<MemoryRouter><VaultScreen /></MemoryRouter>);
    await userEvent.setup().click(await screen.findByRole('button', { name: EDI_VAULT_TABS.ref }));
    expect(await screen.findByText('F111')).toBeInTheDocument();
    expect(screen.getByText('FIRMS query')).toBeInTheDocument();
    expect(screen.queryByText('T1')).not.toBeInTheDocument();
  });
});
