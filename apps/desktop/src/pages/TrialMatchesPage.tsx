import { useEffect, useState } from 'react';

import { Card } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { FindingSummaryCard } from '../components/FindingSummaryCard';
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
          <div className="eyebrow">Trial review</div>
          <h1>Trial Matches</h1>
          <p className="page-lede">Possible trial-oriented matches based on the current local profile and deterministic matching rules.</p>
        </div>
        <div className="page-header-actions">
          <span className="section-counter">{items.length} stored</span>
        </div>
      </div>

      <Card
        title="Possible matches"
        description="Review recruitment status, interventions, score, and explicit gaps before treating any result as actionable."
      >
        {items.length === 0 ? (
          <EmptyState title="No trial matches stored" message="Trial-oriented findings will appear here after a monitoring run." />
        ) : (
          <div className="finding-list">
            {items.map((item) => (
              <FindingSummaryCard key={item.id} finding={item} showWhy showMatchingMeta />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
