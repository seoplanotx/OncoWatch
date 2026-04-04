type PageErrorStateProps = {
  title: string;
  message: string;
  onRetry?: () => void | Promise<void>;
};

export function PageErrorState({ title, message, onRetry }: PageErrorStateProps) {
  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <div className="eyebrow">Local error</div>
          <h1>{title}</h1>
          <p className="page-lede">{message}</p>
        </div>
      </div>

      <div className="recovery-card">
        <p className="muted">
          Retry after the local backend finishes starting, or reopen OncoWatch if the problem persists.
        </p>
        {onRetry && (
          <div className="button-row">
            <button className="primary-button" onClick={() => void onRetry()}>
              Retry
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
