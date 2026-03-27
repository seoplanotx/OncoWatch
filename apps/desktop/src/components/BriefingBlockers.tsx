import { Card } from './Card';
import { EmptyState } from './EmptyState';
import type { BriefingBlocker } from '../lib/types';

type BriefingBlockersProps = {
  blockers: BriefingBlocker[];
};

export function BriefingBlockers({ blockers }: BriefingBlockersProps) {
  return (
    <Card title="Confidence blockers / missing info" action={<span className="section-counter">{blockers.length} tracked</span>}>
      {blockers.length === 0 ? (
        <EmptyState
          title="No explicit blockers"
          message="The highest-priority findings did not include structured missing-information blockers."
        />
      ) : (
        <div className="blocker-list">
          {blockers.map((blocker) => (
            <article className="blocker-item" key={blocker.label}>
              <div className="blocker-topline">
                <strong>{blocker.label}</strong>
                <span className="section-counter">{blocker.finding_count} findings</span>
              </div>
              {blocker.examples.length > 0 && (
                <div className="muted">Seen in: {blocker.examples.join(', ')}</div>
              )}
            </article>
          ))}
        </div>
      )}
    </Card>
  );
}
