import type { ExtractRequest } from '../api';
import { statusClass } from '../lib/status';

function when(value: string | null | undefined) {
  if (!value) return '';
  return new Date(value).toLocaleString();
}

export default function StatusTimeline({ request }: { request: ExtractRequest }) {
  const received = request.response?.received_at;
  const parsed = request.status === 'APPROVED' || request.status === 'REJECTED';
  const steps = [
    { label: 'Built', done: true, at: request.created_at },
    { label: 'Queued', done: Boolean(request.mq_send_state), at: request.mq_send_state ? request.created_at : null },
    { label: 'Sent', done: request.mq_send_state === 'SENT', at: request.submitted_at },
    { label: 'Response received', done: Boolean(received), at: received },
    { label: 'Parsed', done: parsed, at: parsed ? received : null },
  ];
  return (
    <div>
      <div className="flex align-items-center gap-2 mb-3">
        <span className={statusClass(request.status)}>{request.status}</span>
        {request.mq_send_state && <span className="kn-help">Send {request.mq_send_state}</span>}
        <span className="kn-help">Control ID {request.control_id}</span>
      </div>
      <ol className="m-0 pl-3">
        {steps.map((step) => (
          <li key={step.label} className="mb-2">
            <strong>{step.label}</strong>
            {step.done ? <span className="kn-help"> · {when(step.at) || 'done'}</span> : <span className="kn-help"> · waiting</span>}
          </li>
        ))}
        {request.mq_send_state === 'FAILED' && (
          <li className="mb-2"><strong>Failed</strong> <span className="kn-help">{request.mq_send_error}</span></li>
        )}
      </ol>
    </div>
  );
}
