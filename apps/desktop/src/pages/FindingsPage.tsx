import { useEffect, useMemo, useState } from 'react';

import { Card } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { FindingSummaryCard } from '../components/FindingSummaryCard';
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
              <FindingSummaryCard key={item.id} finding={item} showWhy />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
