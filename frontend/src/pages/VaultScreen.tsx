import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from 'primereact/button';
import { Card } from 'primereact/card';
import { InputText } from 'primereact/inputtext';
import { api, demoUser, type MqStatus, type UsageSummary, type VaultCheck, type VaultItem } from '../api';
import EdiEditor from '../components/EdiEditor';
import { copyEdi, EDI_VAULT_CHROME, EDI_VAULT_EXTRACT, EDI_VAULT_TABS } from '../lib/ediVaultChrome';
import { fieldLegend, rulerText } from '../lib/ediPositions';
import { statusClass } from '../lib/status';

const RECORD_LABELS: Record<string, string> = {
  A: 'Batch control header (site / sender / date / application id)',
  B: 'Block control header (port / filer / control ID)',
  Y: 'Block control trailer',
  Z: 'Batch control trailer',
  F101: 'Region / district / port query or response',
  F201: 'District address lines 2 and 3',
  F301: 'District city / state / ZIP',
  F401: 'Subport',
  F102: 'Country codes query or response',
  F202: 'Country program dates',
  F104: 'Foreign port (Schedule K)',
  F106: 'Carrier query or response',
  F906: 'Carrier rejection',
  F110: 'HTS update request or narrative',
  F111: 'FIRMS query',
  F211: 'FIRMS facility',
  F311: 'FIRMS street / city / state',
  F411: 'FIRMS ZIP / country or rejection',
};

