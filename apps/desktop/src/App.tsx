import { useEffect, useState } from 'react';
import { HashRouter, Route, Routes } from 'react-router-dom';

import { Layout } from './components/Layout';
import { RecoveryScreen } from './components/RecoveryScreen';
import { OnboardingWizard } from './features/onboarding/OnboardingWizard';
import { API_BASE, api } from './lib/api';
import { getErrorMessage } from './lib/errors';
import type { BootstrapInfo, OnboardingState } from './lib/types';
import { DashboardPage } from './pages/DashboardPage';
import { FindingsPage } from './pages/FindingsPage';
import { ProfilePage } from './pages/ProfilePage';
import { ReportsPage } from './pages/ReportsPage';
import { SettingsPage } from './pages/SettingsPage';
import { SupportPage } from './pages/SupportPage';
import { TrialMatchesPage } from './pages/TrialMatchesPage';
import { UpdatesPage } from './pages/UpdatesPage';

const BOOT_ATTEMPTS = 6;
const BOOT_RETRY_DELAYS_MS = [250, 400, 650, 900, 1200];

function wait(delayMs: number) {
  return new Promise((resolve) => window.setTimeout(resolve, delayMs));
}

export default function App() {
  const [bootstrap, setBootstrap] = useState<BootstrapInfo | null>(null);
  const [onboardingState, setOnboardingState] = useState<OnboardingState | null>(null);
  const [loading, setLoading] = useState(true);
  const [bootError, setBootError] = useState<string | null>(null);
  const [loadingLabel, setLoadingLabel] = useState('Starting local OncoWatch services...');

  async function load() {
    setLoading(true);
    setBootError(null);

    let lastError: unknown = null;
    for (let attempt = 1; attempt <= BOOT_ATTEMPTS; attempt += 1) {
      setLoadingLabel(
        attempt === 1
          ? 'Starting local OncoWatch services...'
          : `Waiting for the local backend to start (${attempt}/${BOOT_ATTEMPTS})...`
      );
      try {
        const [bootstrapInfo, onboarding] = await Promise.all([api.getBootstrap(), api.getOnboardingState()]);
        setBootstrap(bootstrapInfo);
        setOnboardingState(onboarding);
        setLoading(false);
        return;
      } catch (error) {
        lastError = error;
        if (attempt < BOOT_ATTEMPTS) {
          await wait(BOOT_RETRY_DELAYS_MS[Math.min(attempt - 1, BOOT_RETRY_DELAYS_MS.length - 1)]);
        }
      }
    }

    setBootstrap(null);
    setOnboardingState(null);
    setBootError(getErrorMessage(lastError, 'OncoWatch could not reach its local backend.'));
    setLoading(false);
  }

  useEffect(() => {
    void load();
  }, []);

  if (loading) {
    return <div className="app-loading">{loadingLabel}</div>;
  }

  if (bootError) {
    return <RecoveryScreen errorMessage={bootError} apiBase={API_BASE} onRetry={load} />;
  }

  if (!bootstrap || !onboardingState) {
    return <RecoveryScreen errorMessage="The local app did not initialize correctly." apiBase={API_BASE} onRetry={load} />;
  }

  if (!onboardingState.is_completed) {
    return <OnboardingWizard onCompleted={load} />;
  }

  return (
    <HashRouter>
      <Layout disclaimer={bootstrap.disclaimer}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/findings" element={<FindingsPage />} />
          <Route path="/trials" element={<TrialMatchesPage />} />
          <Route path="/updates" element={<UpdatesPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/support" element={<SupportPage bootstrap={bootstrap} />} />
        </Routes>
      </Layout>
    </HashRouter>
  );
}
