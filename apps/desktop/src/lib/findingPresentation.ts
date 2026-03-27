import type { BadgeTone } from '../components/Badge';

export function formatStatusLabel(status: string) {
  return status.replace(/_/g, ' ').toUpperCase();
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
