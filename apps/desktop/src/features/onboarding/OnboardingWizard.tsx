import { useEffect, useMemo, useState } from 'react';

import { api } from '../../lib/api';
import type { AppSettings, HealthResponse, PatientProfile, ProviderConfig, SourceConfig } from '../../lib/types';
import { Card } from '../../components/Card';
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
  const [apiKey, setApiKey] = useState('');
  const [selectedModel, setSelectedModel] = useState('openai/gpt-4.1-mini');
  const [modelOptions, setModelOptions] = useState<string[]>(['openai/gpt-4.1-mini']);
  const [providerState, setProviderState] = useState<ProviderConfig | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [demoProfile, setDemoProfile] = useState(false);
  const [testMessage, setTestMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    async function load() {
      const [appSettings, sourceConfigs, provider] = await Promise.all([
        api.getSettings(),
        api.getSources(),
        api.getProviderConfig()
      ]);
      setSettings(appSettings);
      setSources(sourceConfigs);
      setProviderState(provider);
      if (provider?.selected_model) setSelectedModel(provider.selected_model);
      try {
        const models = await api.getOpenRouterModels();
        if (models.length) setModelOptions(models.slice(0, 30));
      } catch {
        // keep fallback
      }
    }
    load();
  }, []);

  const steps = useMemo(
    () => [
      {
        label: 'Welcome',
        title: 'Set up a calmer local oncology briefing workspace.',
        description: 'OncoWatch stays focused on structured monitoring, conservative language, and clinician review.'
      },
      {
        label: 'Patient Profile',
        title: 'Add the core facts that should guide matching.',
        description: 'Only enter what you already know. Leaving uncertain fields blank is safer than filling them with guesses.'
      },
      {
        label: 'OpenRouter',
        title: 'Optionally connect a model provider for summaries.',
        description: 'This is optional and affects explanation text only. It does not change the underlying matching logic.'
      },
      {
        label: 'Monitoring Preferences',
        title: 'Choose cadence, report format, and enabled sources.',
        description: 'These settings shape the local daily workflow without changing the product’s conservative scope.'
      },
      {
        label: 'Test Run',
        title: 'Verify storage, enabled sources, and report generation.',
        description: 'A quick health pass helps confirm the local environment is ready before the dashboard opens.'
      },
      {
        label: 'Complete',
        title: 'Finish setup and open the dashboard.',
        description: 'Once complete, OncoWatch is ready to generate local daily briefings on this computer.'
      }
    ],
    []
  );

  async function saveProfile(tempProfile: PatientProfile) {
    setErrorMessage('');
    setProfile(tempProfile);
    setStep(2);
  }

  async function saveProviderAndContinue() {
    if (apiKey.trim()) {
      const saved = await api.saveProviderConfig({
        provider_key: 'openrouter',
        display_name: 'OpenRouter',
        selected_model: selectedModel,
        api_key: apiKey
      });
      setProviderState(saved);
    }

    setStep(3);
  }

  async function testOpenRouter() {
    if (!apiKey.trim()) {
      setTestMessage('Paste an API key first.');
      return;
    }
    setBusy(true);
    setTestMessage('Testing API key…');
    try {
      const result = await api.testOpenRouterKey({ api_key: apiKey, model: selectedModel });
      setTestMessage(result.message);
      if (result.discovered_models.length) {
        setModelOptions(result.discovered_models);
        if (!result.discovered_models.includes(selectedModel)) setSelectedModel(result.discovered_models[0]);
      }
    } catch (error) {
      setTestMessage(error instanceof Error ? error.message : 'Could not test the API key.');
    } finally {
      setBusy(false);
    }
  }

  async function runHealth() {
    setErrorMessage('');
    setBusy(true);
    try {
      const result = await api.getHealth();
      setHealth(result);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Could not run the health check.');
    } finally {
      setBusy(false);
    }
  }

  async function finalize() {
    setErrorMessage('');
    setBusy(true);
    try {
      let activeProfileId: number | undefined;
      if (demoProfile) {
        const demo = await api.createDemoProfile();
        activeProfileId = demo.profile_id;
      } else {
        const saved = await api.createProfile(profile);
        activeProfileId = saved.id;
      }

      await api.updateSettings({
        ...settings,
        default_profile_id: activeProfileId,
        demo_profile_enabled: demoProfile
      });

      if (apiKey.trim()) {
        await api.saveProviderConfig({
          provider_key: 'openrouter',
          display_name: 'OpenRouter',
          selected_model: selectedModel,
          api_key: apiKey
        });
      }

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
      setErrorMessage(error instanceof Error ? error.message : 'Could not finish setup.');
    } finally {
      setBusy(false);
    }
  }

  const currentStep = steps[step];
  const progress = ((step + 1) / steps.length) * 100;

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
          <h1>Build a steady daily briefing workflow.</h1>
          <p>
            Profiles, reports, and provider settings stay on this computer. Findings are surfaced conservatively and still
            need clinician review.
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
          <strong>Clinical review stays central.</strong>
          <p>
            OncoWatch can summarize public information and local profile context. It does not determine treatment or confirm
            eligibility.
          </p>
        </div>
      </div>

      <div className="onboarding-content">
        <div className="onboarding-progress">
          <div>
            <div className="eyebrow">Step {step + 1} of {steps.length}</div>
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
            description="A local-first workspace for tracking public oncology information that may be worth discussing with a care team."
          >
            <div className="stack">
              <p>
                OncoWatch helps patients and families monitor oncology information that <strong>may be relevant</strong>
                so they can bring structured, source-backed notes to a doctor visit.
              </p>
              <p>
                It can help you keep up with clinical trials, literature, drug updates, and biomarker-related findings.
              </p>
              <div className="mini-stats-grid onboarding-highlights">
                <div className="mini-stat">
                  <span className="mini-stat-label">Trials</span>
                  <strong>Structured matching</strong>
                </div>
                <div className="mini-stat">
                  <span className="mini-stat-label">Literature</span>
                  <strong>Evidence excerpts</strong>
                </div>
                <div className="mini-stat">
                  <span className="mini-stat-label">Reports</span>
                  <strong>Local PDF briefings</strong>
                </div>
              </div>
              <div className="callout">
                It does <strong>not</strong> determine treatment, confirm eligibility, or replace an oncology team.
              </div>
              <button className="primary-button" onClick={() => setStep(1)}>
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
            title="OpenRouter setup"
            description="Optional provider access for summary and explanation text. The key is stored locally on this machine."
          >
            <div className="stack">
              <p>
                You will need an API key so OncoWatch can generate optional summaries and explanation text.
              </p>
              <p>
                OpenRouter is a service that gives one API key access to many AI models. OncoWatch stores the key locally
                on this machine.
              </p>
              <div className="button-row">
                <button className="secondary-button" onClick={() => window.open('https://openrouter.ai', '_blank')}>
                  Open OpenRouter
                </button>
                <button className="ghost-button" onClick={() => setStep(3)}>
                  Skip for now
                </button>
              </div>
              <div className="callout">
                <strong>How to get your OpenRouter API key</strong>
                <ol>
                  <li>Open your OpenRouter account in the browser.</li>
                  <li>Create an API key.</li>
                  <li>Copy the key.</li>
                  <li>Paste it here.</li>
                  <li>Click “Test API Key”.</li>
                </ol>
                <p className="muted">Usage is billed through your OpenRouter account. OncoWatch does not bill you directly.</p>
              </div>

              <div className="field">
                <label>API key</label>
                <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="Paste your OpenRouter API key" />
              </div>
              <div className="field">
                <label>Model</label>
                <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)}>
                  {modelOptions.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
              </div>
              <div className="button-row">
                <button className="primary-button" onClick={testOpenRouter} disabled={busy}>
                  {busy ? 'Testing…' : 'Test API Key'}
                </button>
                <button className="secondary-button" onClick={saveProviderAndContinue}>
                  Continue
                </button>
              </div>
              {testMessage && <div className="callout">{testMessage}</div>}
              {providerState?.is_configured && <div className="muted">Saved model: {providerState.selected_model || 'not set'}</div>}
            </div>
          </Card>
        )}

        {step === 3 && (
          <Card
            title="Monitoring preferences"
            description="Choose the default daily cadence and keep only the source categories you want monitored."
          >
            <div className="form-grid">
              <div className="field">
                <label>Daily run time</label>
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
              <div className="field">
                <label>Use demo profile</label>
                <select value={demoProfile ? 'yes' : 'no'} onChange={(e) => setDemoProfile(e.target.value === 'yes')}>
                  <option value="no">No</option>
                  <option value="yes">Yes, load a sample profile</option>
                </select>
              </div>
            </div>

            <div className="section-divider">Enabled source categories</div>
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

            <div className="button-row">
              <button className="ghost-button" onClick={() => setStep(2)}>
                Back
              </button>
              <button className="primary-button" onClick={() => setStep(4)}>
                Continue
              </button>
            </div>
          </Card>
        )}

        {step === 4 && (
          <Card
            title="Test run"
            description="This checks local storage, the database, enabled sources, PDF generation, and model setup if you entered a key."
          >
            <div className="stack">
              <button className="primary-button" disabled={busy} onClick={runHealth}>
                {busy ? 'Running checks…' : 'Run health check'}
              </button>
              {errorMessage && <div className="callout">{errorMessage}</div>}
              {health && (
                <div className="health-grid">
                  {health.items.map((item) => (
                    <div key={item.key} className={item.ok ? 'health-item ok' : 'health-item error'}>
                      <strong>{item.label}</strong>
                      <div>{item.message}</div>
                    </div>
                  ))}
                </div>
              )}
              <div className="button-row">
                <button className="ghost-button" onClick={() => setStep(3)}>
                  Back
                </button>
                {health && (
                  <button className="primary-button" onClick={() => setStep(5)}>
                    Continue
                  </button>
                )}
              </div>
            </div>
          </Card>
        )}

        {step === 5 && (
          <Card
            title="Setup complete"
            description="The workspace is configured locally and ready to open the main dashboard."
          >
            <div className="stack">
              <p>OncoWatch is ready on this computer.</p>
              <p>Next scheduled run: {settings.daily_run_time} each day.</p>
              <p>Reports will be saved in the local OncoWatch reports folder.</p>
              {errorMessage && <div className="callout">{errorMessage}</div>}
              <button className="primary-button" disabled={busy} onClick={finalize}>
                {busy ? 'Finishing…' : 'Open dashboard'}
              </button>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
