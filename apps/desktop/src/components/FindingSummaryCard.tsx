import { Badge } from './Badge';
import { EvidenceCallout } from './EvidenceCallout';
import { TrialDetailsGrid } from './TrialDetailsGrid';
import { formatStatusLabel, relevanceTone, statusTone } from '../lib/findingPresentation';
import type { Finding } from '../lib/types';

type FindingSummaryCardProps = {
  finding: Finding;
  showWhy?: boolean;
  showSourceLink?: boolean;
};

export function FindingSummaryCard({
  finding,
  showWhy = false,
  showSourceLink = true
}: FindingSummaryCardProps) {
  const timestamp = finding.published_at || finding.retrieved_at;

  return (
    <article className="finding-item">
      <div className="finding-topline">
        <div>
          <strong>{finding.title}</strong>
          <div className="muted">
            {finding.source_name} • {finding.type} • {new Date(timestamp).toLocaleString()}
          </div>
        </div>
        <div className="badge-row">
          <Badge label={formatStatusLabel(finding.status)} tone={statusTone(finding.status)} />
          <Badge label={finding.relevance_label} tone={relevanceTone(finding.relevance_label)} />
        </div>
      </div>

      <p>{finding.normalized_summary || finding.raw_summary || 'No summary available.'}</p>
      <TrialDetailsGrid finding={finding} />
      <EvidenceCallout finding={finding} />

      {showWhy && (
        <div className="detail-grid">
          <div>
            <strong>Why it surfaced</strong>
            <div className="multiline">{finding.why_it_surfaced || 'No structured rationale stored.'}</div>
          </div>
          <div>
            <strong>Why it may not fit</strong>
            <div className="multiline">{finding.why_it_may_not_fit || 'No cautions stored.'}</div>
          </div>
        </div>
      )}

      {showSourceLink && finding.source_url && (
        <a href={finding.source_url} target="_blank" rel="noreferrer" className="source-link">
          Open source
        </a>
      )}
    </article>
  );
}
