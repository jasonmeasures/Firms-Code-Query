import { Dropdown } from 'primereact/dropdown';
import { demoUser, setDemoUser } from '../api';

const OPTIONS = [
  { label: 'Operator — own requests only', value: 'operator' },
  { label: 'Admin — whole-file loads and every request', value: 'admin' },
];

export default function RoleBar({ onChange }: { onChange: () => void }) {
  return (
    <div className="flex align-items-center gap-2">
      <label htmlFor="demo-role" className="kn-help font-bold">Demo role</label>
      <Dropdown
        inputId="demo-role"
        value={demoUser()}
        options={OPTIONS}
        onChange={(event) => {
          setDemoUser(event.value);
          onChange();
        }}
      />
    </div>
  );
}
