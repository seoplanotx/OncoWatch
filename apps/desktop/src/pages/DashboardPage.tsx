import { useEffect, useMemo, useState } from 'react';

import { BriefingBlockers } from '../components/BriefingBlockers';
import { BriefingSection } from '../components/BriefingSection';
import { Card } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { api } from '../lib/api';
import type { Dashboard } from '../lib/types';

function jumpToSection(anchorId: string) {
  document.getElementById(anchorId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

export function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const result = await api.getDashboard();
      setData(result);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleRunNow() {
    await api.triggerRun();
    await load();
  }

  const latestRunLabel = useMemo(() => {
    if (!data) return 'Run monitoring to populate the first briefing.';
    if (data.briefing.latest_run_completed_at) {
      return `Latest completed run: ${new Date(data.briefing.latest_run_completed_at).toLocaleString()}`;
    }
    if (data.latest_run) {
      return `Latest run started: ${new Date(data.latest_run.started_at).toLocaleString()}`;
    }
    return 'Run monitoring to populate the first briefing.';
  }, [data]);

  if (loading) return <div className="loading-block">Loading dashboard…</div>;
  if (!data) return <EmptyState title="Dashboard unavailable" message="The dashboard could not be loaded." />;

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <div className="eyebrow">Daily monitoring</div>
          <h1>Dashboard</h1>
          <p className="page-lede">Scan what is new, what changed, and where clinician review still needs extra context.</p>
        </div>
        <div className="page-header-actions">
          <button className="primary-button" onClick={handleRunNow}>
            Run now
          </button>
        </div>
      </div>

      <div className="stats-grid">
        <Card title="New findings" description="Since the last completed run." className="stat-card">
          <div className="stat-value">{data.counts.new || 0}</div>
        </Card>
        <Card title="Changed findings" description="Existing items with meaningful updates." className="stat-card">
          <div className="stat-value">{data.counts.changed || 0}</div>
        </Card>
        <Card title="High relevance" description="Items currently surfaced as the strongest fit." className="stat-card">
          <div className="stat-value">{data.counts.high_relevance || 0}</div>
        </Card>
        <Card title="Trial matches" description="Trial-oriented findings worth a closer review." className="stat-card">
          <div className="stat-value">{data.counts.trial_matches || 0}</div>
        </Card>
      </div>

      <Card
        title="What changed since last run?"
        description={latestRunLabel}
        className="hero-card"
        action={
          <button className="secondary-button" onClick={() => (window.location.hash = '#/reports')}>
            Open reports
          </button>
        }
      >
        <div className="briefing-hero">
          <div className="briefing-copy">
            <div className="eyebrow">Daily briefing</div>
            <h2>Start with the net-new items, then review changes that may affect follow-up questions.</h2>
            <p className="muted">{data.disclaimer}</p>
          </div>
          <div className="briefing-metrics">
            <div className="briefing-metric">
              <span className="briefing-metric-label">New</span>
              <strong>{data.briefing.new_count}</strong>
            </div>
            <div className="briefing-metric">
              <span className="briefing-metric-label">Changed</span>
              <strong>{data.briefing.changed_count}</strong>
            </div>
            <div className="briefing-metric">
              <span className="briefing-metric-label">Blockers</span>
              <strong>{data.briefing.blockers.length}</strong>
            </div>
          </div>
        </div>

        <div className="button-row hero-actions">
          <button className="secondary-button" onClick={() => jumpToSection('dashboard-new-findings')}>
            View new findings
          </button>
          <button className="secondary-button" onClick={() => jumpToSection('dashboard-changed-findings')}>
            View changed findings
          </button>
          <button className="secondary-button" onClick={() => jumpToSection('dashboard-blockers')}>
            View blockers
          </button>
        </div>
      </Card>

      <div className="dashboard-layout">
        <div className="dashboard-main-column">
          {data.briefing.sections.map((section) => (
            <BriefingSection
              key={section.key}
              section={section}
              anchorId={`dashboard-${section.key.replace(/_/g, '-')}`}
            />
          ))}
        </div>

        <div className="dashboard-side-column">
          <Card
            title="Run status"
            description="Monitoring cadence and the most recent execution details."
            className="side-panel-card"
          >
            {data.latest_run ? (
              <div className="detail-grid">
                <div>
                  <strong>Last run</strong>
                  <div>{new Date(data.latest_run.started_at).toLocaleString()}</div>
                </div>
                <div>
                  <strong>Status</strong>
                  <div>{data.latest_run.status}</div>
                </div>
                <div>
                  <strong>Triggered by</strong>
                  <div>{data.latest_run.triggered_by}</div>
                </div>
                <div>
                  <strong>Next scheduled run</strong>
                  <div>{data.next_scheduled_run ? new Date(data.next_scheduled_run).toLocaleString() : 'Not scheduled'}</div>
                </div>
              </div>
            ) : (
              <EmptyState title="No runs yet" message="Use Run now to populate the first monitoring results." />
            )}
          </Card>

          <div id="dashboard-blockers">
            <BriefingBlockers blockers={data.briefing.blockers} />
          </div>

          <Card title="Recent surfaced items" description="A quick glance at the latest stored records." className="side-panel-card">
            {data.recent_findings.length === 0 ? (
              <EmptyState title="No findings stored" message="Once a run completes, findings will appear here." />
            ) : (
              <div className="headline-list">
                {data.recent_findings.slice(0, 5).map((item) => (
                  <article className="headline-item" key={item.id}>
                    <strong>{item.title}</strong>
                    <div className="muted">
                      {item.source_name} • {new Date(item.published_at || item.retrieved_at).toLocaleString()}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
