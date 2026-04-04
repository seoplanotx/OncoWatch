import { Card } from '../components/Card';
import type { BootstrapInfo } from '../lib/types';

type SupportPageProps = {
  bootstrap: BootstrapInfo;
};

export function SupportPage({ bootstrap }: SupportPageProps) {
  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <div className="eyebrow">About and support</div>
          <h1>About / Support</h1>
          <p className="page-lede">
            Local product details, storage locations, privacy notes, and the quickest recovery steps if something goes
            wrong.
          </p>
        </div>
      </div>

      <Card title="Release details" description="The public macOS release stays narrow and truthful.">
        <div className="detail-grid">
          <div>
            <strong>Version</strong>
            <div>{bootstrap.app_version}</div>
          </div>
          <div>
            <strong>Scope</strong>
            <div>{bootstrap.product_scope}</div>
          </div>
          <div>
            <strong>Monitoring mode</strong>
            <div>{bootstrap.monitoring_mode === 'while_open' ? 'Automatic runs while the app is open' : bootstrap.monitoring_mode}</div>
          </div>
          <div>
            <strong>Privacy</strong>
            <div>{bootstrap.privacy_summary}</div>
          </div>
        </div>
      </Card>

      <Card title="Local storage" description="These folders matter for support, debugging, and manual recovery.">
        <div className="detail-grid support-path-grid">
          <div>
            <strong>Data</strong>
            <div className="support-path">{bootstrap.data_dir}</div>
          </div>
          <div>
            <strong>Reports</strong>
            <div className="support-path">{bootstrap.reports_dir}</div>
          </div>
          <div>
            <strong>Logs</strong>
            <div className="support-path">{bootstrap.logs_dir}</div>
          </div>
          <div>
            <strong>Config</strong>
            <div className="support-path">{bootstrap.config_dir}</div>
          </div>
        </div>
      </Card>

      <Card title="Recovery steps" description="Use these steps before reinstalling the app.">
        <div className="stack">
          <div className="support-step">
            <strong>1. Retry startup or reopen OncoWatch.</strong>
            <div className="muted">The local backend may need a second launch window after an update or crash.</div>
          </div>
          <div className="support-step">
            <strong>2. Review the local log folder.</strong>
            <div className="muted">
              Open the logs path above and inspect the newest `oncowatch.log` entries for backend startup or connector
              failures.
            </div>
          </div>
          <div className="support-step">
            <strong>3. Back up your data folder before any reset.</strong>
            <div className="muted">
              Copy the data directory to a safe location before deleting app data, especially if you want to preserve
              profiles or reports.
            </div>
          </div>
          <div className="support-step">
            <strong>4. Reset only as a last resort.</strong>
            <div className="muted">
              Quit the app, back up the data and config folders, then remove them only if you need a clean first-launch
              state.
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
