export type BadgeTone = 'neutral' | 'success' | 'warning' | 'danger' | 'info';

type BadgeProps = {
  label: string;
  tone?: BadgeTone;
};

export function Badge({ label, tone = 'neutral' }: BadgeProps) {
  return <span className={`badge badge-${tone}`}>{label}</span>;
}
