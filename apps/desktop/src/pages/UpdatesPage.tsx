import { useEffect, useState } from 'react';

import { Card } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { FindingSummaryCard } from '../components/FindingSummaryCard';
import { PageErrorState } from '../components/PageErrorState';
import { api } from '../lib/api';
import { getErrorMessage } from '../lib/errors';
import type { Finding } from '../lib/types';

export function UpdatesPage() {
  const [items, setItems] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  async function load() {
    setLoading(true);
    setErrorMessage('');
    try {
      const result = await api.getFindings({ finding_type: 'literature' });
      setItems(result.items);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, 'Could not load literature updates.'));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (loading) return <div className="loading-block">Loading literature updates...</div>;
  if (errorMessage && items.length === 0) {
    return <PageErrorState title="Literature unavailable" message={errorMessage} onRetry={load} />;
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <div className="eyebrow">Literature monitoring</div>
          <h1>Literature Updates</h1>
          <p className="page-lede">
            PubMed findings in one calmer feed with evidence excerpts and explicit source context.
          </p>
        </div>
        <div className="page-header-actions">
          <span className="section-counter">{items.length} stored</span>
        </div>
      </div>

      {errorMessage && <div className="callout callout-danger">{errorMessage}</div>}

      <Card
        title="Literature"
        description="These records keep the evidence excerpt and the reason each item was surfaced side by side."
      >
        {items.length === 0 ? (
          <EmptyState title="No literature stored" message="Run monitoring to populate PubMed findings." />
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
