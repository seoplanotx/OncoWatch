import { Card } from './Card';
import { EmptyState } from './EmptyState';
import { FindingSummaryCard } from './FindingSummaryCard';
import type { BriefingFindingSection } from '../lib/types';

type BriefingSectionProps = {
  section: BriefingFindingSection;
  anchorId?: string;
  showWhy?: boolean;
};

export function BriefingSection({ section, anchorId, showWhy = true }: BriefingSectionProps) {
  return (
    <div id={anchorId}>
      <Card
        title={section.title}
        description={section.description}
        action={<span className="section-counter">{section.count} total</span>}
      >
        {section.items.length === 0 ? (
          <EmptyState title={section.title} message={section.empty_message} />
        ) : (
          <div className="finding-list">
            {section.items.map((finding) => (
              <FindingSummaryCard key={finding.id} finding={finding} showWhy={showWhy} />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
