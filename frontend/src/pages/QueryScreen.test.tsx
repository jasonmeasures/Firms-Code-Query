import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'jest-axe';
import { F111 } from '../test/fixtures';

const preview = vi.fn();
const submit = vi.fn();
const files = vi.fn();

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api');
  return {
    ...actual,
    api: {
      ...actual.api,
      files: (...args: unknown[]) => files(...args),
      preview: (...args: unknown[]) => preview(...args),
      submit: (...args: unknown[]) => submit(...args),
    },
  };
});

import QueryScreen from './QueryScreen';

function renderQuery() {
  return render(
    <MemoryRouter initialEntries={['/query/F111']}>
      <Routes>
        <Route path="/query/:fileCode" element={<QueryScreen />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('QueryScreen', () => {
  beforeEach(() => {
    sessionStorage.setItem('extract-demo-user', 'operator');
    files.mockResolvedValue({ files: [F111] });
    preview.mockReset();
    preview.mockResolvedValue({
      edi: 'A2809S1F      101826     FQ                                                     \nB  2809S1FFQ                                                                     ',
      all_80: true,
      line_count: 2,
      kn_number: '',
      control_id: 'PREVIEWPREVIEWPREVIE',
      app_id: 'FQ',
    });
    submit.mockReset();
  });

  it('blocks an invalid FIRMS code before preview', async () => {
    const user = userEvent.setup();
    renderQuery();
    const input = await screen.findByLabelText(/FIRMS code/i);
    await user.type(input, 'E36');
    expect(await screen.findByText(/FIRMS code must be 4 letters or digits/)).toBeInTheDocument();
    expect(preview).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Submit' })).toBeDisabled();
  });

  it('updates the EDI preview for a valid code', async () => {
    const user = userEvent.setup();
    renderQuery();
    const input = await screen.findByLabelText(/FIRMS code/i);
    await user.type(input, 'E364');
    await waitFor(() => expect(preview).toHaveBeenCalled());
    expect(await screen.findByLabelText('EDI preview')).toHaveTextContent('FQ');
    expect(screen.getByText(/All 80 characters: yes/)).toBeInTheDocument();
  });

  it('lists invalid tokens on the list mode', async () => {
    const user = userEvent.setup();
    renderQuery();
    await screen.findByLabelText(/FIRMS code/i);
    await user.click(screen.getByRole('tab', { name: /List of codes/i }));
    await user.type(screen.getByLabelText(/FIRMS codes/i), 'E364, NO; AB');
    expect(await screen.findByText(/Not valid FIRMS codes: NO, AB/)).toBeInTheDocument();
  });

  it('refuses a whole-file date pull for an operator', async () => {
    const user = userEvent.setup();
    renderQuery();
    await screen.findByLabelText(/FIRMS code/i);
    await user.click(screen.getByRole('tab', { name: /Everything since a date/i }));
    expect(await screen.findByText(/limited to an admin/)).toBeInTheDocument();
    expect(preview).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Submit' })).toBeDisabled();
  });

  it('lets a keyboard user move between modes', async () => {
    const user = userEvent.setup();
    renderQuery();
    await screen.findByRole('tab', { name: /One code/i });
    const list = screen.getByRole('tab', { name: /List of codes/i });
    list.focus();
    await user.keyboard('{Enter}');
    expect(list).toHaveAttribute('aria-selected', 'true');
  });

  it('has no obvious axe violations after a valid preview', async () => {
    const user = userEvent.setup();
    const { container } = renderQuery();
    await user.type(await screen.findByLabelText(/FIRMS code/i), 'E364');
    await waitFor(() => expect(preview).toHaveBeenCalled());
    expect(await axe(container)).toHaveNoViolations();
  });
});
