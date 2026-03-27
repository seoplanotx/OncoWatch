import { useEffect, useMemo, useState } from 'react';

import { BriefingBlockers } from '../components/BriefingBlockers';
import { BriefingSection } from '../components/BriefingSection';
import { Card } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { api } from '../lib/api';
import type { BriefingFindingSection, BriefingBlocker, ReportExport } from '../lib/types';

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

  const latestReport = useMemo(() => reports[0], [reports]);
  const latestSections = useMemo(
    () =>
      (Array.isArray(latestReport?.summary_json.sections)
        ? latestReport?.summary_json.sections
        : []) as BriefingFindingSection[],
    [latestReport]
  );
  const latestBlockers = useMemo(
    () =>
      (Array.isArray(latestReport?.summary_json.blockers)
        ? latestReport?.summary_json.blockers
        : []) as BriefingBlocker[],
    [latestReport]
  );

  if (loading) return <div className="loading-block">Loading reports…</div>;

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <div className="eyebrow">Local reports</div>
          <h1>Reports</h1>
          <p className="page-lede">Generate clinician-friendly PDF briefings locally and review the latest structured summary before downloading.</p>
        </div>
      </div>

      <Card title="Generate report" description="Reports are produced on this machine using the active local profile and stored findings.">
        <div className="button-row">
          <button className="primary-button" disabled={busy} onClick={() => generate('daily_summary')}>
            Generate daily summary
          </button>
          <button className="secondary-button" disabled={busy} onClick={() => generate('full_review')}>
            Generate full oncology review
          </button>
        </div>
      </Card>

      <Card title="Latest briefing preview" description="A structured preview of the most recent PDF briefing output.">
        {!latestReport ? (
          <EmptyState title="No reports yet" message="Generate a report to preview the latest briefing structure." />
        ) : latestSections.length === 0 ? (
          <div className="stack">
            <div className="muted">
              The latest report does not include structured briefing metadata yet. Generate a new report to refresh the preview.
            </div>
            <div>
              <strong>{latestReport.report_type === 'daily_summary' ? 'Daily Summary Report' : 'Full Oncology Review Report'}</strong>
              <div className="muted">{new Date(latestReport.generated_at).toLocaleString()}</div>
            </div>
          </div>
        ) : (
          <div className="page-stack">
            <div className="briefing-preview-header">
              <div>
                <strong>{latestReport.summary_json.report_title || 'OncoWatch briefing'}</strong>
                <div className="muted">
                  {latestReport.summary_json.generated_at
                    ? new Date(latestReport.summary_json.generated_at).toLocaleString()
                    : new Date(latestReport.generated_at).toLocaleString()}
                </div>
              </div>
              <div className="briefing-preview-metrics">
                <span className="section-counter">{latestReport.summary_json.new_count || 0} new</span>
                <span className="section-counter">{latestReport.summary_json.changed_count || 0} changed</span>
                <span className="section-counter">{latestBlockers.length} blockers</span>
              </div>
            </div>

            {latestSections.map((section) => (
              <BriefingSection key={section.key} section={section} showWhy={false} />
            ))}

            <BriefingBlockers blockers={latestBlockers} />
          </div>
        )}
      </Card>

      <Card title="Report history" description="Recent locally generated PDFs and their saved locations.">
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
