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
    () => ['Welcome', 'Patient Profile', 'OpenRouter', 'Monitoring Preferences', 'Test Run', 'Complete'],
    []
  );

  async function saveProfile(tempProfile: PatientProfile) {
    setProfile(tempProfile);
    setStep(2);
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
    setBusy(true);
    try {
      const result = await api.getHealth();
      setHealth(result);
      setStep(5);
    } finally {
      setBusy(false);
    }
  }

  async function finalize() {
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
    } finally {
      setBusy(false);
    }
  }

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
        <ol className="step-list">
          {steps.map((label, index) => (
            <li key={label} className={index === step ? 'step-item active' : 'step-item'}>
              <span>{index + 1}</span>
              <div>{label}</div>
            </li>
          ))}
        </ol>
      </div>

      <div className="onboarding-content">
        {step === 0 && (
          <Card title="Welcome to OncoWatch">
            <div className="stack">
              <p>
                OncoWatch helps patients and families monitor oncology information that <strong>may be relevant</strong>
                so they can bring structured, source-backed notes to a doctor visit.
              </p>
              <p>
                It can help you keep up with clinical trials, literature, drug updates, and biomarker-related findings.
              </p>
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
          <Card title="Patient profile setup">
            <p className="muted">
              Enter the details you already know. Leave anything blank that you are unsure about.
            </p>
            <ProfileForm initialValue={profile} onSave={saveProfile} submitLabel="Save and continue" />
          </Card>
        )}

        {step === 2 && (
          <Card title="OpenRouter setup">
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
                <button className="secondary-button" onClick={async () => {
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
                }}>
                  Continue
                </button>
              </div>
              {testMessage && <div className="callout">{testMessage}</div>}
              {providerState?.is_configured && <div className="muted">Saved model: {providerState.selected_model || 'not set'}</div>}
            </div>
          </Card>
        )}

        {step === 3 && (
          <Card title="Monitoring preferences">
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
          <Card title="Test run">
            <div className="stack">
              <p>
                This checks local storage, the database, enabled sources, PDF generation, and model setup if you entered a key.
              </p>
              <button className="primary-button" disabled={busy} onClick={runHealth}>
                {busy ? 'Running checks…' : 'Run health check'}
              </button>
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
          <Card title="Setup complete">
            <div className="stack">
              <p>OncoWatch is ready on this computer.</p>
              <p>Next scheduled run: {settings.daily_run_time} each day.</p>
              <p>Reports will be saved in the local OncoWatch reports folder.</p>
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
