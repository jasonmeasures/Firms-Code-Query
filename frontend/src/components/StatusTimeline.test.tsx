import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { axe } from 'jest-axe';
import StatusTimeline from './StatusTimeline';
import { request } from '../test/fixtures';

describe('StatusTimeline', () => {
  it('walks Built, Queued, Sent, then waiting for the response', () => {
    render(<StatusTimeline request={request()} />);
    expect(screen.getByText('PENDING_CBP')).toBeInTheDocument();
    expect(screen.getByText(/Control ID 2TGFEC9WQDMLKMFSFASI/)).toBeInTheDocument();
    expect(screen.getByText('Built')).toBeInTheDocument();
    expect(screen.getByText('Queued')).toBeInTheDocument();
    expect(screen.getByText('Sent')).toBeInTheDocument();
    expect(screen.getAllByText(/waiting/).length).toBeGreaterThan(0);
  });

  it('marks Parsed after an approved response', () => {
    render(<StatusTimeline request={request({
      status: 'APPROVED',
      response: {
        raw_text: 'FO',
        parsed: { kn_number: '', control_id: '2TGFEC9WQDMLKMFSFASI', application_id: 'FO', file_code: 'F111', rows: [], unrecognized: [], warnings: [] },
        received_at: '2026-10-23T12:00:10.000Z',
        parse_errors: null,
      },
    })} />);
    expect(screen.getByText('APPROVED')).toBeInTheDocument();
    expect(screen.getAllByText('Parsed')).toHaveLength(1);
    expect(screen.queryByText(/waiting/)).not.toBeInTheDocument();
  });

  it('has no obvious axe violations', async () => {
    const { container } = render(<StatusTimeline request={request()} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
