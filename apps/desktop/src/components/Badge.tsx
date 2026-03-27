type BadgeProps = {
  label: string;
  tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info';
};

export function Badge({ label, tone = 'neutral' }: BadgeProps) {
  return <span className={`badge badge-${tone}`}>{label}</span>;
}
