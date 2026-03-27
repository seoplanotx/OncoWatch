import type { BadgeTone } from '../components/Badge';

export function formatStatusLabel(status: string) {
  return status.replace(/_/g, ' ').toUpperCase();
}

export function formatFindingTypeLabel(type: string) {
  if (type === 'clinical_trials') return 'Clinical trial';
  if (type === 'drug_updates') return 'Drug update';
  if (type === 'literature') return 'Literature';
  if (type === 'biomarker') return 'Biomarker';
  return type.replace(/_/g, ' ');
}

export function typeTone(type: string): BadgeTone {
  if (type === 'clinical_trials') return 'info';
  if (type === 'drug_updates') return 'warning';
  if (type === 'biomarker') return 'success';
  return 'neutral';
}

export function statusTone(status: string): BadgeTone {
  if (status === 'new') return 'info';
  if (status === 'changed') return 'warning';
  return 'neutral';
}

export function relevanceTone(relevanceLabel: string): BadgeTone {
  if (relevanceLabel === 'High relevance') return 'success';
  if (relevanceLabel === 'Worth reviewing') return 'info';
  if (relevanceLabel === 'Low confidence') return 'warning';
  return 'danger';
}
