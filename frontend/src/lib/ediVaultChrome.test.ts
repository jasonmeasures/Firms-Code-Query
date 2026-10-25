import { describe, expect, it, vi } from 'vitest';
import { copyEdi, EDI_VAULT_CHROME, EDI_VAULT_EXTRACT, EDI_VAULT_TABS } from './ediVaultChrome';

describe('EDI vault chrome — same labels as 5106 Tools', () => {
  it('keeps the four Tools tabs', () => {
    expect(Object.values(EDI_VAULT_TABS)).toEqual([
      'MQ connection',
      'EDI vault',
      'Usage',
      'CATAIR reference',
    ]);
  });

  it('keeps the shared add / edit / copy / download actions', () => {
    expect(EDI_VAULT_CHROME).toMatchObject({
      add: 'ADD EDI',
      edit: 'EDIT EDI',
      check: 'CHECK EDI',
      save: 'SAVE EDI',
      cancel: 'CANCEL',
      copy: 'COPY EDI',
      download: 'DOWNLOAD',
      testConnection: 'TEST CONNECTION',
    });
  });

  it('adds extract-only actions without renaming the 5106 set', () => {
    expect(EDI_VAULT_EXTRACT.openRequest).toBe('OPEN REQUEST');
    expect(EDI_VAULT_EXTRACT.retry).toBe('RETRY');
    expect(Object.values(EDI_VAULT_CHROME)).not.toContain('OPEN REQUEST');
  });

  it('copies the masked EDI text', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal('navigator', { clipboard: { writeText } });
    await copyEdi('F111E364');
    expect(writeText).toHaveBeenCalledWith('F111E364');
  });
});
