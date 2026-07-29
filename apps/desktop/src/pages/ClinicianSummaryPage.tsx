import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { Badge } from '../components/Badge';
import { BriefingBlockers } from '../components/BriefingBlockers';
import { Card } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { PageErrorState } from '../components/PageErrorState';
import { api } from '../lib/api';
import { getErrorMessage } from '../lib/errors';
import {
  formatFindingTypeLabel,
  formatFreshnessBucket,
  formatRecruitmentBucket,
  formatRelevanceLabel,
  formatStatusLabel,
  relevanceTone,
  statusTone,
  typeTone
} from '../lib/findingPresentation';
import { useLanguageMode } from '../lib/languageMode';
import { appointmentPayload, readAppointment } from '../lib/appointmentPrefs';
import {
  downloadInBrowser,
  isDesktopShell,
  openReportFile,
  saveReportCopy,
  suggestedFileName
} from '../lib/reportFile';
import type { CaseHeader, ClinicianSummary, CondensedFinding, ReportExport } from '../lib/types';

function caseHeaderRows(header: CaseHeader): { label: string; value: string }[] {
  const rows: { label: string; value: string }[] = [
    { label: 'Cancer type', value: header.cancer_type || 'Not recorded' }
  ];
  if (header.subtype) rows.push({ label: 'Subtype', value: header.subtype });
  if (header.stage_or_context) rows.push({ label: 'Stage / context', value: header.stage_or_context });
  if (header.current_therapy_status) {
    rows.push({ label: 'Current therapy', value: header.current_therapy_status });
  }
  if (header.location_label) rows.push({ label: 'Location', value: header.location_label });
  if (typeof header.travel_radius_miles === 'number') {
    rows.push({ label: 'Travel radius', value: `${header.travel_radius_miles} miles` });
  }
  return rows;
}

function CondensedFindingItem({ finding }: { finding: CondensedFinding }) {
  const mode = useLanguageMode();
  const metaLine = [finding.source_name, finding.identifier].filter(Boolean).join('  ·  ');
  const buckets = [
    finding.recruitment_bucket ? `Recruitment: ${formatRecruitmentBucket(finding.recruitment_bucket)}` : null,
    finding.freshness_bucket ? `Evidence: ${formatFreshnessBucket(finding.freshness_bucket)}` : null
  ].filter(Boolean);

  return (
    <article className="finding-item">
      <div className="finding-topline">
        <div className="finding-heading">
          <h3 className="finding-title">{finding.title}</h3>
          {metaLine && <p className="finding-meta-line">{metaLine}</p>}
        </div>
        <div className="badge-row">
          <Badge label={formatFindingTypeLabel(finding.type)} tone={typeTone(finding.type)} />
          <Badge label={formatStatusLabel(finding.status, mode)} tone={statusTone(finding.status)} />
          <Badge
            label={formatRelevanceLabel(finding.relevance_label, mode)}
            tone={relevanceTone(finding.relevance_label)}
          />
          {finding.user_action === 'discuss' && <Badge label="To discuss" tone="success" />}
        </div>
      </div>

      {buckets.length > 0 && <p className="finding-meta-line">{buckets.join('  ·  ')}</p>}

      <div className="rationale-split">
        <div className="rationale-col">
          <div className="support-card-label">Why it surfaced</div>
          <div className="multiline">{finding.why_it_surfaced || 'No structured rationale stored.'}</div>
        </div>
        <div className="rationale-col rationale-col-caution">
          <div className="support-card-label">Why it may not fit</div>
          <div className="multiline">{finding.why_it_may_not_fit || 'No cautions stored.'}</div>
        </div>
      </div>

      {finding.matching_gaps.length > 0 && (
        <p className="muted">Still to confirm: {finding.matching_gaps.join(', ')}</p>
      )}

      {finding.source_url && (
        <div className="finding-footer">
          <a href={finding.source_url} target="_blank" rel="noreferrer" className="source-link">
            Open source record
          </a>
        </div>
      )}
    </article>
  );
}

