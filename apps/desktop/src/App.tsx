import { useEffect, useState } from 'react';
import { HashRouter, Route, Routes } from 'react-router-dom';

import { Layout } from './components/Layout';
import { OnboardingWizard } from './features/onboarding/OnboardingWizard';
import { api } from './lib/api';
import type { BootstrapInfo, OnboardingState } from './lib/types';
import { DashboardPage } from './pages/DashboardPage';
import { FindingsPage } from './pages/FindingsPage';
import { ProfilePage } from './pages/ProfilePage';
import { ReportsPage } from './pages/ReportsPage';
import { SettingsPage } from './pages/SettingsPage';
import { TrialMatchesPage } from './pages/TrialMatchesPage';
import { UpdatesPage } from './pages/UpdatesPage';

export default function App() {
  const [bootstrap, setBootstrap] = useState<BootstrapInfo | null>(null);
  const [onboardingState, setOnboardingState] = useState<OnboardingState | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const [bootstrapInfo, onboarding] = await Promise.all([api.getBootstrap(), api.getOnboardingState()]);
      setBootstrap(bootstrapInfo);
      setOnboardingState(onboarding);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (loading) {
    return <div className="app-loading">Loading OncoWatch…</div>;
  }

  if (!bootstrap || !onboardingState) {
    return <div className="app-loading">The local app did not initialize correctly.</div>;
  }

  if (!onboardingState.is_completed) {
    return <OnboardingWizard onCompleted={load} />;
  }

  return (
    <HashRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/findings" element={<FindingsPage />} />
          <Route path="/trials" element={<TrialMatchesPage />} />
          <Route path="/updates" element={<UpdatesPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </Layout>
    </HashRouter>
  );
}
