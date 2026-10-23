import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Message } from 'primereact/message';
import { api, demoUser, type FileSpec, type ModeSpec } from '../api';
import EdiPreview from '../components/EdiPreview';

function controlId() {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  const bytes = crypto.getRandomValues(new Uint8Array(20));
  return Array.from(bytes, (byte) => alphabet[byte % alphabet.length]).join('');
}

export default function QueryScreen() {
  const { fileCode = '' } = useParams();
  const navigate = useNavigate();
  const [file, setFile] = useState<FileSpec | null>(null);
  const [mode, setMode] = useState<ModeSpec | null>(null);
  const [params, setParams] = useState<Record<string, string>>({});
  const [control, setControl] = useState('');
  const [edi, setEdi] = useState('');
  const [all80, setAll80] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const role = demoUser();

  useEffect(() => {
    api.files().then((res) => {
      const found = res.files.find((item) => item.file_code === fileCode.toUpperCase()) || null;
      setFile(found);
      const first = found?.modes.find((item) => role === 'admin' || !item.admin_only) || found?.modes[0] || null;
      setMode(first);
      setControl(controlId());
      setParams({});
    }).catch((err: Error) => setError(err.message));
  }, [fileCode, role]);

  useEffect(() => {
    if (!file || !mode || !control) return;
    if (mode.admin_only && role !== 'admin') {
      setEdi('');
      setError('This load is limited to an admin.');
      return;
    }
    const handle = window.setTimeout(() => {
      api.preview({
        file_code: file.file_code,
        query_type: mode.id,
        params,
        kn_number: '',
        control_id: control,
      }).then((res) => {
        setEdi(res.edi);
        setAll80(res.all_80);
        setError('');
      }).catch((err: Error) => {
        setEdi('');
        setError(err.message);
      });
    }, 250);
    return () => window.clearTimeout(handle);
  }, [file, mode, params, control, role]);

  const submit = async () => {
    if (!file || !mode) return;
    setBusy(true);
    try {
      const result = await api.submit({
        file_code: file.file_code,
        query_type: mode.id,
        params,
        kn_number: '',
        control_id: control,
      });
      if (result.job) navigate(`/jobs/${result.job.id}`);
      else navigate(`/requests/${result.request.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Submit failed');
    } finally {
      setBusy(false);
    }
  };

  if (!file || !mode) return <p className="p-4">Loading the reference file…</p>;

  return (
    <div className="p-4" style={{ maxWidth: '980px' }}>
      <p className="text-sm font-bold mt-0" style={{ letterSpacing: '0.12em', color: '#005D7C' }}>{file.spec}</p>
      <h1 className="mt-0" style={{ color: '#11304C' }}>{file.title}</h1>
      <p className="kn-help">{file.summary} Request application id {file.app_in}. Response application id {file.app_out}.</p>
      <div className="flex flex-wrap gap-2 mb-3" role="tablist" aria-label="Query mode">
        {file.modes.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={item.id === mode.id}
            className={`kn-nav-btn${item.id === mode.id ? ' active' : ''}`}
            onClick={() => { setMode(item); setParams({}); }}
          >
            {item.label}{item.admin_only ? ' (admin)' : ''}
          </button>
        ))}
      </div>
      <p className="kn-help">{mode.help}</p>
      <div className="flex flex-column gap-3 mb-3">
        {mode.fields.map((field) => (
          <label key={field.name} className="flex flex-column gap-1 font-bold text-sm">
            {field.label}
            {field.multiline ? (
              <InputTextarea
                value={params[field.name] || ''}
                onChange={(event) => setParams({ ...params, [field.name]: event.target.value.toUpperCase() })}
                rows={5}
                autoResize
              />
            ) : (
              <InputText
                value={params[field.name] || ''}
                maxLength={field.max_length}
                onChange={(event) => setParams({ ...params, [field.name]: event.target.value.toUpperCase() })}
              />
            )}
            <span className="kn-help font-normal">Positions {field.positions}</span>
          </label>
        ))}
        <label className="flex flex-column gap-1 font-bold text-sm" style={{ flex: '1 1 280px' }}>
          Control ID
          <span className="flex gap-2">
            <InputText value={control} maxLength={20} onChange={(event) => setControl(event.target.value.toUpperCase())} className="w-full" />
            <Button type="button" label="New" outlined onClick={() => setControl(controlId())} />
          </span>
          <span className="kn-help font-normal">B record, positions 60-80. This is the correlation id. A positions 60-80 stay blank: these queries are not a shipment.</span>
        </label>
      </div>
      {error && <Message severity="error" text={error} className="mb-3 w-full" />}
      <div className="flex justify-content-between align-items-center mb-2">
        <h2 className="m-0 text-sm" style={{ letterSpacing: '0.08em' }}>EDI PREVIEW</h2>
        <span className="kn-help">All 80 characters: {edi ? (all80 ? 'yes' : 'no') : '—'}. The password in positions 9-14 is hidden.</span>
      </div>
      <EdiPreview edi={edi} />
      <Button className="mt-3" label={busy ? 'Sending…' : 'Submit'} disabled={busy || !edi} onClick={submit} />
    </div>
  );
}
