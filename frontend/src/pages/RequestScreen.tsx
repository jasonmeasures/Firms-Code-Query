import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Button } from 'primereact/button';
import { Column } from 'primereact/column';
import { DataTable } from 'primereact/datatable';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { TabPanel, TabView } from 'primereact/tabview';
import { Tag } from 'primereact/tag';
import { api, demoUser, type ExtractRequest } from '../api';
import EdiPreview from '../components/EdiPreview';
import StatusTimeline from '../components/StatusTimeline';
import { echoMatches } from '../lib/status';

function text(value: unknown) {
  return value == null ? '' : String(value);
}

export default function RequestScreen() {
  const { requestId = '' } = useParams();
  const [row, setRow] = useState<ExtractRequest | null>(null);
  const [error, setError] = useState('');
  const [paste, setPaste] = useState('');
  const [search, setSearch] = useState('');

  const load = () => {
    api.request(requestId).then(setRow).catch((err: Error) => setError(err.message));
  };
  useEffect(load, [requestId]);

  if (!row) return <p className="p-4">{error || 'Loading request…'}</p>;
  const parsed = row.response?.parsed;
  const rows = (parsed?.rows || []).filter((item) => item.kind !== 'carrier_query');
  const visible = rows.filter((item) => {
    if (!search.trim()) return true;
    return JSON.stringify(item).toUpperCase().includes(search.trim().toUpperCase());
  });
  const knEcho = echoMatches(row.kn_number, parsed?.kn_number || '');
  const controlEcho = echoMatches(row.control_id, parsed?.control_id || '');

  const download = async () => {
    const csv = await api.csv(row.id);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${row.file_code}_${row.control_id}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-4">
      <h1 className="mt-0" style={{ color: '#11304C' }}>{row.file_code} {row.query_type}</h1>
      <StatusTimeline request={row} />
      {parsed && (
        <div className="flex gap-2 my-3">
          {knEcho !== 'empty' && (
            <Tag severity={knEcho === 'differ' ? 'danger' : 'success'} value={`A user data ${parsed.kn_number} ${knEcho === 'differ' ? 'differs' : 'matches'}`} />
          )}
          <Tag severity={controlEcho === 'differ' ? 'danger' : 'success'} value={`Control ${parsed.control_id || '—'} ${controlEcho === 'match' ? 'matches' : controlEcho === 'differ' ? 'differs' : ''}`} />
        </div>
      )}
      {parsed?.warnings?.map((warning) => <p key={warning} className="kn-help">{warning}</p>)}
      <TabView>
        <TabPanel header="Response">
          {rows.length === 0 && <p>No parsed rows yet.</p>}
          {rows.length > 0 && rows.length <= 10 && (
            <div className="grid">
              {rows.map((item, index) => (
                <div key={index} className="col-12 md:col-6">
                  <article className="kn-card h-full">
                    {item.kind === 'rejection' || item.kind === 'carrier_rejection' ? (
                      <>
                        <h3><span className="kn-status-REJECTED">Rejected</span> {text(item.firms_code || item.carrier_code || 'Query')}</h3>
                        <p><strong>{text(item.error_code)}</strong> {text(item.error_message)}</p>
                      </>
                    ) : (
                      <>
                        <h3>{text(item.facility_name || item.name || item.carrier_name || item.narrative || item.code || item.iso)}</h3>
                        {item.status_label != null && <p><span className={text(item.status) === 'D' ? 'kn-status-REJECTED' : 'kn-status-APPROVED'}>{text(item.status_label)}</span> {text(item.facility_type)}</p>}
                        <p className="kn-help m-0">
                          {[item.firms_code && `FIRMS ${text(item.firms_code)}`, item.district_port && `Port ${text(item.district_port)}`, item.address, item.city, item.state, item.zip, item.country].filter(Boolean).join(' · ')}
                        </p>
                        {item.entry_warning != null && text(item.entry_warning) && <p>{text(item.entry_warning)}</p>}
                      </>
                    )}
                  </article>
                </div>
              ))}
            </div>
          )}
          {rows.length > 10 && (
            <>
              <label className="block mb-2 font-bold text-sm" htmlFor="row-search">Search</label>
              <InputText id="row-search" className="mb-2 w-full" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Filter the rows" />
              <DataTable value={visible} paginator rows={10} emptyMessage="No rows match.">
                <Column field="firms_code" header="FIRMS" />
                <Column field="district_port" header="District/port" />
                <Column field="status_label" header="Status" />
                <Column field="facility_type" header="Type" />
                <Column field="facility_name" header="Name" />
                <Column field="state" header="State" />
                <Column field="error_code" header="Error" />
              </DataTable>
            </>
          )}
          <Button className="mt-3" label="Export CSV" outlined disabled={!parsed} onClick={download} />
        </TabPanel>
        <TabPanel header="Raw EDI">
          <h2 className="text-base">Request</h2>
          <EdiPreview edi={row.edi || ''} />
          <h2 className="text-base">Response</h2>
          <EdiPreview edi={row.response?.raw_text || ''} />
        </TabPanel>
      </TabView>
      {demoUser() === 'admin' && row.status === 'PENDING_CBP' && (
        <section className="mt-4">
          <h2 className="text-base">Dev only — paste an ACE response</h2>
          <InputTextarea value={paste} onChange={(event) => setPaste(event.target.value)} rows={6} className="w-full" />
          <Button className="mt-2" label="Apply response" onClick={() => api.devResponse(row.id, paste).then(setRow).catch((err: Error) => setError(err.message))} />
        </section>
      )}
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
