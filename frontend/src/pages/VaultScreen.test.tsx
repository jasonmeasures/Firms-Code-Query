import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { request } from '../test/fixtures';

const vault = vi.fn();
const mq = vi.fn();

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api');
  return {
    ...actual,
    api: {
      ...actual.api,
      vault: (...args: unknown[]) => vault(...args),
      mq: (...args: unknown[]) => mq(...args),
    },
  };
});

import VaultScreen from './VaultScreen';

describe('VaultScreen', () => {
  beforeEach(() => {
    mq.mockResolvedValue({
      mode: 'mock',
      outbound_queue: 'CBP.OUT.EXTRACT.QUERY',
      inbound_queue: 'CBP.IN.EXTRACT.RESPONSE',
      reachable: true,
      detail: 'ok',
    });
    vault.mockResolvedValue({
      requests: [request({ mq_send_state: 'FAILED', mq_send_error: 'queue down' })],
      orphans: [{ id: 'o1', control_id: 'ORPHANCONTROLID00001', kn_number: '', raw_text: 'FO', received_at: null }],
      dead_letters: [request({ mq_send_state: 'FAILED', mq_send_error: 'queue down' })],
    });
  });

  it('hides dead letters and orphans from an operator', async () => {
    sessionStorage.setItem('extract-demo-user', 'operator');
    render(<MemoryRouter><VaultScreen /></MemoryRouter>);
    expect(await screen.findByText('2TGFEC9WQDMLKMFSFASI')).toBeInTheDocument();
    expect(screen.queryByText('Failed sends')).not.toBeInTheDocument();
    expect(screen.queryByText('Unmatched responses')).not.toBeInTheDocument();
  });

  it('shows the local dead-letter list to an admin', async () => {
    sessionStorage.setItem('extract-demo-user', 'admin');
    render(<MemoryRouter><VaultScreen /></MemoryRouter>);
    expect(await screen.findByText('Failed sends')).toBeInTheDocument();
    expect(screen.getByText('Unmatched responses')).toBeInTheDocument();
    expect(screen.getByText('ORPHANCONTROLID00001')).toBeInTheDocument();
    expect(screen.getByText(/queue down/)).toBeInTheDocument();
  });
});
