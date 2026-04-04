import { useEffect, useMemo, useState } from 'react';

import { Card } from '../../components/Card';
import { api } from '../../lib/api';
import { getErrorMessage } from '../../lib/errors';
import type { AppSettings, HealthResponse, PatientProfile, SourceConfig } from '../../lib/types';
import { ProfileForm } from '../profile/ProfileForm';

type Props = {
  onCompleted: () => Promise<void>;
};

const defaultSettings: AppSettings = {
  daily_run_time: '08:30',
  default_report_style: 'clinical',
  default_report_length: 'daily_summary',
  demo_profile_enabled: false
};

const blankProfile: PatientProfile = {
  profile_name: 'My profile',
  display_name: '',
  date_of_birth: '',
  cancer_type: '',
  subtype: '',
  stage_or_context: '',
  current_therapy_status: '',
  location_label: '',
  travel_radius_miles: 100,
  notes: '',
  would_consider: [],
  would_not_consider: [],
  is_active: true,
  biomarkers: [{ name: '', variant: '', status: '', notes: '' }],
  therapy_history: [{ therapy_name: '', therapy_type: '', line_of_therapy: '', status: '', notes: '' }]
};

export function OnboardingWizard({ onCompleted }: Props) {
  const [step, setStep] = useState(0);
  const [profile, setProfile] = useState<PatientProfile>(blankProfile);
  const [settings, setSettings] = useState<AppSettings>(defaultSettings);
  const [sources, setSources] = useState<SourceConfig[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    async function load() {
      setBusy(true);
      setErrorMessage('');
      try {
        const [appSettings, sourceConfigs] = await Promise.all([api.getSettings(), api.getSources()]);
        setSettings(appSettings);
        setSources(sourceConfigs);
      } catch (error) {
        setErrorMessage(getErrorMessage(error, 'Could not load local onboarding settings.'));
      } finally {
        setBusy(false);
      }
    }

    void load();
  }, []);

  const steps = useMemo(
    () => [
      {
        label: 'Welcome',
        title: 'Set up a calm local briefing workflow.',
        description: 'OncoWatch focuses on real trial and literature monitoring, conservative language, and clinician review.'
      },
      {
        label: 'Patient Profile',
        title: 'Add the profile facts that drive matching.',
        description: 'Only enter the facts you already know. Leaving uncertain fields blank is safer than guessing.'
      },
      {
        label: 'Monitoring Preferences',
        title: 'Choose when OncoWatch can run while it is open.',
        description: 'This release keeps monitoring local and truthful: automatic runs only happen while the app stays open.'
      },
      {
        label: 'Health Check',
        title: 'Verify local storage, reports, and the enabled real sources.',
        description: 'Blocking issues must be fixed before the dashboard opens. Warnings can be revisited later.'
      },
      {
        label: 'Complete',
        title: 'Finish setup and open the dashboard.',
        description: 'After setup, start with a manual run and use while-open scheduling only when this Mac is active.'
      }
    ],
    []
  );

  async function saveProfile(tempProfile: PatientProfile) {
    setErrorMessage('');
    setProfile(tempProfile);
    setStep(2);
  }

  function continueFromPreferences() {
    setErrorMessage('');
    setNotice('');
    if (!sources.some((source) => source.enabled)) {
      setErrorMessage('Enable at least one real source before continuing.');
      return;
    }
    setStep(3);
  }

  async function runHealth() {
    setErrorMessage('');
    setNotice('');
    setBusy(true);
    try {
      const result = await api.getHealth();
      setHealth(result);
      if (result.overall_ok && result.items.some((item) => !item.ok && !item.blocking)) {
        setNotice('Setup can continue. Resolve warnings later if you choose.');
      } else if (result.overall_ok) {
        setNotice('This Mac is ready for local monitoring and report generation.');
      }
    } catch (error) {
      setHealth(null);
      setErrorMessage(getErrorMessage(error, 'Could not run the health check.'));
    } finally {
      setBusy(false);
    }
  }

  async function finalize() {
    setErrorMessage('');
    setNotice('');
    setBusy(true);
    try {
      const saved = await api.createProfile(profile);
      await api.updateSettings({
        ...settings,
        default_profile_id: saved.id
      });

      await Promise.all(
        sources.map((source) =>
          api.updateSource(source.id, {
            enabled: source.enabled,
            settings_json: source.settings_json
          })
        )
      );

      await api.completeOnboarding({
        current_step: 'completed',
        welcome_acknowledged: true,
        is_completed: true
      });

      await onCompleted();
    } catch (error) {
      setErrorMessage(getErrorMessage(error, 'Could not finish setup.'));
    } finally {
      setBusy(false);
    }
  }

  const currentStep = steps[step];
  const progress = ((step + 1) / steps.length) * 100;
  const hasBlockingHealthFailure = health ? !health.overall_ok : false;

  return (
    <div className="onboarding-shell">
      <div className="onboarding-sidebar">
        <div className="sidebar-brand large">
          <div className="brand-mark">O</div>
          <div>
            <strong>OncoWatch</strong>
            <div className="muted">Set up local oncology monitoring</div>
          </div>
        </div>
        <div className="onboarding-sidebar-copy">
          <div className="eyebrow">Private setup</div>
          <h1>Build a steady trial and literature briefing routine.</h1>
          <p>
            Profiles, reports, and logs stay on this computer. Findings stay conservative and still need clinician review.
          </p>
        </div>
        <ol className="step-list">
          {steps.map((item, index) => (
            <li key={item.label} className={index === step ? 'step-item active' : 'step-item'}>
              <span>{index + 1}</span>
              <div>
                <strong>{item.label}</strong>
                <div>{item.description}</div>
              </div>
            </li>
          ))}
        </ol>
        <div className="onboarding-note">
          <strong>Public v1 scope</strong>
          <p>
            This release tracks real ClinicalTrials.gov and PubMed results. It does not surface demo feeds, treatment
            advice, or eligibility decisions.
          </p>
        </div>
      </div>

      <div className="onboarding-content">
        <div className="onboarding-progress">
          <div>
            <div className="eyebrow">
              Step {step + 1} of {steps.length}
            </div>
            <h2>{currentStep.title}</h2>
            <p className="muted">{currentStep.description}</p>
          </div>
          <div className="progress-track" aria-hidden="true">
            <div className="progress-bar" style={{ width: `${progress}%` }} />
          </div>
        </div>

        {step === 0 && (
          <Card
            title="Welcome to OncoWatch"
            description="A local-first workspace for tracking real public oncology information that may be worth discussing with a care team."
          >
            <div className="stack">
              <p>
                OncoWatch helps patients and families monitor oncology information that <strong>may be relevant</strong>{' '}
                so they can bring structured, source-backed notes to a doctor visit.
              </p>
              <p>
                This public release focuses on ClinicalTrials.gov trial matching, PubMed literature monitoring, and local
                PDF briefings.
              </p>
              <div className="mini-stats-grid onboarding-highlights">
                <div className="mini-stat">
                  <span className="mini-stat-label">Trials</span>
                  <strong>ClinicalTrials.gov</strong>
                </div>
                <div className="mini-stat">
                  <span className="mini-stat-label">Literature</span>
                  <strong>PubMed excerpts</strong>
                </div>
                <div className="mini-stat">
                  <span className="mini-stat-label">Reports</span>
                  <strong>Local PDF briefings</strong>
                </div>
              </div>
              <div className="callout">
                It does <strong>not</strong> determine treatment, confirm eligibility, or replace an oncology team.
              </div>
              {errorMessage && <div className="callout callout-danger">{errorMessage}</div>}
              <button className="primary-button" onClick={() => setStep(1)} disabled={busy}>
                Start setup
              </button>
            </div>
          </Card>
        )}

        {step === 1 && (
          <Card
            title="Patient profile setup"
            description="Enter the details you already know. Leave anything blank that you are unsure about."
          >
            <ProfileForm initialValue={profile} onSave={saveProfile} submitLabel="Save and continue" />
          </Card>
        )}

        {step === 2 && (
          <Card
            title="Monitoring preferences"
            description="Choose when OncoWatch can run while it is open and confirm which real sources are enabled."
          >
            <div className="stack">
              <div className="form-grid">
                <div className="field">
                  <label>Automatic run time while OncoWatch is open</label>
                  <input
                    type="time"
                    value={settings.daily_run_time}
                    onChange={(e) => setSettings({ ...settings, daily_run_time: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label>Report style</label>
                  <select
                    value={settings.default_report_style}
                    onChange={(e) => setSettings({ ...settings, default_report_style: e.target.value })}
                  >
                    <option value="clinical">Clinical</option>
                    <option value="plain">Plain English</option>
                  </select>
                </div>
                <div className="field">
                  <label>Default report type</label>
                  <select
                    value={settings.default_report_length}
                    onChange={(e) => setSettings({ ...settings, default_report_length: e.target.value })}
                  >
                    <option value="daily_summary">Short daily summary</option>
                    <option value="full_review">Full oncology review</option>
                  </select>
                </div>
              </div>

              <div className="callout">
                Automatic runs are local and truthful in this release: they only happen while OncoWatch stays open on this
                Mac. You can always start a manual run from the dashboard.
              </div>

              <div className="section-divider">Enabled real sources</div>
              <div className="stack">
                {sources.map((source) => (
                  <label className="toggle-row" key={source.id}>
                    <input
                      type="checkbox"
                      checked={source.enabled}
                      onChange={(e) =>
                        setSources((current) =>
                          current.map((item) => (item.id === source.id ? { ...item, enabled: e.target.checked } : item))
                        )
                      }
                    />
                    <div>
                      <strong>{source.name}</strong>
                      <div className="muted">{source.category}</div>
                    </div>
                  </label>
                ))}
              </div>

              {errorMessage && <div className="callout callout-danger">{errorMessage}</div>}

              <div className="button-row">
                <button className="ghost-button" onClick={() => setStep(1)}>
                  Back
                </button>
                <button className="primary-button" onClick={continueFromPreferences}>
                  Continue
                </button>
              </div>
            </div>
          </Card>
        )}

        {step === 3 && (
          <Card
            title="Health check"
            description="This checks local storage, the database, PDF generation, and the enabled real data sources."
          >
            <div className="stack">
              <button className="primary-button" disabled={busy} onClick={runHealth}>
                {busy ? 'Running checks...' : 'Run health check'}
              </button>
              {errorMessage && <div className="callout callout-danger">{errorMessage}</div>}
              {notice && <div className="callout">{notice}</div>}
              {health && (
                <div className="health-grid">
                  {health.items.map((item) => {
                    const statusClass = item.ok ? 'ok' : item.blocking ? 'error' : 'warning';
                    return (
                      <div key={item.key} className={`health-item ${statusClass}`}>
                        <strong>{item.label}</strong>
                        <div>{item.message}</div>
                        <div className="muted">{item.blocking ? 'Blocking check' : 'Warning only'}</div>
                      </div>
                    );
                  })}
                </div>
              )}
              {hasBlockingHealthFailure && (
                <div className="callout callout-danger">
                  Resolve the blocking items before finishing setup.
                </div>
              )}
              <div className="button-row">
                <button className="ghost-button" onClick={() => setStep(2)}>
                  Back
                </button>
                <button
                  className="primary-button"
                  onClick={() => setStep(4)}
                  disabled={!health || hasBlockingHealthFailure}
                >
                  Continue
                </button>
              </div>
            </div>
          </Card>
        )}

        {step === 4 && (
          <Card
            title="Setup complete"
            description="The workspace is configured locally and ready to open the main dashboard."
          >
            <div className="stack">
              <p>OncoWatch is ready on this computer.</p>
              <p>Automatic run time while the app stays open: {settings.daily_run_time}.</p>
              <p>Reports will be saved in the local OncoWatch reports folder.</p>
              <div className="callout">
                Start with a manual run once the dashboard opens. Automatic runs only happen while OncoWatch stays open on
                this Mac.
              </div>
              {errorMessage && <div className="callout callout-danger">{errorMessage}</div>}
              <button className="primary-button" disabled={busy} onClick={finalize}>
                {busy ? 'Finishing...' : 'Open dashboard'}
              </button>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
