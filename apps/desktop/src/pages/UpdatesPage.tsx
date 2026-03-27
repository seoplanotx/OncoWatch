import { useEffect, useState } from 'react';

import { Card } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { FindingSummaryCard } from '../components/FindingSummaryCard';
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
          <div className="eyebrow">Literature and updates</div>
          <h1>Research / Drug Updates</h1>
          <p className="page-lede">Literature, drug, safety, and biomarker-related findings in one calmer feed with explicit source context.</p>
        </div>
        <div className="page-header-actions">
          <span className="section-counter">{items.length} stored</span>
        </div>
      </div>

      <Card
        title="Updates"
        description="These records keep the evidence excerpt and the reason each item was surfaced side by side."
      >
        {items.length === 0 ? (
          <EmptyState title="No updates stored" message="Run monitoring to populate literature and drug-related items." />
        ) : (
          <div className="finding-list">
            {items.map((item) => (
              <FindingSummaryCard key={item.id} finding={item} showWhy />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
