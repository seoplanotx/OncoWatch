import { useEffect, useState } from 'react';

import { Card } from '../components/Card';
import { api } from '../lib/api';
import type { AppSettings, ProviderConfig, SourceConfig } from '../lib/types';

export function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [provider, setProvider] = useState<ProviderConfig | null>(null);
  const [sources, setSources] = useState<SourceConfig[]>([]);
  const [apiKey, setApiKey] = useState('');
  const [models, setModels] = useState<string[]>([]);
  const [message, setMessage] = useState('');

  async function load() {
    const [settingsResult, providerResult, sourceResult, modelResult] = await Promise.all([
      api.getSettings(),
      api.getProviderConfig(),
      api.getSources(),
      api.getOpenRouterModels()
    ]);
    setSettings(settingsResult);
    setProvider(providerResult);
    setSources(sourceResult);
    setModels(modelResult);
  }

  useEffect(() => {
    load();
  }, []);

  if (!settings) return <div className="loading-block">Loading settings…</div>;

  async function saveGeneral() {
    const saved = await api.updateSettings(settings);
    setSettings(saved);
    setMessage('Settings saved locally.');
  }

  async function saveProvider() {
    const saved = await api.saveProviderConfig({
      provider_key: 'openrouter',
      display_name: 'OpenRouter',
      selected_model: provider?.selected_model,
      api_key: apiKey || undefined
    });
    setProvider(saved);
    setMessage('Provider settings saved.');
  }

  async function testKey() {
    if (!apiKey.trim()) {
      setMessage('Paste an API key to test.');
      return;
    }
    const result = await api.testOpenRouterKey({ api_key: apiKey, model: provider?.selected_model });
    setMessage(result.message);
    if (result.discovered_models.length) setModels(result.discovered_models);
  }

  async function saveSource(source: SourceConfig) {
    const saved = await api.updateSource(source.id, { enabled: source.enabled, settings_json: source.settings_json });
    setSources((current) => current.map((item) => (item.id === saved.id ? saved : item)));
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <div className="eyebrow">Configuration</div>
          <h1>Settings</h1>
          <p className="page-lede">Provider setup, scheduling, and local source controls for the desktop workspace.</p>
        </div>
      </div>

      {message && <div className="callout">{message}</div>}

      <Card title="General settings" description="Adjust when OncoWatch runs and the default briefing format it generates.">
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
              <option value="daily_summary">Daily summary</option>
              <option value="full_review">Full oncology review</option>
            </select>
          </div>
        </div>
        <button className="primary-button" onClick={saveGeneral}>
          Save general settings
        </button>
      </Card>

      <Card title="OpenRouter" description="Optional model access for summaries and explanation text. It is not used to determine treatment.">
        <div className="stack">
          <p className="muted">
            OpenRouter is optional. It is used only for summarization and explanation tasks, not for deciding treatment.
          </p>
          <div className="field">
            <label>API key</label>
            <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="Paste new API key to update" />
          </div>
          <div className="field">
            <label>Model</label>
            <select
              value={provider?.selected_model || models[0] || ''}
              onChange={(e) => setProvider((current) => ({ ...(current || { provider_key: 'openrouter', display_name: 'OpenRouter', is_configured: false }), selected_model: e.target.value }))}
            >
              {models.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </div>
          <div className="button-row">
            <button className="secondary-button" onClick={testKey}>
              Test API key
            </button>
            <button className="primary-button" onClick={saveProvider}>
              Save provider settings
            </button>
          </div>
        </div>
      </Card>

      <Card title="Sources" description="Enable or disable connectors without changing the local-first storage model.">
        <div className="stack">
          {sources.map((source) => (
            <div className="toggle-row" key={source.id}>
              <label className="toggle-row">
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
                  <div className="muted">{source.connector_key}</div>
                </div>
              </label>
              <button className="ghost-button" onClick={() => saveSource(source)}>
                Save
              </button>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
