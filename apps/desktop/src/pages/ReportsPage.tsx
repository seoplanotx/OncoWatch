import { useEffect, useState } from 'react';

import { Card } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { api } from '../lib/api';
import type { ReportExport } from '../lib/types';

export function ReportsPage() {
  const [reports, setReports] = useState<ReportExport[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const result = await api.getReports();
      setReports(result);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function generate(reportType: string) {
    setBusy(true);
    try {
      await api.generateReport({ report_type: reportType });
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function download(reportId: number, reportType: string) {
    const blob = await api.downloadReport(reportId);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `oncowatch-${reportType}.pdf`;
    link.click();
    window.URL.revokeObjectURL(url);
  }

  if (loading) return <div className="loading-block">Loading reports…</div>;

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <h1>Reports</h1>
          <p className="muted">Generate clinician-friendly PDF briefings locally.</p>
        </div>
      </div>

      <Card title="Generate report">
        <div className="button-row">
          <button className="primary-button" disabled={busy} onClick={() => generate('daily_summary')}>
            Generate daily summary
          </button>
          <button className="secondary-button" disabled={busy} onClick={() => generate('full_review')}>
            Generate full oncology review
          </button>
        </div>
      </Card>

      <Card title="Report history">
        {reports.length === 0 ? (
          <EmptyState title="No reports yet" message="Generate a report to start the local report history." />
        ) : (
          <div className="finding-list">
            {reports.map((report) => (
              <article className="finding-item" key={report.id}>
                <div className="finding-topline">
                  <div>
                    <strong>{report.report_type === 'daily_summary' ? 'Daily Summary Report' : 'Full Oncology Review Report'}</strong>
                    <div className="muted">{new Date(report.generated_at).toLocaleString()}</div>
                  </div>
                  <button className="secondary-button" onClick={() => download(report.id, report.report_type)}>
                    Download PDF
                  </button>
                </div>
                <div className="muted">{report.file_path}</div>
              </article>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
