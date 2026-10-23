import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { facilityRow, request } from '../test/fixtures';

const load = vi.fn();

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api');
  return {
    ...actual,
    api: {
      ...actual.api,
      request: (...args: unknown[]) => load(...args),
    },
  };
});

import RequestScreen from './RequestScreen';

function renderRequest() {
  return render(
    <MemoryRouter initialEntries={['/requests/req-1']}>
      <Routes>
        <Route path="/requests/:requestId" element={<RequestScreen />} />
      </Routes>
    </MemoryRouter>,
  );
}

function withRows(rows: Array<Record<string, unknown>>) {
  return request({
    status: 'APPROVED',
    response: {
      raw_text: 'FO',
      parsed: {
        kn_number: '',
        control_id: '2TGFEC9WQDMLKMFSFASI',
        application_id: 'FO',
        file_code: 'F111',
        rows,
        unrecognized: [],
        warnings: rows.length > 1 ? ['Multi-facility response'] : [],
      },
      received_at: '2026-10-23T12:00:10.000Z',
      parse_errors: null,
    },
  });
}

describe('RequestScreen', () => {
  beforeEach(() => {
    sessionStorage.setItem('extract-demo-user', 'operator');
  });

  it('shows a Port Liberty card for a single facility', async () => {
    load.mockResolvedValue(withRows([{
      ...facilityRow(364),
      firms_code: 'E364',
      facility_name: 'PORT LIBERTY - BAYONNE',
    }]));
    renderRequest();
    expect(await screen.findByText('PORT LIBERTY - BAYONNE')).toBeInTheDocument();
    expect(screen.getByText(/FIRMS E364/)).toBeInTheDocument();
    expect(screen.queryByRole('searchbox')).not.toBeInTheDocument();
  });

  it('switches to a table at 11 rows', async () => {
    load.mockResolvedValue(withRows(Array.from({ length: 11 }, (_, index) => facilityRow(index + 1))));
    renderRequest();
    expect(await screen.findByLabelText('Search')).toBeInTheDocument();
    expect(screen.getByText('FACILITY 1')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'PORT LIBERTY - BAYONNE' })).not.toBeInTheDocument();
  });

  it('shows a rejection card with the F411 code', async () => {
    load.mockResolvedValue(withRows([{
      kind: 'rejection',
      firms_code: 'ZZZZ',
      error_code: '012',
      error_message: 'FIRMS CODE NOT ON FILE',
    }]));
    renderRequest();
    expect(await screen.findByText('012')).toBeInTheDocument();
    expect(screen.getByText(/FIRMS CODE NOT ON FILE/)).toBeInTheDocument();
    expect(screen.getByText('Rejected')).toBeInTheDocument();
  });
});
