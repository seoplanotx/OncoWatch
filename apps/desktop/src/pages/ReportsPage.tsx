import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { Badge } from '../components/Badge';
import { Card } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { PageErrorState } from '../components/PageErrorState';
import { ReportContents, outlineSummaryLine } from '../components/ReportContents';
import { api, ApiError } from '../lib/api';
import { getErrorMessage } from '../lib/errors';
import {
  downloadInBrowser,
  isDesktopShell,
  openReportFile,
  revealLabel,
  revealReportFile,
  saveReportCopy,
  suggestedFileName
} from '../lib/reportFile';
import type { ClinicianSummary, ReportExport, ReportOutline, ReportType } from '../lib/types';

const REPORT_TYPE_LABELS: Record<string, string> = {
  daily_summary: 'Daily summary report',
  full_review: 'Full oncology review report',
  appointment_prep: 'Appointment prep sheet'
};

function reportTypeLabel(reportType: string): string {
  return REPORT_TYPE_LABELS[reportType] || 'Full oncology review report';
}

// Lead with intent — what the family is preparing for — mapped onto the existing
// three report types. No change to report generation itself.
const INTENTS: { key: ReportType; title: string; detail: string }[] = [
  {
    key: 'appointment_prep',
    title: 'An upcoming appointment',
    detail: 'A focused one-page sheet to bring to a visit — the top things to raise and questions in one place.'
  },
  {
    key: 'daily_summary',
    title: 'A quick update to share',
    detail: 'A short summary of what is new, easy to email or hand to someone on the care team.'
  },
  {
    key: 'full_review',
    title: 'A comprehensive review',
    detail: 'Everything Firstlight has gathered, with an evidence appendix, for a thorough read.'
  }
];

const APPOINTMENT_KEY = 'firstlight.appointmentPrep';

type Appointment = { date: string; doctor: string };

function readAppointment(): Appointment {
  try {
    const raw = window.localStorage.getItem(APPOINTMENT_KEY);
    if (!raw) return { date: '', doctor: '' };
    const parsed = JSON.parse(raw) as Partial<Appointment>;
    return { date: typeof parsed.date === 'string' ? parsed.date : '', doctor: typeof parsed.doctor === 'string' ? parsed.doctor : '' };
  } catch {
    return { date: '', doctor: '' };
  }
}

// Which key profile details are still empty — used both to acknowledge gaps
// before generating and to phrase the readiness summary afterward.
function missingProfileDetails(summary: ClinicianSummary | null): string[] {
  if (!summary) return [];
  const header = summary.case_header;
  const missing: string[] = [];
  if (header.lines_of_therapy.length === 0) missing.push('Treatment line');
  if (header.biomarkers.length === 0) missing.push('Biomarkers');
  if (!header.stage_or_context) missing.push('Stage');
  return missing;
}

/**
 * The contents of an already-generated report. Reports made before the in-app
 * view shipped have no stored outline, so fall back to their briefing sections.
 */
function outlineFor(report: ReportExport): ReportOutline | null {
  const summary = report.summary_json || {};
  if (summary.outline) return summary.outline;
  if (!summary.sections) return null;
  return {
    report_type: report.report_type,
    report_title: summary.report_title || reportTypeLabel(report.report_type),
    sections: summary.sections.map((section) => ({
      key: section.key,
      title: section.title,
      description: section.description,
      empty_message: section.empty_message,
      count: section.count,
      items: section.items.map((item) => ({
        id: item.id,
        title: item.title,
        source_name: item.source_name,
        source_url: item.source_url,
        identifier: item.external_identifier,
        relevance_label: item.relevance_label,
        status: item.status,
        status_line: [item.source_name, item.relevance_label].filter(Boolean).join(' • '),
        why_it_surfaced: (item.why_it_surfaced || '').split('\n')[0] || null
      }))
    })),
    questions: [],
    gaps: (summary.blockers || []).map((blocker) => ({
      label: blocker.label,
      finding_count: blocker.finding_count,
      examples: blocker.examples
    })),
    counts: {
      findings: summary.finding_count,
      new: summary.new_count,
      changed: summary.changed_count
    }
  };
}

function relativeTime(iso: string): string {
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return '';
  const minutes = Math.round((Date.now() - then.getTime()) / 60_000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? '' : 's'} ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
  const days = Math.round(hours / 24);
  if (days <= 7) return `${days} day${days === 1 ? '' : 's'} ago`;
  return then.toLocaleDateString();
}