export function ClinicianSummaryPage({ embedded = false }: { embedded?: boolean } = {}) {
  const [summary, setSummary] = useState<ClinicianSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [prepSheet, setPrepSheet] = useState<ReportExport | null>(null);

  async function load() {
    setLoading(true);
    setErrorMessage('');
    try {
      const result = await api.getClinicianSummary();
      setSummary(result);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, 'Could not build the clinician summary.'));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function makePrepSheet() {
    setBusy(true);
    setErrorMessage('');
    setNotice('');
    try {
      // Same stored appointment details as the Reports flow, so both entry
      // points produce the same sheet header.
      const report = await api.generateReport({
        report_type: 'appointment_prep',
        ...appointmentPayload(readAppointment())
      });
      setPrepSheet(report);
      setNotice('Appointment prep sheet created on this computer.');
    } catch (error) {
      setErrorMessage(getErrorMessage(error, 'Could not generate the appointment prep sheet.'));
    } finally {
      setBusy(false);
    }
  }

  async function openPrepSheet(report: ReportExport) {
    if (await openReportFile(report.file_path)) return;
    setErrorMessage(`Could not open the PDF. It is saved on this computer at: ${report.file_path}`);
  }

  async function savePrepSheet(report: ReportExport) {
    const suggested = suggestedFileName(report.report_type, report.generated_at);
    try {
      const result = await saveReportCopy(suggested, () => api.downloadReport(report.id));
      if (result === 'saved') setNotice('Saved a copy.');
      if (result === 'unavailable') {
        downloadInBrowser(await api.downloadReport(report.id), suggested);
        setNotice(`Saved to your downloads as ${suggested}.`);
      }
    } catch (error) {
      setErrorMessage(getErrorMessage(error, 'Could not save a copy of the PDF.'));
    }
  }

  if (loading) return <div className="loading-block" role="status">Building clinician summary…</div>;
  if (errorMessage && !summary) {
    return <PageErrorState title="Summary unavailable" message={errorMessage} onRetry={load} />;
  }
  if (!summary) {
    return <PageErrorState title="Summary unavailable" message="No summary was returned." onRetry={load} />;
  }

  const header = summary.case_header;
  const framing = summary.case_framing;
  const trialCount = summary.trial_findings.length;
  const researchCount = summary.research_findings.length;

  const actions = (
    <>
      {prepSheet ? (
        <>
          {isDesktopShell() ? (
            <>
              <button type="button" className="secondary-button" onClick={() => void openPrepSheet(prepSheet)}>
                Open prep sheet
              </button>
              <button type="button" className="ghost-button" onClick={() => void savePrepSheet(prepSheet)}>
                Save a copy…
              </button>
            </>
          ) : (
            <button type="button" className="secondary-button" onClick={() => void savePrepSheet(prepSheet)}>
              Download prep sheet
            </button>
          )}
          <Link className="ghost-button" to="/reports">
            All reports
          </Link>
        </>
      ) : (
        <button type="button" className="secondary-button" disabled={busy} onClick={() => void makePrepSheet()}>
          {busy ? 'Creating…' : 'Make appointment prep sheet'}
        </button>
      )}
      <button type="button" className="ghost-button" onClick={() => window.print()}>
        Print this page
      </button>
    </>
  );

  const content = (
    <>
      <div className="callout summary-frame">
        <p>
          <strong>A starting point to review together.</strong> Firstlight gathered what may be worth raising with
          your care team — they decide what actually matters for you.
        </p>
        <p className="summary-frame-note">{summary.disclaimer}</p>
      </div>

      {notice && <div className="callout" role="status">{notice}</div>}
      {errorMessage && <div className="callout callout-caution" role="alert">{errorMessage}</div>}

      <Card
        title="Case snapshot"
        description="The details you entered, summarized for a clinician's quick read."
      >
        <div className="chart-grid">
          {caseHeaderRows(header).map((row) => (
            <div className="chart-row" key={row.label}>
              <div className="chart-label">{row.label}</div>
              <div className="chart-value">{row.value}</div>
            </div>
          ))}
        </div>

        <hr className="chart-divider" />

        <div className="chart-grid chart-cols-2">
          <div className="chart-row">
            <div className="chart-label">Biomarkers</div>
            <div className="chart-value chart-value-soft">
              {header.biomarkers.length === 0
                ? 'None recorded.'
                : header.biomarkers
                    .map((b) => [b.name, b.variant, b.status].filter(Boolean).join(' '))
                    .join('\n')}
            </div>
          </div>
          <div className="chart-row">
            <div className="chart-label">Lines of therapy</div>
            <div className="chart-value chart-value-soft">
              {header.lines_of_therapy.length === 0
                ? 'None recorded.'
                : header.lines_of_therapy
                    .map((t) =>
                      [t.line_of_therapy, t.therapy_name, t.status ? `(${t.status})` : null]
                        .filter(Boolean)
                        .join(' ')
                    )
                    .join('\n')}
            </div>
          </div>
        </div>

        {(header.would_consider.length > 0 || header.would_not_consider.length > 0) && (
          <>
            <hr className="chart-divider" />
            <div className="chart-grid chart-cols-2">
              <div className="chart-row">
                <div className="chart-label">Would consider</div>
                <div className="chart-value chart-value-soft">
                  {header.would_consider.length === 0 ? 'Not specified.' : header.would_consider.join('\n')}
                </div>
              </div>
              <div className="chart-row chart-row-caution">
                <div className="chart-label">Would not consider</div>
                <div className="chart-value">
                  {header.would_not_consider.length === 0 ? 'Not specified.' : header.would_not_consider.join('\n')}
                </div>
              </div>
            </div>
          </>
        )}
      </Card>

      <Card
        title="Case framing"
        description="A short, plain summary of where this case stands."
        action={
          framing.generation.status === 'ai_generated' ? (
            <Badge label="AI-assisted" tone="info" />
          ) : (
            <Badge label="Generated locally" tone="neutral" />
          )
        }
      >
        <p className="finding-summary">{framing.text}</p>
        {framing.generation.message && <p className="muted">{framing.generation.message}</p>}
      </Card>

      <Card
        title="Trials to review"
        description="Possible trials, ranked by how closely they relate to the case. Recruitment status and unknowns matter before treating any as a fit."
        action={<span className="section-counter">{trialCount} found</span>}
      >
        {trialCount === 0 ? (
          <EmptyState title="No trials flagged" message="Run a check to surface trials that may relate to this case." />
        ) : (
          <div className="finding-list">
            {summary.trial_findings.map((finding) => (
              <CondensedFindingItem key={finding.id} finding={finding} />
            ))}
          </div>
        )}
      </Card>

      <Card
        title="Research to review"
        description="Literature, drug updates, and biomarker items worth raising with the care team."
        action={<span className="section-counter">{researchCount} found</span>}
      >
        {researchCount === 0 ? (
          <EmptyState title="No research flagged" message="Run a check to surface research that may relate to this case." />
        ) : (
          <div className="finding-list">
            {summary.research_findings.map((finding) => (
              <CondensedFindingItem key={finding.id} finding={finding} />
            ))}
          </div>
        )}
      </Card>

      <Card
        title="Questions to ask"
        description="Suggested starting points for the conversation with the care team."
        action={<span className="section-counter">{summary.discussion_questions.length} suggested</span>}
      >
        {summary.discussion_questions.length === 0 ? (
          <EmptyState
            title="No questions yet"
            message="Questions will appear here once there are findings to discuss."
          />
        ) : (
          <div className="headline-list">
            {summary.discussion_questions.map((question) => (
              <article className="headline-item" key={question}>
                <strong>{question}</strong>
              </article>
            ))}
          </div>
        )}
      </Card>

      <BriefingBlockers blockers={summary.data_gaps} />
    </>
  );

  if (embedded) {
    return (
      <>
        <div className="section-toolbar">{actions}</div>
        {content}
      </>
    );
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <div className="eyebrow">For your oncology visit</div>
          <h1>For your doctor</h1>
          <p className="page-lede">A clinician-facing snapshot of the case and what Firstlight flagged for review.</p>
        </div>
        <div className="page-header-actions">{actions}</div>
      </div>
      {content}
    </div>
  );
}
