import { useState } from 'react';
import { NavLink, Route, Routes } from 'react-router-dom';
import RoleBar from './components/RoleBar';
import Home from './pages/Home';
import JobScreen from './pages/JobScreen';
import QueryScreen from './pages/QueryScreen';
import ReferenceScreen from './pages/ReferenceScreen';
import RequestScreen from './pages/RequestScreen';
import VaultScreen from './pages/VaultScreen';

const links = [
  ['/', 'Reference files'],
  ['/reference', 'Tables'],
  ['/vault', 'MQ / EDI'],
];

export default function App() {
  const [tick, setTick] = useState(0);
  return (
    <div key={tick}>
      <header className="kn-topbar flex justify-content-between align-items-center flex-wrap gap-3">
        <div>
          <div className="text-sm font-bold" style={{ letterSpacing: '0.16em', color: '#005D7C' }}>KLEARNOW</div>
          <strong>CBP reference files</strong>
        </div>
        <nav className="flex gap-1" aria-label="CBP reference files">
          {links.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `kn-nav-btn${isActive ? ' active' : ''}`}>
              {label}
            </NavLink>
          ))}
        </nav>
        <RoleBar onChange={() => setTick((value) => value + 1)} />
      </header>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/query/:fileCode" element={<QueryScreen />} />
        <Route path="/requests/:requestId" element={<RequestScreen />} />
        <Route path="/jobs/:jobId" element={<JobScreen />} />
        <Route path="/reference" element={<ReferenceScreen />} />
        <Route path="/vault" element={<VaultScreen />} />
      </Routes>
    </div>
  );
}
