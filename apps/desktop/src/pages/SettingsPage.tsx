import { useEffect, useState } from 'react';

import { Card } from '../components/Card';
import { PageErrorState } from '../components/PageErrorState';
import { api } from '../lib/api';
import { getErrorMessage } from '../lib/errors';
import type { AppSettings, SourceConfig } from '../lib/types';

export function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [sources, setSources] = useState<SourceConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);

  async function load() {
    setLoading(true);
    setErrorMessage('');
    try {
      const [settingsResult, sourceResult] = await Promise.all([api.getSettings(), api.getSources()]);
      setSettings(settingsResult);
      setSources(sourceResult);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, 'Could not load local settings.'));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (loading) return <div className="loading-block">Loading settings...</div>;
  if (errorMessage && !settings) {
    return <PageErrorState title="Settings unavailable" message={errorMessage} onRetry={load} />;
  }
  if (!settings) {
    return <PageErrorState title="Settings unavailable" message="The local settings payload was empty." onRetry={load} />;
  }

  async function saveGeneral() {
    setBusy(true);
    setErrorMessage('');
    setNotice('');
    try {
      const saved = await api.updateSettings(settings);
      setSettings(saved);
      setNotice('Settings saved locally.');
    } catch (error) {
      setErrorMessage(getErrorMessage(error, 'Could not save local settings.'));
    } finally {
      setBusy(false);
    }
  }

  async function saveSource(source: SourceConfig) {
    setBusy(true);
    setErrorMessage('');
    setNotice('');
    try {
      const saved = await api.updateSource(source.id, { enabled: source.enabled, settings_json: source.settings_json });
      setSources((current) => current.map((item) => (item.id === saved.id ? saved : item)));
      setNotice(`${saved.name} updated locally.`);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, 'Could not update the selected source.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <div className="eyebrow">Configuration</div>
          <h1>Settings</h1>
          <p className="page-lede">
            Adjust while-open monitoring, report defaults, and the real sources available in this release.
          </p>
        </div>
      </div>

      {notice && <div className="callout">{notice}</div>}
      {errorMessage && <div className="callout callout-danger">{errorMessage}</div>}

      <Card
        title="General settings"
        description="Automatic runs are local and only happen while OncoWatch remains open on this Mac."
      >
        <div className="form-grid">
          <div className="field">
            <label>Automatic run time while open</label>
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
        <div className="button-row">
          <button className="primary-button" onClick={saveGeneral} disabled={busy}>
            Save general settings
          </button>
          <button className="secondary-button" onClick={() => (window.location.hash = '#/support')}>
            Open support details
          </button>
        </div>
      </Card>

      <Card
        title="Real sources"
        description="This public release keeps the source list honest: ClinicalTrials.gov and PubMed only."
      >
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
              <button className="ghost-button" onClick={() => void saveSource(source)} disabled={busy}>
                Save
              </button>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
