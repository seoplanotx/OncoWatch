import type { ReactNode } from 'react';

import { DisclaimerBanner } from './DisclaimerBanner';
import { Sidebar } from './Sidebar';

type LayoutProps = {
  children: ReactNode;
};

export function Layout({ children }: LayoutProps) {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="app-main">
        <DisclaimerBanner />
        <div className="page-content">{children}</div>
        <footer className="footer-note">
          OncoWatch surfaces information that may be relevant. It does not replace a clinician.
        </footer>
      </main>
    </div>
  );
}
