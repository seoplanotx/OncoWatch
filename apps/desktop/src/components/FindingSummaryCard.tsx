import { Badge } from './Badge';
import { EvidenceCallout } from './EvidenceCallout';
import { TrialDetailsGrid } from './TrialDetailsGrid';
import {
  formatFindingTypeLabel,
  formatStatusLabel,
  relevanceTone,
  statusTone,
  typeTone
} from '../lib/findingPresentation';
import type { Finding } from '../lib/types';

type FindingSummaryCardProps = {
  finding: Finding;
  showWhy?: boolean;
  showSourceLink?: boolean;
  showMatchingMeta?: boolean;
};

export function FindingSummaryCard({
  finding,
  showWhy = false,
  showSourceLink = true,
  showMatchingMeta = false
}: FindingSummaryCardProps) {
  const timestamp = finding.published_at || finding.retrieved_at;
  const metaItems = [
    { label: 'Captured', value: new Date(timestamp).toLocaleString() },
    { label: 'Source', value: finding.source_name },
    { label: 'Record', value: finding.external_identifier }
  ];
  const supportingItems = [
    { label: 'Location context', value: finding.location_summary || 'Location details not stored.' },
    { label: 'Match score', value: String(finding.score) },
    {
      label: 'Missing information',
      value: finding.matching_gaps.length ? finding.matching_gaps.join(' ') : 'No structured gaps stored.'
    }
  ];

  return (
    <article className="finding-item">
      <div className="finding-topline">
        <div className="finding-heading">
          <div className="finding-eyebrow">{formatFindingTypeLabel(finding.type)}</div>
          <h3 className="finding-title">{finding.title}</h3>
        </div>
        <div className="badge-row">
          <Badge label={formatFindingTypeLabel(finding.type)} tone={typeTone(finding.type)} />
          <Badge label={formatStatusLabel(finding.status)} tone={statusTone(finding.status)} />
          <Badge label={finding.relevance_label} tone={relevanceTone(finding.relevance_label)} />
        </div>
      </div>

      <p className="finding-summary">{finding.normalized_summary || finding.raw_summary || 'No summary available.'}</p>

      <div className="finding-meta-strip">
        {metaItems.map((item) => (
          <div className="finding-meta-item" key={item.label}>
            <span className="finding-meta-label">{item.label}</span>
            <strong>{item.value}</strong>
          </div>
        ))}
      </div>

      <TrialDetailsGrid finding={finding} />

      {showMatchingMeta && (
        <div className="detail-grid finding-support-grid">
          {supportingItems.map((item) => (
            <div className="support-card" key={item.label}>
              <div className="support-card-label">{item.label}</div>
              <div>{item.value}</div>
            </div>
          ))}
        </div>
      )}

      <EvidenceCallout finding={finding} />

      {showWhy && (
        <div className="detail-grid finding-rationale-grid">
          <div className="support-card">
            <div className="support-card-label">Why it surfaced</div>
            <div className="multiline">{finding.why_it_surfaced || 'No structured rationale stored.'}</div>
          </div>
          <div className="support-card caution">
            <div className="support-card-label">Why it may not fit</div>
            <div className="multiline">{finding.why_it_may_not_fit || 'No cautions stored.'}</div>
          </div>
        </div>
      )}

      {showSourceLink && finding.source_url && (
        <div className="finding-footer">
          <a href={finding.source_url} target="_blank" rel="noreferrer" className="source-link">
            Open source record
          </a>
        </div>
      )}
    </article>
  );
}
