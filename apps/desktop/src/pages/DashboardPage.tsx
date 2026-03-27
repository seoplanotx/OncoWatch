import { useEffect, useState } from 'react';

import { Badge } from '../components/Badge';
import { Card } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { EvidenceCallout } from '../components/EvidenceCallout';
import { TrialDetailsGrid } from '../components/TrialDetailsGrid';
import { api } from '../lib/api';
import type { Dashboard } from '../lib/types';

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

  if (loading) return <div className="loading-block">Loading dashboard…</div>;
  if (!data) return <EmptyState title="Dashboard unavailable" message="The dashboard could not be loaded." />;

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p className="muted">Latest monitoring snapshot for this local profile.</p>
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

      <Card title="Recent surfaced items">
        {data.recent_findings.length === 0 ? (
          <EmptyState title="No findings stored" message="Once a run completes, findings will appear here." />
        ) : (
          <div className="finding-list">
            {data.recent_findings.map((finding) => (
              <article key={finding.id} className="finding-item">
                <div className="finding-topline">
                  <div>
                    <strong>{finding.title}</strong>
                    <div className="muted">
                      {finding.source_name} • {finding.type}
                    </div>
                  </div>
                  <div className="badge-row">
                    <Badge label={finding.status.toUpperCase()} tone={finding.status === 'new' ? 'info' : 'warning'} />
                    <Badge
                      label={finding.relevance_label}
                      tone={
                        finding.relevance_label === 'High relevance'
                          ? 'success'
                          : finding.relevance_label === 'Worth reviewing'
                          ? 'info'
                          : finding.relevance_label === 'Low confidence'
                          ? 'warning'
                          : 'danger'
                      }
                    />
                  </div>
                </div>
                <p>{finding.normalized_summary || finding.raw_summary}</p>
                <TrialDetailsGrid finding={finding} />
                <EvidenceCallout finding={finding} />
              </article>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
