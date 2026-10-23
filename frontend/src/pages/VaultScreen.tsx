import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from 'primereact/button';
import { api, demoUser, type MqStatus, type Vault } from '../api';
import EdiPreview from '../components/EdiPreview';
import { statusClass } from '../lib/status';

export default function VaultScreen() {
  const [vault, setVault] = useState<Vault | null>(null);
  const [mq, setMq] = useState<MqStatus | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [error, setError] = useState('');
  const admin = demoUser() === 'admin';

  const load = () => {
    api.vault().then(setVault).catch((err: Error) => setError(err.message));
    api.mq().then(setMq).catch(() => undefined);
  };
  useEffect(load, []);

  return (
    <div className="p-4">
      <h1 className="mt-0" style={{ color: '#11304C' }}>MQ and EDI vault</h1>
      {mq && (
        <p className="kn-help">
          {mq.mode} · out {mq.outbound_queue} · in {mq.inbound_queue} · {mq.reachable ? mq.detail : mq.detail}
        </p>
      )}
      <p className="kn-help">The communication password is hidden in this view. The mock outbox file keeps the real record for the transmitter. Dead-letter, backoff, timeouts and a queue console wait on the Engine transmitter.</p>
      {error && <p role="alert">{error}</p>}
      <ul className="list-none p-0">
        {vault?.requests.map((row) => (
          <li key={row.id} className="kn-card mb-3">
            <div className="flex justify-content-between align-items-center">
              <div>
                <Link to={`/requests/${row.id}`}>{row.control_id}</Link>
                <span className="ml-2 kn-help">{row.kn_number} · {row.file_code}</span>
                <span className={`ml-2 ${statusClass(row.status)}`}>{row.status}</span>
              </div>
              <div className="flex gap-2">
                <Button type="button" label={open === row.id ? 'Hide EDI' : 'EDI'} outlined onClick={() => setOpen(open === row.id ? null : row.id)} />
                {admin && row.mq_send_state === 'FAILED' && (
                  <Button type="button" label="Retry" onClick={() => api.retry(row.id).then(load).catch((err: Error) => setError(err.message))} />
                )}
              </div>
            </div>
            {open === row.id && <div className="mt-3"><EdiPreview edi={row.edi || ''} /></div>}
          </li>
        ))}
      </ul>
      {admin && (
        <section className="mb-4">
          <h2>Failed sends</h2>
          <p className="kn-help">Local stand-in for the transmitter dead-letter queue. An admin can retry these.</p>
          {(vault?.dead_letters || []).length === 0 && <p>None.</p>}
          {(vault?.dead_letters || []).map((row) => (
            <article key={row.id} className="kn-card mb-2">
              <Link to={`/requests/${row.id}`}>{row.control_id}</Link>
              <span className="kn-help"> {row.mq_send_error}</span>
              <Button className="ml-2" type="button" label="Retry" onClick={() => api.retry(row.id).then(load).catch((err: Error) => setError(err.message))} />
            </article>
          ))}
        </section>
      )}
      {admin && (
        <section>
          <h2>Unmatched responses</h2>
          <p className="kn-help">Visible to admins only. A response with an unknown control ID is kept here.</p>
          {vault?.orphans.length === 0 && <p>None.</p>}
          {vault?.orphans.map((item) => (
            <article key={item.id} className="kn-card mb-2">
              <strong>{item.control_id || 'No control ID'}</strong>
              <span className="kn-help"> {item.kn_number}</span>
              <EdiPreview edi={item.raw_text} />
            </article>
          ))}
        </section>
      )}
    </div>
  );
}
