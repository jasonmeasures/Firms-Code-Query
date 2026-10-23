import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { request } from '../test/fixtures';

const job = vi.fn();

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api');
  return {
    ...actual,
    api: {
      ...actual.api,
      job: (...args: unknown[]) => job(...args),
    },
  };
});

import JobScreen from './JobScreen';

describe('JobScreen', () => {
  beforeEach(() => {
    job.mockResolvedValue({
      id: 'job-1',
      file_code: 'F111',
      query_type: 'ALL_DISTRICT',
      status: 'PENDING_CBP',
      total: 2,
      pending: 1,
      approved: 1,
      rejected: 0,
      failed: 0,
      requests: [
        request({ id: 'a', control_id: 'AAAA', status: 'APPROVED' }),
        request({ id: 'b', control_id: 'BBBB', status: 'PENDING_CBP' }),
      ],
    });
  });

  it('shows load progress', async () => {
    render(
      <MemoryRouter initialEntries={['/jobs/job-1']}>
        <Routes>
          <Route path="/jobs/:jobId" element={<JobScreen />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByText(/1 of 2 responses in/)).toBeInTheDocument();
    expect(screen.getByLabelText('Load progress')).toHaveAttribute('value', '1');
    expect(screen.getByText('AAAA')).toBeInTheDocument();
  });
});
