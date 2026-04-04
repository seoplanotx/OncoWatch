import { NavLink } from 'react-router-dom';

const primaryItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/findings', label: 'Findings Feed' },
  { to: '/trials', label: 'Trial Matches' },
  { to: '/updates', label: 'Literature Updates' },
  { to: '/reports', label: 'Reports' }
];

const secondaryItems = [
  { to: '/profile', label: 'Patient Profile' },
  { to: '/settings', label: 'Settings' },
  { to: '/support', label: 'About / Support' }
];

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-panel">
        <div className="sidebar-brand">
          <div className="brand-mark">O</div>
          <div>
            <strong>OncoWatch</strong>
            <div className="muted">Calm local oncology monitoring</div>
          </div>
        </div>

        <div className="sidebar-summary">
          <div className="sidebar-summary-label">Workspace</div>
          <p className="sidebar-summary-copy">
            A private briefing surface for real ClinicalTrials.gov and PubMed monitoring on this Mac.
          </p>
        </div>

        <div className="sidebar-nav-group">
          <div className="sidebar-section-label">Monitor</div>
          <nav className="sidebar-nav">
            {primaryItems.map((item) => (
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
        </div>

        <div className="sidebar-nav-group">
          <div className="sidebar-section-label">Configure</div>
          <nav className="sidebar-nav">
            {secondaryItems.map((item) => (
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
        </div>

        <div className="sidebar-trust">
          <div className="sidebar-trust-label">Trust guardrails</div>
          <p className="sidebar-trust-copy">
            Profiles, reports, and logs stay local. Findings are informational and still need clinician review.
          </p>
        </div>
      </div>
    </aside>
  );
}
