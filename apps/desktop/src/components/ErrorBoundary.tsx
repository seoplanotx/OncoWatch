import { Component, type ErrorInfo, type ReactNode } from 'react';

type Props = {
  children: ReactNode;
};

type State = {
  hasError: boolean;
};

export class ErrorBoundary extends Component<Props, State> {
  state: State = {
    hasError: false
  };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('OncoWatch render failure', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="app-loading">
          <div className="recovery-card">
            <div className="eyebrow">Unexpected error</div>
            <h1>OncoWatch ran into a rendering problem.</h1>
            <p className="muted">
              Reload the app first. If this keeps happening, reopen OncoWatch and review the local logs from the
              support page.
            </p>
            <div className="button-row">
              <button className="primary-button" onClick={() => window.location.reload()}>
                Reload app
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
