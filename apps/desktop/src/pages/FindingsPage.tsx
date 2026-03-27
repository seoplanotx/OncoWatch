import { useEffect, useMemo, useState } from 'react';

import { Card } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { FindingSummaryCard } from '../components/FindingSummaryCard';
import { api } from '../lib/api';
import { formatFindingTypeLabel } from '../lib/findingPresentation';
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

  const filterOptions = useMemo(
    () => [
      { value: '', label: 'All findings' },
      { value: 'clinical_trials', label: 'Clinical trials' },
      { value: 'literature', label: 'Literature' },
      { value: 'drug_updates', label: 'Drug updates' },
      { value: 'biomarker', label: 'Biomarkers' }
    ],
    []
  );
  const visibleMetrics = useMemo(
    () => ({
      highRelevance: visible.filter((item) => item.relevance_label === 'High relevance').length,
      newItems: visible.filter((item) => item.status === 'new').length,
      changedItems: visible.filter((item) => item.status === 'changed').length
    }),
    [visible]
  );

  if (loading) return <div className="loading-block">Loading findings…</div>;

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <div className="eyebrow">Source-backed feed</div>
          <h1>Findings Feed</h1>
          <p className="page-lede">Search across titles, summaries, trial metadata, and evidence snippets without changing the underlying stored results.</p>
        </div>
        <div className="page-header-actions">
          <span className="section-counter">{visible.length} shown</span>
        </div>
      </div>

      <Card
        title="Filter the feed"
        description="Search stays local and runs against the currently stored source-backed findings."
        className="filter-card"
      >
        <div className="toolbar toolbar-wide">
          <input placeholder="Search findings, evidence, sponsors, phases, or summaries" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <div className="filter-chip-row">
          {filterOptions.map((option) => (
            <button
              key={option.value || 'all'}
              className={filter === option.value ? 'filter-chip active' : 'filter-chip'}
              onClick={() => setFilter(option.value)}
              type="button"
            >
              {option.label}
            </button>
          ))}
        </div>
        <div className="mini-stats-grid">
          <div className="mini-stat">
            <span className="mini-stat-label">High relevance</span>
            <strong>{visibleMetrics.highRelevance}</strong>
          </div>
          <div className="mini-stat">
            <span className="mini-stat-label">New</span>
            <strong>{visibleMetrics.newItems}</strong>
          </div>
          <div className="mini-stat">
            <span className="mini-stat-label">Changed</span>
            <strong>{visibleMetrics.changedItems}</strong>
          </div>
          <div className="mini-stat">
            <span className="mini-stat-label">Category</span>
            <strong>{filter ? formatFindingTypeLabel(filter) : 'Mixed'}</strong>
          </div>
        </div>
      </Card>

      <Card title="Results" description="Each record keeps the source, evidence excerpt, and explicit rationale together.">
        {visible.length === 0 ? (
          <EmptyState title="No findings" message="Run monitoring or change filters to see surfaced items." />
        ) : (
          <div className="finding-list">
            {visible.map((item) => (
              <FindingSummaryCard key={item.id} finding={item} showWhy />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
