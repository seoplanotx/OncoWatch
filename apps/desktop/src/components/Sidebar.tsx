import { NavLink } from 'react-router-dom';

const items = [
  { to: '/', label: 'Dashboard' },
  { to: '/profile', label: 'Patient Profile' },
  { to: '/findings', label: 'Findings Feed' },
  { to: '/trials', label: 'Trial Matches' },
  { to: '/updates', label: 'Research / Drug Updates' },
  { to: '/reports', label: 'Reports' },
  { to: '/settings', label: 'Settings' }
];

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-mark">O</div>
        <div>
          <strong>OncoWatch</strong>
          <div className="muted">Local oncology monitoring</div>
        </div>
      </div>
      <nav className="sidebar-nav">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
