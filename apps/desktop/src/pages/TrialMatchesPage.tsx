import { useEffect, useState } from 'react';

import { Badge } from '../components/Badge';
import { Card } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { api } from '../lib/api';
import type { Finding } from '../lib/types';

export function TrialMatchesPage() {
  const [items, setItems] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const result = await api.getFindings({ finding_type: 'clinical_trials' });
        setItems(result.items);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div className="loading-block">Loading trial matches…</div>;

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <h1>Trial Matches</h1>
          <p className="muted">Possible trial-oriented matches based on currently entered profile data.</p>
        </div>
      </div>

      <Card title="Possible matches">
        {items.length === 0 ? (
          <EmptyState title="No trial matches stored" message="Trial-oriented findings will appear here after a monitoring run." />
        ) : (
          <div className="finding-list">
            {items.map((item) => (
              <article className="finding-item" key={item.id}>
                <div className="finding-topline">
                  <div>
                    <strong>{item.title}</strong>
                    <div className="muted">{item.source_name}</div>
                  </div>
                  <Badge
                    label={item.relevance_label}
                    tone={item.relevance_label === 'High relevance' ? 'success' : 'info'}
                  />
                </div>
                <div className="detail-grid">
                  <div>
                    <strong>Status / location</strong>
                    <div>{item.location_summary || 'Location details not stored.'}</div>
                  </div>
                  <div>
                    <strong>Score</strong>
                    <div>{item.score}</div>
                  </div>
                </div>
                <p>{item.normalized_summary || item.raw_summary}</p>
                <div className="multiline">
                  <strong>Gaps:</strong>
                  {' '}
                  {item.matching_gaps.length ? item.matching_gaps.join(' ') : 'No gaps stored.'}
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
