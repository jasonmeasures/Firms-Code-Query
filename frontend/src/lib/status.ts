/** Filing words shared with the 5106 tool. Every reference file uses this set. */

export function statusClass(status: string): string {
  if (status === 'APPROVED') return 'kn-status-APPROVED';
  if (status === 'REJECTED') return 'kn-status-REJECTED';
  if (status === 'PENDING_CBP' || status === 'SUBMITTED') return 'kn-status-PENDING_CBP';
  if (status === 'FAILED') return 'kn-send-error';
  return 'kn-status-DRAFT';
}

export function echoMatches(left: string, right: string): 'match' | 'differ' | 'empty' {
  if (!left || !right) return 'empty';
  return left.trim() === right.trim() ? 'match' : 'differ';
}

export { firmsCodeValid } from './validation';
