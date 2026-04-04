type RecoveryScreenProps = {
  errorMessage: string;
  apiBase: string;
  onRetry: () => void | Promise<void>;
};

export function RecoveryScreen({ errorMessage, apiBase, onRetry }: RecoveryScreenProps) {
  return (
    <div className="app-loading">
      <div className="recovery-card">
        <div className="eyebrow">Local backend recovery</div>
        <h1>OncoWatch could not finish starting its local service.</h1>
        <p className="muted">
          OncoWatch waits for the bundled backend for a few seconds on launch. If that startup window is missed, retry
          before reinstalling.
        </p>
        <div className="callout callout-danger">{errorMessage}</div>
        <div className="detail-grid recovery-details">
          <div>
            <strong>Expected API</strong>
            <div>{apiBase}</div>
          </div>
          <div>
            <strong>Next step</strong>
            <div>Retry startup, then reopen the app if it still fails.</div>
          </div>
        </div>
        <div className="button-row">
          <button className="primary-button" onClick={() => void onRetry()}>
            Retry startup
          </button>
        </div>
      </div>
    </div>
  );
}