function fileName(path: string): string {
  const idx = Math.max(path.lastIndexOf('/'), path.lastIndexOf('\\'));
  return idx >= 0 ? path.slice(idx + 1) : path;
}

type Phase = 'choose' | 'prep' | 'done';

export function ReportsPage({ embedded = false }: { embedded?: boolean } = {}) {
  const [reports, setReports] = useState<ReportExport[]>([]);
  const [summary, setSummary] = useState<ClinicianSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | 'new' | null>(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [notice, setNotice] = useState('');

  const [phase, setPhase] = useState<Phase>('choose');
  const [intent, setIntent] = useState<ReportType | null>(null);
  const [preview, setPreview] = useState<ReportOutline | null>(null);
  const [appointment, setAppointment] = useState<Appointment>(readAppointment);
  const [lastGenerated, setLastGenerated] = useState<ReportExport | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [missingFileIds, setMissingFileIds] = useState<number[]>([]);
  const [printTarget, setPrintTarget] = useState<ReportOutline | null>(null);

  const desktop = useMemo(() => isDesktopShell(), []);

  async function load(options: { silent?: boolean } = {}) {
    if (!options.silent) setLoading(true);
    setErrorMessage('');
    try {
      const result = await api.getReports();
      setReports(result);
      // Best-effort: the page still works before a profile or a run exists.
      try {
        setSummary(await api.getClinicianSummary());
      } catch {
        setSummary(null);
      }
    } catch (error) {
      setErrorMessage(getErrorMessage(error, 'Could not load local reports.'));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(APPOINTMENT_KEY, JSON.stringify(appointment));
    } catch {
      // best-effort
    }
  }, [appointment]);

  // Ask the backend what this report would contain, so the preview and the PDF
  // are built from the same rules.
  useEffect(() => {
    if (phase !== 'prep' || !intent) return;
    let cancelled = false;
    setPreview(null);
    api
      .getReportPreview(intent)
      .then((result) => {
        if (!cancelled) setPreview(result);
      })
      .catch(() => {
        if (!cancelled) setPreview(null);
      });
    return () => {
      cancelled = true;
    };
  }, [phase, intent]);

  // Render the print sheet first, then hand the page to the OS print dialog.
  useEffect(() => {
    if (!printTarget) return;
    document.body.classList.add('printing-report');
    window.print();
    document.body.classList.remove('printing-report');
    setPrintTarget(null);
  }, [printTarget]);

  function startIntent(next: ReportType) {
    setIntent(next);
    setPhase('prep');
    setNotice('');
    setErrorMessage('');
  }

  async function generate(reportType: ReportType, source: 'new' | number) {
    setBusyId(source);
    setErrorMessage('');
    setNotice('');
    try {
      const result = await api.generateReport({ report_type: reportType });
      setLastGenerated(result);
      if (source === 'new') {
        setPhase('done');
      } else {
        setNotice(`New ${reportTypeLabel(reportType).toLowerCase()} created.`);
      }
      await load({ silent: true });
    } catch (error) {
      setErrorMessage(getErrorMessage(error, 'Could not create the report.'));
    } finally {
      setBusyId(null);
    }
  }

  function noteMissingFile(report: ReportExport) {
    setMissingFileIds((current) => (current.includes(report.id) ? current : [...current, report.id]));
  }

  async function open(report: ReportExport) {
    setErrorMessage('');
    setNotice('');
    if (await openReportFile(report.file_path)) return;
    setErrorMessage(`Could not open the PDF. It is saved on this computer at: ${report.file_path}`);
  }

  async function reveal(report: ReportExport) {
    setErrorMessage('');
    setNotice('');
    if (await revealReportFile(report.file_path)) return;
    setErrorMessage(`Saved on this computer at: ${report.file_path}`);
  }

  async function saveCopy(report: ReportExport) {
    setErrorMessage('');
    setNotice('');
    const suggested = suggestedFileName(report.report_type, report.generated_at);
    try {
      const result = await saveReportCopy(suggested, () => api.downloadReport(report.id));
      if (result === 'saved') setNotice('Saved a copy.');
      if (result === 'unavailable') {
        downloadInBrowser(await api.downloadReport(report.id), suggested);
        setNotice(`Saved to your downloads as ${suggested}.`);
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        noteMissingFile(report);
        return;
      }
      setErrorMessage(getErrorMessage(error, 'Could not save a copy of the PDF.'));
    }
  }

  async function download(report: ReportExport) {
    setErrorMessage('');
    setNotice('');
    const filename = suggestedFileName(report.report_type, report.generated_at);
    try {
      downloadInBrowser(await api.downloadReport(report.id), filename);
      setNotice(`Saved to your downloads as ${filename}.`);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        noteMissingFile(report);
        return;
      }
      setErrorMessage(getErrorMessage(error, 'Could not download the PDF.'));
    }
  }

  function print(report: ReportExport) {
    const outline = outlineFor(report);
    if (!outline) {
      setErrorMessage('This report was made before in-app printing. Open the PDF and print from there.');
      return;
    }
    setErrorMessage('');
    setNotice('');
    setPrintTarget(outline);
  }

  function reportActions(report: ReportExport, variant: 'primary' | 'row') {
    if (missingFileIds.includes(report.id)) {
      return (
        <div className="report-missing" role="status">
          <span>This file is no longer on your computer.</span>
          <button
            className="secondary-button"
            type="button"
            disabled={busyId !== null}
            onClick={() => void generate(report.report_type as ReportType, report.id)}
          >
            {busyId === report.id ? 'Making it again…' : 'Make it again'}
          </button>
        </div>
      );
    }

    const openClass = variant === 'primary' ? 'primary-button' : 'secondary-button';
    return (
      <div className="button-row">
        {desktop ? (
          <>
            <button className={openClass} type="button" onClick={() => void open(report)}>
              Open PDF
            </button>
            <button className="secondary-button" type="button" onClick={() => void saveCopy(report)}>
              Save a copy…
            </button>
          </>
        ) : (
          <button className={openClass} type="button" onClick={() => void download(report)}>
            Download PDF
          </button>
        )}
        <button className="ghost-button" type="button" onClick={() => print(report)}>
          Print
        </button>
        {desktop && (
          <button className="ghost-button" type="button" onClick={() => void reveal(report)}>
            {revealLabel()}
          </button>
        )}
      </div>
    );
  }

  const missingDetails = useMemo(() => missingProfileDetails(summary), [summary]);
  const intentLabel = intent ? reportTypeLabel(intent) : '';
  const generatedOutline = lastGenerated ? outlineFor(lastGenerated) : null;

  if (loading) return <div className="loading-block" role="status">Loading reports…</div>;
  if (errorMessage && reports.length === 0 && phase === 'choose') {
    return <PageErrorState title="Reports unavailable" message={errorMessage} onRetry={() => void load()} />;
  }

  const content = (
    <>
      {notice && <div className="callout" role="status">{notice}</div>}
      {errorMessage && <div className="callout callout-caution" role="alert">{errorMessage}</div>}

      {phase === 'choose' && (
        <Card title="What are you preparing for?" description="Pick one to start — you can read the whole report before it is created.">
          <div className="intent-grid">
            {INTENTS.map((option) => (
              <button key={option.key} type="button" className="intent-card" onClick={() => startIntent(option.key)}>
                <strong className="intent-card-title">{option.title}</strong>
                <span className="intent-card-detail">{option.detail}</span>
                <span className="intent-card-cue" aria-hidden="true">
                  Choose
                </span>
              </button>
            ))}
          </div>
        </Card>
      )}

      {phase === 'prep' && intent && (
        <Card
          title={`What will be in this report: ${intentLabel}`}
          description="Everything below goes into the PDF. Nothing leaves this computer."
        >
          <div className="stack">
            {intent === 'appointment_prep' && (
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="appt-date">Appointment date (optional)</label>
                  <input
                    id="appt-date"
                    type="date"
                    value={appointment.date}
                    onChange={(e) => setAppointment((current) => ({ ...current, date: e.target.value }))}
                  />
                  <div className="field-hint">Kept on this computer as a reminder. It is not printed on the sheet.</div>
                </div>
                <div className="field">
                  <label htmlFor="appt-doctor">Doctor or clinic (optional)</label>
                  <input
                    id="appt-doctor"
                    value={appointment.doctor}
                    onChange={(e) => setAppointment((current) => ({ ...current, doctor: e.target.value }))}
                    placeholder="e.g. Dr. Rivera"
                  />
                  <div className="field-hint">Kept on this computer as a reminder. It is not printed on the sheet.</div>
                </div>
              </div>
            )}

            {preview ? (
              <ReportContents outline={preview} headingLevel={4} />
            ) : (
              <p className="muted" role="status">
                Working out what to include…
              </p>
            )}

            {missingDetails.length > 0 && (
              <div className="callout" role="status">
                <strong>A heads-up before you generate.</strong> {missingDetails.join(', ')}{' '}
                {missingDetails.length === 1 ? 'is' : 'are'} not filled in yet, which may affect trial matching. You can
                add {missingDetails.length === 1 ? 'it' : 'them'} in <Link to="/profile">Patient Details</Link>, or
                continue without.
              </div>
            )}

            <div className="button-row">
              <button className="ghost-button" type="button" onClick={() => setPhase('choose')}>
                Back
              </button>
              <button
                className="primary-button"
                type="button"
                disabled={busyId !== null}
                onClick={() => void generate(intent, 'new')}
              >
                {busyId === 'new' ? 'Creating…' : `Create ${intentLabel.toLowerCase()}`}
              </button>
            </div>
          </div>
        </Card>
      )}

      {phase === 'done' && lastGenerated && (
        <Card
          title="Your report is ready"
          description="Saved on this computer. Open it, print it, or save a copy wherever you like."
        >
          <div className="stack">
            <div className="report-ready">
              <strong>{reportTypeLabel(lastGenerated.report_type)}</strong>
              <p className="muted">{fileName(lastGenerated.file_path)}</p>
              {intent === 'appointment_prep' && (appointment.date || appointment.doctor) && (
                <p className="muted">
                  For your appointment
                  {appointment.doctor ? ` with ${appointment.doctor}` : ''}
                  {appointment.date ? ` on ${new Date(appointment.date).toLocaleDateString()}` : ''}.
                </p>
              )}
            </div>
            {reportActions(lastGenerated, 'primary')}
            {generatedOutline && <ReportContents outline={generatedOutline} headingLevel={4} />}
            <div className="button-row">
              <button
                className="ghost-button"
                type="button"
                onClick={() => {
                  setPhase('choose');
                  setIntent(null);
                  setLastGenerated(null);
                }}
              >
                Prepare another
              </button>
            </div>
          </div>
        </Card>
      )}

      <Card
        title="Report history"
        description="Reports you have made on this computer. Open, print, or save a copy of any of them."
      >
        {reports.length === 0 ? (
          <EmptyState
            title="No reports yet"
            message="Start above to create your first report — it is built from the findings Firstlight has gathered."
          />
        ) : (
          <div className="finding-list">
            {reports.map((report) => {
              const outline = outlineFor(report);
              const expanded = expandedId === report.id;
              return (
                <article className="finding-item" key={report.id}>
                  <div className="finding-topline">
                    <div>
                      <div className="report-row-title">
                        <strong>{reportTypeLabel(report.report_type)}</strong>
                        {lastGenerated?.id === report.id && <Badge label="Just created" tone="success" />}
                      </div>
                      <div className="muted" title={new Date(report.generated_at).toLocaleString()}>
                        {relativeTime(report.generated_at)}
                        {outline ? ` · ${outlineSummaryLine(outline)}` : ''}
                      </div>
                    </div>
                  </div>
                  <div className="finding-footer">
                    <div className="finding-actions">
                      {reportActions(report, 'row')}
                      {outline && (
                        <button
                          type="button"
                          className="ghost-button"
                          aria-expanded={expanded}
                          onClick={() => setExpandedId(expanded ? null : report.id)}
                        >
                          {expanded ? 'Hide contents' : "What's inside"}
                        </button>
                      )}
                      <button
                        type="button"
                        className="ghost-button"
                        disabled={busyId !== null}
                        onClick={() => void generate(report.report_type as ReportType, report.id)}
                      >
                        {busyId === report.id ? 'Creating…' : 'Make a new one'}
                      </button>
                    </div>
                  </div>
                  {expanded && outline && <ReportContents outline={outline} headingLevel={4} />}
                </article>
              );
            })}
          </div>
        )}
      </Card>

      {printTarget && (
        <div className="report-print-sheet">
          <h1>Firstlight — {printTarget.report_title}</h1>
          <p className="muted">Generated on this computer · {new Date().toLocaleString()}</p>
          <ReportContents outline={printTarget} />
        </div>
      )}
    </>
  );

  if (embedded) {
    return content;
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <div className="eyebrow">Generated on this computer</div>
          <h1>Reports</h1>
          <p className="page-lede">
            Start with what you are preparing for. Firstlight builds a PDF you can read here, print, or hand to your
            oncology team — all on this computer.
          </p>
        </div>
      </div>
      {content}
    </div>
  );
}
