import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from 'primereact/card';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { api, type ExtractRequest, type FileSpec } from '../api';
import { statusClass } from '../lib/status';

export default function Home() {
  const navigate = useNavigate();
  const [files, setFiles] = useState<FileSpec[]>([]);
  const [rows, setRows] = useState<ExtractRequest[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    api.files().then((res) => setFiles(res.files)).catch((err: Error) => setError(err.message));
    api.requests().then((res) => setRows(res.requests)).catch((err: Error) => setError(err.message));
  }, []);

  return (
    <div className="p-4">
      <p className="mt-0" style={{ maxWidth: '70ch' }}>
        Loads the ACE reference files the CHB platform keeps current: ports, countries, foreign ports,
        carriers, tariff updates, and FIRMS facilities. Whole-file loads are admin only.
      </p>
      {error && <p role="alert">{error}</p>}
      <div className="grid">
        {files.map((file) => (
          <div key={file.file_code} className="col-12 md:col-6 xl:col-4">
            <button
              type="button"
              className="kn-card w-full text-left cursor-pointer"
              onClick={() => navigate(`/query/${file.file_code}`)}
            >
              <div className="text-sm font-bold mb-2" style={{ letterSpacing: '0.12em', color: '#005D7C' }}>{file.file_code} · {file.app_in}/{file.app_out}</div>
              <h2 className="mt-0 mb-2" style={{ color: '#11304C' }}>{file.title}</h2>
              <p className="kn-help m-0">{file.summary}</p>
              <p className="kn-help mb-0">Spec {file.spec}</p>
            </button>
          </div>
        ))}
      </div>
      <Card className="mt-4" title="Requests you can see">
        <DataTable value={rows} emptyMessage="No requests yet." onRowClick={(event) => navigate(`/requests/${event.data.id}`)} rowHover>
          <Column field="file_code" header="File" />
          <Column field="query_type" header="Query" />
          <Column field="control_id" header="Control ID" />
          <Column field="kn_number" header="KN number" />
          <Column field="status" header="Status" body={(row: ExtractRequest) => <span className={statusClass(row.status)}>{row.status}</span>} />
        </DataTable>
      </Card>
    </div>
  );
}
