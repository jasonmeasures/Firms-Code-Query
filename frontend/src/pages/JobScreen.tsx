import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Button } from 'primereact/button';
import { api, type Job } from '../api';
import { statusClass } from '../lib/status';

export default function JobScreen() {
  const { jobId = '' } = useParams();
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState('');

  const load = () => api.job(jobId).then(setJob).catch((err: Error) => setError(err.message));
  useEffect(() => { load(); }, [jobId]);

  if (!job) return <p className="p-4">{error || 'Loading the load…'}</p>;
  const done = job.approved + job.rejected;
  return (
    <div className="p-4">
      <h1 className="mt-0" style={{ color: '#11304C' }}>{job.file_code} {job.query_type}</h1>
      <p><span className={statusClass(job.status)}>{job.status}</span></p>
      <p aria-live="polite">{done} of {job.total} responses in. {job.pending} waiting. {job.failed} failed to send. {job.approved} approved. {job.rejected} rejected.</p>
      <progress value={done} max={Math.max(job.total, 1)} aria-label="Load progress" />
      {job.failed > 0 && <Button className="ml-3" label="Retry failed blocks" onClick={() => api.resume(job.id).then(setJob).catch((err: Error) => setError(err.message))} />}
      <ul>
        {job.requests.map((row) => (
          <li key={row.id}>
            <Link to={`/requests/${row.id}`}>{row.control_id}</Link>
            <span className="kn-help"> {row.status} {row.mq_send_state || ''}</span>
          </li>
        ))}
      </ul>
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
