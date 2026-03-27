import { useEffect, useMemo, useState } from 'react';

import { Badge } from '../components/Badge';
import { Card } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { EvidenceCallout } from '../components/EvidenceCallout';
import { TrialDetailsGrid } from '../components/TrialDetailsGrid';
import { api } from '../lib/api';
import type { Finding } from '../lib/types';

export function FindingsPage() {
  const [items, setItems] = useState<Finding[]>([]);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const result = await api.getFindings();
      setItems(result.items);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const visible = useMemo(() => {
    return items.filter((item) => {
      const matchesType = filter ? item.type === filter : true;
      const matchesQuery = query
        ? [
            item.title,
            item.normalized_summary || '',
            item.raw_summary || '',
            item.primary_evidence_snippet || '',
            item.trial_recruitment_status || '',
            item.trial_sponsor || '',
            item.trial_intervention_summary || '',
            item.trial_phases.join(' ')
          ]
            .join(' ')
            .toLowerCase()
            .includes(query.toLowerCase())
        : true;
      return matchesType && matchesQuery;
    });
  }, [items, query, filter]);

  if (loading) return <div className="loading-block">Loading findings…</div>;

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <h1>Findings Feed</h1>
          <p className="muted">Source-backed items with explicit reasons and cautions.</p>
        </div>
      </div>

      <Card title="Filters">
        <div className="toolbar">
          <input placeholder="Search findings" value={query} onChange={(e) => setQuery(e.target.value)} />
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">All categories</option>
            <option value="clinical_trials">Clinical trials</option>
            <option value="literature">Literature</option>
            <option value="drug_updates">Drug updates</option>
            <option value="biomarker">Biomarker</option>
          </select>
        </div>
      </Card>

      <Card title={`Results (${visible.length})`}>
        {visible.length === 0 ? (
          <EmptyState title="No findings" message="Run monitoring or change filters to see surfaced items." />
        ) : (
          <div className="finding-list">
            {visible.map((item) => (
              <article className="finding-item" key={item.id}>
                <div className="finding-topline">
                  <div>
                    <strong>{item.title}</strong>
                    <div className="muted">
                      {item.source_name} • {new Date(item.retrieved_at).toLocaleString()}
                    </div>
                  </div>
                  <div className="badge-row">
                    <Badge label={item.status.toUpperCase()} tone={item.status === 'new' ? 'info' : 'warning'} />
                    <Badge
                      label={item.relevance_label}
                      tone={
                        item.relevance_label === 'High relevance'
                          ? 'success'
                          : item.relevance_label === 'Worth reviewing'
                          ? 'info'
                          : item.relevance_label === 'Low confidence'
                          ? 'warning'
                          : 'danger'
                      }
                    />
                  </div>
                </div>

                <p>{item.normalized_summary || item.raw_summary}</p>
                <TrialDetailsGrid finding={item} />
                <EvidenceCallout finding={item} />

                <div className="detail-grid">
                  <div>
                    <strong>Why it surfaced</strong>
                    <div className="multiline">{item.why_it_surfaced || 'No rationale stored.'}</div>
                  </div>
                  <div>
                    <strong>Why it may not fit</strong>
                    <div className="multiline">{item.why_it_may_not_fit || 'No cautions stored.'}</div>
                  </div>
                </div>

                {item.source_url && (
                  <a href={item.source_url} target="_blank" rel="noreferrer" className="source-link">
                    Open source
                  </a>
                )}
              </article>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
