import type { ReactNode } from 'react';

type CardProps = {
  title?: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
};

export function Card({ title, description, action, children, className, bodyClassName }: CardProps) {
  return (
    <section className={className ? `card ${className}` : 'card'}>
      {(title || description || action) && (
        <div className="card-header">
          <div className="card-header-copy">
            {title ? <h3>{title}</h3> : null}
            {description ? <p className="card-description">{description}</p> : null}
          </div>
          {action ? <div className="card-action">{action}</div> : null}
        </div>
      )}
      <div className={bodyClassName ? `card-body ${bodyClassName}` : 'card-body'}>{children}</div>
    </section>
  );
}
