import { useEffect, useState } from 'react';

import { Badge } from '../components/Badge';
import { Card } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { EvidenceCallout } from '../components/EvidenceCallout';
import { api } from '../lib/api';
import type { Finding } from '../lib/types';

export function UpdatesPage() {
  const [items, setItems] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const result = await api.getFindings();
        setItems(result.items.filter((item) => item.type !== 'clinical_trials'));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div className="loading-block">Loading research and drug updates…</div>;

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <h1>Research / Drug Updates</h1>
          <p className="muted">Literature, drug, safety, and biomarker-related findings in one view.</p>
        </div>
      </div>

      <Card title="Updates">
        {items.length === 0 ? (
          <EmptyState title="No updates stored" message="Run monitoring to populate literature and drug-related items." />
        ) : (
          <div className="finding-list">
            {items.map((item) => (
              <article className="finding-item" key={item.id}>
                <div className="finding-topline">
                  <div>
                    <strong>{item.title}</strong>
                    <div className="muted">{item.source_name}</div>
                  </div>
                  <Badge label={item.type} tone="info" />
                </div>
                <p>{item.normalized_summary || item.raw_summary}</p>
                <EvidenceCallout finding={item} />
                <div className="multiline">
                  <strong>Why it surfaced:</strong>
                  {' '}
                  {item.why_it_surfaced || 'No structured rationale stored.'}
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
