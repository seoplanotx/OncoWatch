import type { ReactNode } from 'react';

type CardProps = {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
};

export function Card({ title, action, children }: CardProps) {
  return (
    <section className="card">
      {(title || action) && (
        <div className="card-header">
          {title ? <h3>{title}</h3> : <span />}
          {action}
        </div>
      )}
      <div className="card-body">{children}</div>
    </section>
  );
}
