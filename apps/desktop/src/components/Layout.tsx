import type { ReactNode } from 'react';

import { DisclaimerBanner } from './DisclaimerBanner';
import { Sidebar } from './Sidebar';

type LayoutProps = {
  children: ReactNode;
  disclaimer?: string;
};

export function Layout({ children, disclaimer }: LayoutProps) {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="app-main">
        <div className="shell-header">
          <div className="shell-header-copy">
            <div className="eyebrow">Local-first oncology briefings</div>
            <p className="shell-header-text">
              Designed to help patients and families prepare structured questions and source-backed notes for clinician
              review.
            </p>
          </div>
          <DisclaimerBanner disclaimer={disclaimer} />
        </div>
        <div className="page-content">{children}</div>
        <footer className="footer-note">
          <span>Profiles, settings, and reports stay on this device.</span>
          <span>OncoWatch may surface relevant information, but treatment and eligibility decisions still require a licensed oncology team.</span>
        </footer>
      </main>
    </div>
  );
}
