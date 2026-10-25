/**
 * Shared EDI-management chrome. Labels match 5106 ToolsScreen.
 * Records, queues, and extra actions stay module-specific.
 */

export const EDI_VAULT_TABS = {
  mq: 'MQ connection',
  edi: 'EDI vault',
  usage: 'Usage',
  ref: 'CATAIR reference',
} as const;

export const EDI_VAULT_CHROME = {
  add: 'ADD EDI',
  edit: 'EDIT EDI',
  check: 'CHECK EDI',
  save: 'SAVE EDI',
  cancel: 'CANCEL',
  copy: 'COPY EDI',
  download: 'DOWNLOAD',
  testConnection: 'TEST CONNECTION',
} as const;

/** Extract-only. 5106 Tools has no request detail or retry on the vault item. */
export const EDI_VAULT_EXTRACT = {
  openRequest: 'OPEN REQUEST',
  retry: 'RETRY',
} as const;

export async function copyEdi(text: string): Promise<void> {
  await navigator.clipboard.writeText(text);
}
