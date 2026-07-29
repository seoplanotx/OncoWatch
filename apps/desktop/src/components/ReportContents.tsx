import { Badge } from './Badge';
import { EmptyState } from './EmptyState';
import type { ReportOutline } from '../lib/types';

/** Finding titles are long; naming two of them is enough to place the gap. */
function describeExamples(examples: string[]): string {
  const shown = examples.slice(0, 2).map((title) => (title.length > 64 ? `${title.slice(0, 61).trimEnd()}…` : title));
  const remaining = examples.length - shown.length;
  return `seen in: ${shown.join('; ')}${remaining > 0 ? ` and ${remaining} more` : ''}`;
}

/**
 * The contents of a report, on screen.
 *
 * The backend builds this outline with the same caps and ordering the PDF
 * builders use, so what you read here is what the PDF contains — whether the
 * report has been created yet or not.
 */
export function ReportContents({ outline, headingLevel = 3 }: { outline: ReportOutline; headingLevel?: 3 | 4 }) {
  const SectionHeading = headingLevel === 3 ? 'h3' : 'h4';
  const hasAnyItem = outline.sections.some((section) => section.items.length > 0);

  return (
    <div className="report-doc">
      {!hasAnyItem && outline.questions.length === 0 && (
        <EmptyState
          title="Nothing to include yet"
          message="Run a check first — this report is built from the findings Firstlight has gathered."
        />
      )}

      {outline.sections.map((section) => (
        <section className="report-doc-section" key={section.key}>
          <div className="report-doc-section-head">
            <SectionHeading>{section.title}</SectionHeading>
            <span className="section-counter">
              {section.count > section.items.length
                ? `${section.items.length} of ${section.count} included`
                : `${section.items.length} ${section.items.length === 1 ? 'item' : 'items'}`}
            </span>
          </div>
          <p className="muted">{section.description}</p>
          {section.items.length === 0 ? (
            <p className="muted">{section.empty_message}</p>
          ) : (
            <ol className="report-doc-list">
              {section.items.map((item) => (
                <li key={item.id}>
                  <div className="report-doc-item-title">
                    <strong>{item.title}</strong>
                    {item.saved_for_discussion && <Badge label="You saved this" tone="success" />}
                    {item.relevance_label && <Badge label={item.relevance_label} tone="info" />}
                  </div>
                  <div className="muted">{item.status_line || item.source_name}</div>
                  {item.why_it_surfaced && <div className="report-doc-reason">Why it surfaced: {item.why_it_surfaced}</div>}
                </li>
              ))}
            </ol>
          )}
        </section>
      ))}

      {outline.questions.length > 0 && (
        <section className="report-doc-section">
          <div className="report-doc-section-head">
            <SectionHeading>Questions for your oncology team</SectionHeading>
            <span className="section-counter">{outline.questions.length} suggested</span>
          </div>
          <ul className="report-doc-list">
            {outline.questions.map((question) => (
              <li key={question}>{question}</li>
            ))}
          </ul>
        </section>
      )}

      {outline.gaps.length > 0 && (
        <section className="report-doc-section">
          <div className="report-doc-section-head">
            <SectionHeading>Information to bring or confirm</SectionHeading>
            <span className="section-counter">{outline.gaps.length} to confirm</span>
          </div>
          <p className="muted">Details that would help your team judge how well these items fit.</p>
          <ul className="report-doc-list">
            {outline.gaps.map((gap) => (
              <li key={gap.label}>
                <strong>{gap.label}</strong>
                {gap.examples.length > 0 && <span className="muted"> — {describeExamples(gap.examples)}</span>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {(outline.counts.appendix ?? 0) > 0 && (
        <p className="muted">
          The PDF also carries an evidence appendix with {outline.counts.appendix} source records.
        </p>
      )}

      <p className="report-doc-disclaimer">
        Firstlight monitors and summarizes research. It does not determine treatment or trial eligibility — everything
        here is for review with your oncology team.
      </p>
    </div>
  );
}

/** One-line description of a report's contents, for history rows. */
export function outlineSummaryLine(outline: ReportOutline): string {
  const itemCount = outline.sections.reduce((total, section) => total + section.items.length, 0);
  const parts = [`${itemCount} ${itemCount === 1 ? 'item' : 'items'}`];
  if (outline.questions.length > 0) {
    parts.push(`${outline.questions.length} ${outline.questions.length === 1 ? 'question' : 'questions'}`);
  }
  if (outline.gaps.length > 0) {
    parts.push(`${outline.gaps.length} to confirm`);
  }
  return parts.join(' · ');
}
