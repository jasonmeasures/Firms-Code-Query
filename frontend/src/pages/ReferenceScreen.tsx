import { useEffect, useState } from 'react';
import { Column } from 'primereact/column';
import { DataTable } from 'primereact/datatable';
import { InputText } from 'primereact/inputtext';
import { TabPanel, TabView } from 'primereact/tabview';
import { api, demoUser, type Change, type Facility, type Summary } from '../api';

export default function ReferenceScreen() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [firms, setFirms] = useState<Facility[]>([]);
  const [changes, setChanges] = useState<Change[]>([]);
  const [ports, setPorts] = useState<{ code: string; name: string }[]>([]);
  const [countries, setCountries] = useState<{ iso: string; name: string }[]>([]);
  const [foreignPorts, setForeignPorts] = useState<{ code: string; name: string }[]>([]);
  const [carriers, setCarriers] = useState<{ code: string; name: string; mode_name: string }[]>([]);
  const [q, setQ] = useState('');
  const [error, setError] = useState('');
  const admin = demoUser() === 'admin';

  const loadFirms = (term: string) => {
    api.firms(`q=${encodeURIComponent(term)}`).then((res) => setFirms(res.rows)).catch((err: Error) => setError(err.message));
  };

  useEffect(() => {
    api.summary().then(setSummary).catch((err: Error) => setError(err.message));
    loadFirms('');
    api.ports().then((res) => setPorts(res.rows)).catch(() => undefined);
    api.countries().then((res) => setCountries(res.rows)).catch(() => undefined);
    api.foreignPorts().then((res) => setForeignPorts(res.rows)).catch(() => undefined);
    api.carriers().then((res) => setCarriers(res.rows)).catch(() => undefined);
    if (admin) api.changes().then((res) => setChanges(res.changes)).catch(() => undefined);
  }, [admin]);

  return (
    <div className="p-4">
      <h1 className="mt-0" style={{ color: '#11304C' }}>Reference tables</h1>
      <p className="kn-help">Shared CHB reference data. An individual query updates a row. A whole-file load is admin only. These table names are provisional until engineering connects the CHB schema.</p>
      <div className="flex flex-wrap gap-3 mb-3">
        {summary?.files.map((file) => (
          <div key={file.file_code} className="kn-card">
            <div className="text-sm font-bold" style={{ letterSpacing: '0.12em' }}>{file.file_code}</div>
            <div className="text-3xl font-bold" style={{ color: '#458CFC' }}>{file.count}</div>
            <div className="kn-help">Last pull {file.last_pull ? new Date(file.last_pull).toLocaleString() : 'never'}</div>
          </div>
        ))}
      </div>
      {error && <p role="alert">{error}</p>}
      <TabView>
        <TabPanel header="FIRMS">
          <label htmlFor="firms-search" className="font-bold text-sm">Search</label>
          <InputText id="firms-search" className="ml-2 mb-3" value={q} onChange={(event) => { setQ(event.target.value); loadFirms(event.target.value); }} />
          <DataTable value={firms} paginator rows={15} emptyMessage="No facilities stored yet.">
            <Column field="firms_code" header="FIRMS" sortable />
            <Column field="name" header="Name" sortable />
            <Column field="status" header="Status" sortable />
            <Column field="facility_type" header="Type" sortable />
            <Column field="district_port" header="District/port" sortable />
            <Column field="state" header="State" sortable />
            <Column field="city" header="City" />
          </DataTable>
        </TabPanel>
        {admin && (
          <TabPanel header="Change log">
            <DataTable value={changes} paginator rows={15} emptyMessage="No changes recorded.">
              <Column field="changed_at" header="When" />
              <Column field="firms_code" header="FIRMS" />
              <Column field="change_type" header="Change" />
              <Column field="field_name" header="Field" />
              <Column field="old_value" header="From" />
              <Column field="new_value" header="To" />
              <Column field="source_control_id" header="Control ID" />
            </DataTable>
          </TabPanel>
        )}
        <TabPanel header="Ports">
          <DataTable value={ports} paginator rows={15} emptyMessage="Run an admin F101 load.">
            <Column field="code" header="Code" />
            <Column field="name" header="Name" />
          </DataTable>
        </TabPanel>
        <TabPanel header="Countries">
          <DataTable value={countries} paginator rows={15} emptyMessage="Run an admin F102 load.">
            <Column field="iso" header="ISO" />
            <Column field="name" header="Name" />
          </DataTable>
        </TabPanel>
        <TabPanel header="Foreign ports">
          <DataTable value={foreignPorts} paginator rows={15} emptyMessage="Run an admin F104 load.">
            <Column field="code" header="Code" />
            <Column field="name" header="Name" />
          </DataTable>
        </TabPanel>
        <TabPanel header="Carriers">
          <DataTable value={carriers} paginator rows={15} emptyMessage="No carriers stored yet.">
            <Column field="code" header="Code" />
            <Column field="name" header="Name" />
            <Column field="mode_name" header="Mode" />
          </DataTable>
        </TabPanel>
      </TabView>
    </div>
  );
}