export default function VaultScreen() {
  const [tab, setTab] = useState<'mq' | 'edi' | 'usage' | 'ref'>('mq');
  const [status, setStatus] = useState<MqStatus | null>(null);
  const [host, setHost] = useState('');
  const [port, setPort] = useState('1414');
  const [qm, setQm] = useState('');
  const [channel, setChannel] = useState('');
  const [mode, setMode] = useState('mock');
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [filings, setFilings] = useState<VaultItem[]>([]);
  const [outbox, setOutbox] = useState<VaultItem[]>([]);
  const [orphans, setOrphans] = useState<Vault['orphans']>([]);
  const [preview, setPreview] = useState<VaultItem | null>(null);
  const [editing, setEditing] = useState(false);
  const [adding, setAdding] = useState(false);
  const [draftEdi, setDraftEdi] = useState('');
  const [check, setCheck] = useState<VaultCheck | null>(null);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const admin = demoUser() === 'admin';

  const loadStatus = async () => {
    const next = await api.mq();
    setStatus(next);
    setHost(next.host || '');
    setPort(next.port || '1414');
    setQm(next.queue_manager || '');
    setChannel(next.channel || '');
    setMode(next.mode);
  };

  const loadVault = async () => {
    const next = await api.vault();
    setFilings(next.filings || next.requests || []);
    setOutbox(next.outbox || []);
    setOrphans(next.orphans || []);
  };

  const loadUsage = async () => {
    setUsage(await api.usage());
  };

  useEffect(() => {
    loadStatus().catch((err: Error) => setError(err.message));
    loadVault().catch((err: Error) => setError(err.message));
    loadUsage().catch(() => undefined);
  }, []);

  const items = [...filings, ...outbox];

  const openItem = async (id: string) => {
    const item = await api.vaultItem(id);
    setPreview(item);
    setDraftEdi(item.edi || item.edi_raw || '');
    setEditing(false);
    setAdding(false);
    setCheck(null);
    setError('');
    await loadUsage();
  };

  const startAdd = () => {
    setPreview(null);
    setDraftEdi('');
    setAdding(true);
    setEditing(true);
    setCheck(null);
    setError('');
  };

  const checkEdi = async () => {
    setBusy(true);
    setError('');
    try {
      const result = await api.checkVaultItem(draftEdi);
      setCheck(result);
    } catch (err) {
      setCheck(null);
      setError(err instanceof Error ? err.message : 'EDI check failed');
    } finally {
      setBusy(false);
    }
  };

  const saveEdi = async () => {
    setBusy(true);
    setError('');
    setCheck(null);
    try {
      const saved = adding ? await api.addVaultItem(draftEdi) : await api.saveVaultItem(preview!.id, draftEdi);
      setPreview(saved);
      setDraftEdi(saved.edi || saved.edi_raw || '');
      setEditing(false);
      setAdding(false);
      await loadVault();
      await loadUsage();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'EDI save failed');
    } finally {
      setBusy(false);
    }
  };

  const test = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const result = await api.mqTest({ host, port, queue_manager: qm, channel, mode });
      setStatus(result.status);
      setMessage(result.status.reachable ? `Connected — ${result.status.detail}` : result.status.detail);
      await loadVault();
      await loadUsage();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Connection test failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="p-4 flex flex-column gap-3">
      <div className="flex gap-2 flex-wrap">
        <button type="button" className={`kn-nav-btn${tab === 'mq' ? ' active' : ''}`} onClick={() => setTab('mq')}>{EDI_VAULT_TABS.mq}</button>
        <button type="button" className={`kn-nav-btn${tab === 'edi' ? ' active' : ''}`} onClick={() => { setTab('edi'); loadVault(); }}>{EDI_VAULT_TABS.edi}</button>
        <button type="button" className={`kn-nav-btn${tab === 'usage' ? ' active' : ''}`} onClick={() => { setTab('usage'); loadUsage(); }}>{EDI_VAULT_TABS.usage}</button>
        <button type="button" className={`kn-nav-btn${tab === 'ref' ? ' active' : ''}`} onClick={() => setTab('ref')}>{EDI_VAULT_TABS.ref}</button>
      </div>
      {error && tab !== 'edi' && <p role="alert">{error}</p>}

      {tab === 'mq' && (
        <Card className="shadow-2">
          <div className="p-4">
            <h2 className="mt-0 mb-2" style={{ color: '#003F5B' }}>MQ connection</h2>
            <p className="mt-0 mb-3 text-sm" style={{ color: '#64748B' }}>
              Host-independent. Mock writes <code>CBP.OUT.EXTRACT.QUERY</code> to the local outbox.
              Live uses Engine AE credentials when <code>MQ_MODE=live</code>.
            </p>
            {status && (
              <div className="mb-3 text-sm">
                <span className={`kn-status-badge ${status.reachable ? 'kn-status-APPROVED' : 'kn-status-REJECTED'}`}>
                  {status.reachable ? 'REACHABLE' : 'DOWN'}
                </span>
                <span className="ml-2">{status.mode} · {status.outbound_queue} · TTL {status.ttl_ms}ms · priority {status.priority}</span>
              </div>
            )}
            <div className="grid">
              <div className="col-12 md:col-6">
                <label className="field-label">Host</label>
                <InputText className="w-full" value={host} onChange={(event) => setHost(event.target.value)} placeholder="This developer's MQ host" />
              </div>
              <div className="col-12 md:col-3">
                <label className="field-label">Port</label>
                <InputText className="w-full" value={port} onChange={(event) => setPort(event.target.value)} />
              </div>
              <div className="col-12 md:col-3">
                <label className="field-label">Mode</label>
                <InputText className="w-full" value={mode} onChange={(event) => setMode(event.target.value)} placeholder="mock or live" />
              </div>
              <div className="col-12 md:col-6">
                <label className="field-label">Queue manager</label>
                <InputText className="w-full" value={qm} onChange={(event) => setQm(event.target.value)} />
              </div>
              <div className="col-12 md:col-6">
                <label className="field-label">Channel</label>
                <InputText className="w-full" value={channel} onChange={(event) => setChannel(event.target.value)} />
              </div>
            </div>
            <Button label={EDI_VAULT_CHROME.testConnection} className="mt-3" loading={busy} onClick={test} />
            {message && <p className="text-sm mt-3 mb-0">{message}</p>}
          </div>
        </Card>
      )}

      {tab === 'edi' && (
        <div className="grid">
          <div className="col-12 lg:col-5">
            <Card className="shadow-2">
              <div className="p-3">
                <div className="flex justify-content-between align-items-center mb-3">
                  <h2 className="m-0" style={{ color: '#003F5B' }}>{EDI_VAULT_TABS.edi}</h2>
                  <Button label={EDI_VAULT_CHROME.add} className="p-button-sm" onClick={startAdd} />
                </div>
                {items.length === 0 && <p className="text-sm" style={{ color: '#64748B' }}>No EDI yet. Submit a query or add one here.</p>}
                {items.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className="w-full text-left mb-2 p-2 border-round"
                    style={{ border: '1px solid #DEE2E6', background: preview?.id === item.id ? '#E7ECF0' : '#fff' }}
                    onClick={() => openItem(item.id)}
                  >
                    <strong className="block">{item.filename || item.edi_filename || item.control_id}</strong>
                    <span className="text-sm" style={{ color: '#64748B' }}>
                      <span className={statusClass(item.status)}>{item.status || item.action}</span>
                      {' · '}{item.file_code || item.action} {item.query_type}
                    </span>
                  </button>
                ))}
                {admin && orphans.length > 0 && (
                  <section className="mt-3">
                    <h3 className="text-base">Unmatched responses</h3>
                    {orphans.map((item) => (
                      <article key={item.id} className="kn-card mb-2">
                        <strong>{item.control_id || 'No control ID'}</strong>
                        <span className="kn-help"> {item.kn_number}</span>
                      </article>
                    ))}
                  </section>
                )}
              </div>
            </Card>
          </div>
          <div className="col-12 lg:col-7">
            <Card className="shadow-2">
              <div className="p-3">
                <h2 className="mt-0 mb-3" style={{ color: '#003F5B' }}>EDI {adding ? 'add' : editing ? 'edit' : 'view'}</h2>
                {!preview && !adding && <p className="text-sm" style={{ color: '#64748B' }}>Select a vault item or add EDI.</p>}
                {(preview || adding) && (
                  <>
                    <div className="flex gap-2 mb-3 flex-wrap">
                      {!editing && preview && preview.editable !== false && (
                        <Button
                          label={EDI_VAULT_CHROME.edit}
                          className="p-button-sm"
                          onClick={() => {
                            setDraftEdi(preview.edi || preview.edi_raw || '');
                            setEditing(true);
                            setError('');
                          }}
                        />
                      )}
                      {editing && (
                        <>
                          <Button label={EDI_VAULT_CHROME.check} className="p-button-outlined p-button-sm" loading={busy} onClick={checkEdi} />
                          <Button label={EDI_VAULT_CHROME.save} className="p-button-sm" loading={busy} onClick={saveEdi} />
                          <Button
                            label={EDI_VAULT_CHROME.cancel}
                            className="p-button-outlined p-button-sm"
                            onClick={() => {
                              setEditing(false);
                              setAdding(false);
                              setDraftEdi(preview?.edi || preview?.edi_raw || '');
                              setCheck(null);
                              setError('');
                            }}
                          />
                        </>
                      )}
                      {preview && (
                        <>
                          <Button
                            label={EDI_VAULT_CHROME.copy}
                            className="p-button-outlined p-button-sm"
                            onClick={() => copyEdi(preview.edi || preview.edi_raw || '').catch((err: Error) => setError(err.message))}
                          />
                          <Button
                            label={EDI_VAULT_CHROME.download}
                            className="p-button-outlined p-button-sm"
                            onClick={() => api.downloadVaultItem(preview.id).catch((err: Error) => setError(err.message))}
                          />
                          {preview.request_id && (
                            <Link className="p-button p-button-outlined p-button-sm" to={`/requests/${preview.request_id}`}>
                              {EDI_VAULT_EXTRACT.openRequest}
                            </Link>
                          )}
                          {admin && preview.mq_send_state === 'FAILED' && preview.request_id && (
                            <Button label={EDI_VAULT_EXTRACT.retry} className="p-button-sm" onClick={() => api.retry(preview.request_id!).then(() => openItem(preview.id)).catch((err: Error) => setError(err.message))} />
                          )}
                        </>
                      )}
                    </div>
                    {preview?.editable === false && (
                      <p className="text-sm mt-0 mb-3" style={{ color: '#64748B' }}>
                        <i className="pi pi-lock mr-2" />
                        {preview.edit_locked_reason || 'This EDI is read-only.'}
                      </p>
                    )}
                    {error && <p className="text-sm mt-0 mb-3" style={{ color: '#FF3D33' }}>{error}</p>}
                    {check && (
                      <div className="mb-3">
                        <p className="text-sm mt-0 mb-1" style={{ color: check.ok ? '#23C55E' : '#FF3D33' }}>
                          {check.ok
                            ? `EDI checks out — ${check.line_count} record${check.line_count === 1 ? '' : 's'}, all 80 characters, extract rules passed.`
                            : 'EDI did not pass format or ACE Extract rules.'}
                        </p>
                        {!check.ok && [...check.errors, ...(check.rule_errors || [])].map((msg) => (
                          <p key={msg} className="text-sm mt-0 mb-1" style={{ color: '#FF3D33' }}>{msg}</p>
                        ))}
                      </div>
                    )}
                    {!check && !editing && (preview?.warnings?.length ?? 0) > 0 && (
                      <div className="mb-3">
                        <p className="text-sm mt-0 mb-1" style={{ color: '#F58F00' }}>
                          Saved. Format is valid; ACE Extract rules would still fail on send:
                        </p>
                        {preview!.warnings!.map((msg) => (
                          <p key={msg} className="text-sm mt-0 mb-1" style={{ color: '#F58F00' }}>{msg}</p>
                        ))}
                      </div>
                    )}
                    {editing ? (
                      <EdiEditor
                        value={draftEdi}
                        onChange={(next) => { setDraftEdi(next); setCheck(null); }}
                        placeholder="Paste an 80-character extract block. Brackets are optional."
                      />
                    ) : (
                      <pre className="p-3 border-round overflow-auto text-xs" style={{ background: '#0E2638', color: '#E7ECF0', maxHeight: 320 }}>
                        <span className="kn-ruler">{`${rulerText()}\n`}</span>
                        {(preview?.records || []).map((rec) => (
                          <div key={`${rec.id}-${rec.text}`} className="mb-2">
                            <div>
                              <span style={{ color: '#49BFE8' }}>{rec.id}</span>
                              <span>{rec.text.slice(rec.id.length)}</span>
                              <span style={{ color: rec.ok ? '#94A3B8' : '#F58F00' }}>  ← {rec.label} ({rec.length})</span>
                            </div>
                            <div style={{ color: '#6f8aa5' }}>{fieldLegend(rec.id)}</div>
                          </div>
                        ))}
                      </pre>
                    )}
                    <p className="text-xs mt-2 mb-0" style={{ color: '#64748B' }}>
                      Extract Reference — each record is 80 characters, space-padded. Short lines are padded on save. The communication password is hidden and cannot be changed here.
                    </p>
                    {preview?.envelope && (
                      <>
                        <h3 className="mt-3 mb-2" style={{ color: '#003F5B' }}>MQ envelope</h3>
                        <pre className="p-3 border-round overflow-auto text-xs" style={{ background: '#F1F3F5', maxHeight: 220 }}>
                          {preview.envelope}
                        </pre>
                      </>
                    )}
                  </>
                )}
              </div>
            </Card>
          </div>
        </div>
      )}

      {tab === 'usage' && (
        <Card className="shadow-2">
          <div className="p-4">
            <h2 className="mt-0 mb-2" style={{ color: '#003F5B' }}>Usage tracking</h2>
            <p className="mt-0 mb-3 text-sm" style={{ color: '#64748B' }}>
              Event log only — no invoices or payments. Use these quantities later if the tool is metered.
            </p>
            {!usage && <p className="text-sm">No usage yet.</p>}
            {usage && (
              <>
                <div className="flex gap-4 mb-3">
                  <div>
                    <div className="field-label">Events</div>
                    <div className="text-2xl font-bold" style={{ color: '#458CFC' }}>{usage.total_events}</div>
                  </div>
                  <div>
                    <div className="field-label">Quantity</div>
                    <div className="text-2xl font-bold" style={{ color: '#003F5B' }}>{usage.total_quantity}</div>
                  </div>
                </div>
                {usage.events.length === 0 && <p className="text-sm" style={{ color: '#64748B' }}>No billable events recorded yet.</p>}
                {usage.events.map((row) => (
                  <div key={row.event_type} className="flex justify-content-between py-2" style={{ borderBottom: '1px solid #DEE2E6' }}>
                    <div>
                      <strong>{row.event_type}</strong>
                      <span className="ml-2 text-sm" style={{ color: '#64748B' }}>{row.unit}</span>
                    </div>
                    <span>{row.quantity} ({row.count} rows)</span>
                  </div>
                ))}
              </>
            )}
          </div>
        </Card>
      )}

      {tab === 'ref' && (
        <Card className="shadow-2">
          <div className="p-4">
            <h2 className="mt-0 mb-3" style={{ color: '#003F5B' }}>CATAIR Extract records</h2>
            {Object.entries(RECORD_LABELS).map(([id, label]) => (
              <div key={id} className="flex justify-content-between py-2" style={{ borderBottom: '1px solid #DEE2E6' }}>
                <strong>{id}</strong>
                <span>{label}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

type Vault = Awaited<ReturnType<typeof api.vault>>;
