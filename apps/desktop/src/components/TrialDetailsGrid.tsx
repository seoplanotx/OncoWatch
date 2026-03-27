import type { Finding } from '../lib/types';

type TrialDetailsGridProps = {
  finding: Pick<
    Finding,
    'type' | 'trial_intervention_summary' | 'trial_phases' | 'trial_recruitment_status' | 'trial_sponsor'
  >;
};

function formatRecruitmentStatus(value?: string | null) {
  if (!value) {
    return null;
  }

  return value
    .toLowerCase()
    .replace(/_/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(' ');
}

export function TrialDetailsGrid({ finding }: TrialDetailsGridProps) {
  if (finding.type !== 'clinical_trials') {
    return null;
  }

  const details = [
    { label: 'Recruitment', value: formatRecruitmentStatus(finding.trial_recruitment_status) },
    { label: 'Phase', value: finding.trial_phases.length ? finding.trial_phases.join(', ') : null },
    { label: 'Sponsor', value: finding.trial_sponsor || null },
    { label: 'Interventions', value: finding.trial_intervention_summary || null }
  ].filter((item) => item.value);

  if (!details.length) {
    return null;
  }

  return (
    <div className="detail-grid trial-details-grid">
      {details.map((detail) => (
        <div key={detail.label}>
          <strong>{detail.label}</strong>
          <div>{detail.value}</div>
        </div>
      ))}
    </div>
  );
}
