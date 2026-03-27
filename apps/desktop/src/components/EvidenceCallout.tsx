import type { Finding } from '../lib/types';

type EvidenceCalloutProps = {
  finding: Pick<Finding, 'primary_evidence_label' | 'primary_evidence_snippet'>;
};

export function EvidenceCallout({ finding }: EvidenceCalloutProps) {
  if (!finding.primary_evidence_snippet) {
    return null;
  }

  return (
    <div className="evidence-callout">
      <div className="evidence-label">{finding.primary_evidence_label || 'Evidence excerpt'}</div>
      <div className="evidence-snippet">{finding.primary_evidence_snippet}</div>
    </div>
  );
}
