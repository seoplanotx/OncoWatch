import { useEffect, useMemo, useState } from 'react';

import { BriefingBlockers } from '../components/BriefingBlockers';
import { BriefingSection } from '../components/BriefingSection';
import { Card } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { api } from '../lib/api';
import type { BriefingFindingSection, Dashboard } from '../lib/types';

function sectionByKey(sections: BriefingFindingSection[], key: string) {
  return sections.find((section) => section.key === key);
}

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

  const newSection = useMemo(
    () => (data ? sectionByKey(data.briefing.sections, 'new_findings') : undefined),
    [data]
  );
  const changedSection = useMemo(
    () => (data ? sectionByKey(data.briefing.sections, 'changed_findings') : undefined),
    [data]
  );

  if (loading) return <div className="loading-block">Loading dashboard…</div>;
  if (!data) return <EmptyState title="Dashboard unavailable" message="The dashboard could not be loaded." />;

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p className="muted">Daily briefing view for the active local profile.</p>
        </div>
        <button className="primary-button" onClick={handleRunNow}>
          Run now
        </button>
      </div>

      <div className="stats-grid">
        <Card title="New findings">
          <div className="stat-value">{data.counts.new || 0}</div>
        </Card>
        <Card title="Changed findings">
          <div className="stat-value">{data.counts.changed || 0}</div>
        </Card>
        <Card title="High relevance">
          <div className="stat-value">{data.counts.high_relevance || 0}</div>
        </Card>
        <Card title="Trial matches">
          <div className="stat-value">{data.counts.trial_matches || 0}</div>
        </Card>
      </div>

      <Card
        title="What changed since last run?"
        action={
          <button className="secondary-button" onClick={() => (window.location.hash = '#/reports')}>
            Open reports
          </button>
        }
      >
        <div className="briefing-hero">
          <div className="briefing-copy">
            <div className="eyebrow">Daily briefing</div>
            <h2>Scan what is new, then what materially changed.</h2>
            <p className="muted">
              {data.briefing.latest_run_completed_at
                ? `Latest completed run: ${new Date(data.briefing.latest_run_completed_at).toLocaleString()}`
                : data.latest_run
                ? `Latest run started: ${new Date(data.latest_run.started_at).toLocaleString()}`
                : 'Run monitoring to populate the first briefing.'}
            </p>
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

        <div className="button-row">
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

      <Card title="Run status">
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

      {data.briefing.sections.map((section) => (
        <BriefingSection
          key={section.key}
          section={section}
          anchorId={`dashboard-${section.key.replace(/_/g, '-')}`}
        />
      ))}

      <div id="dashboard-blockers">
        <BriefingBlockers blockers={data.briefing.blockers} />
      </div>

      {data.recent_findings.length === 0 && !newSection?.items.length && !changedSection?.items.length && (
        <Card title="Recent surfaced items">
          <EmptyState title="No findings stored" message="Once a run completes, findings will appear here." />
        </Card>
      )}
    </div>
  );
}
