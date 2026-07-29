import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ReportsPage } from './ReportsPage';
import { api, ApiError } from '../lib/api';
import {
  downloadInBrowser,
  isDesktopShell,
  openReportFile,
  revealReportFile,
  saveReportCopy
} from '../lib/reportFile';
import type { ClinicianSummary, ReportExport, ReportOutline } from '../lib/types';

vi.mock('../lib/api', async () => {
  const actual = await vi.importActual<typeof import('../lib/api')>('../lib/api');
  return {
    ApiError: actual.ApiError,
    api: {
      getReports: vi.fn(),
      getReportPreview: vi.fn(),
      generateReport: vi.fn(),
      downloadReport: vi.fn(),
      getClinicianSummary: vi.fn()
    }
  };
});

vi.mock('../lib/reportFile', () => ({
  isDesktopShell: vi.fn(),
  revealLabel: () => 'Show in Finder',
  openReportFile: vi.fn(),
  revealReportFile: vi.fn(),
  saveReportCopy: vi.fn(),
  downloadInBrowser: vi.fn(),
  suggestedFileName: (type: string) => `firstlight-${type.replace(/_/g, '-')}-2026-06-21.pdf`
}));

const mockedApi = vi.mocked(api);
const mockedDesktop = vi.mocked(isDesktopShell);

function buildOutline(overrides: Partial<ReportOutline> = {}): ReportOutline {
  return {
    report_type: 'appointment_prep',
    report_title: 'Appointment Prep Sheet',
    sections: [
      {
        key: 'top_things_to_raise',
        title: 'Top things to raise',
        description: 'The highest-priority items from your latest check.',
        empty_message: 'No monitored findings are stored for this profile yet.',
        count: 1,
        items: [
          {
            id: 5,
            title: 'New recruiting EGFR trial',
            source_name: 'ClinicalTrials.gov',
            source_url: 'https://example.org/NCT-1',
            identifier: 'NCT-1',
            relevance_label: 'High relevance',
            status: 'new',
            status_line: 'New • High relevance • NCT-1',
            why_it_surfaced: 'Matches your EGFR biomarker'
          }
        ]
      }
    ],
    questions: ['What are my trial options?', 'Any new targeted therapies?'],
    gaps: [{ label: 'Performance status', finding_count: 1, examples: ['New recruiting EGFR trial'] }],
    counts: { findings: 1, new: 1, changed: 0, appendix: 0 },
    ...overrides
  };
}

function buildReport(overrides: Partial<ReportExport> = {}): ReportExport {
  return {
    id: 1,
    report_type: 'appointment_prep',
    status: 'completed',
    file_path: '/reports/20260621-120000-appointment_prep-sample.pdf',
    generated_at: '2026-06-21T12:00:00Z',
    summary_json: { outline: buildOutline() },
    ...overrides
  };
}

const summary: ClinicianSummary = {
  generated_at: '2026-06-01T00:00:00Z',
  case_header: {
    cancer_type: 'breast cancer',
    stage_or_context: 'Stage 4',
    biomarkers: [{ name: 'HER2' }],
    lines_of_therapy: [], // Treatment line missing -> should surface as a heads-up
    would_consider: [],
    would_not_consider: []
  },
  case_framing: { text: 'framing', generation: { mode: 'local_only', status: 'deterministic_fallback' } },
  trial_findings: [],
  research_findings: [],
  discussion_questions: ['What are my trial options?', 'Any new targeted therapies?'],
  data_gaps: [],
  disclaimer: 'Review with your care team.'
};

function renderPage() {
  return render(
    <MemoryRouter>
      <ReportsPage />
    </MemoryRouter>
  );
}

describe('ReportsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    mockedDesktop.mockReturnValue(true);
    mockedApi.getReports.mockResolvedValue([buildReport()]);
    mockedApi.getReportPreview.mockResolvedValue(buildOutline());
    mockedApi.generateReport.mockResolvedValue(buildReport());
    mockedApi.downloadReport.mockResolvedValue(new Blob(['%PDF']));
    mockedApi.getClinicianSummary.mockResolvedValue(summary);
    vi.mocked(openReportFile).mockResolvedValue(true);
    vi.mocked(revealReportFile).mockResolvedValue(true);
    vi.mocked(saveReportCopy).mockResolvedValue('saved');
  });

  it('labels the appointment prep report type in history', async () => {
    renderPage();
    expect((await screen.findAllByText('Appointment prep sheet')).length).toBeGreaterThan(0);
  });

  it('shows what will be in the report before creating it', async () => {
    renderPage();
    await screen.findByText('What are you preparing for?');

    await userEvent.click(screen.getByRole('button', { name: /an upcoming appointment/i }));

    await waitFor(() => expect(mockedApi.getReportPreview).toHaveBeenCalledWith('appointment_prep'));
    // The preview is the report's real contents, not a hand-rolled summary.
    expect(await screen.findByText('New recruiting EGFR trial')).toBeInTheDocument();
    expect(screen.getByText('What are my trial options?')).toBeInTheDocument();
    expect(screen.getByText(/Treatment line/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /create appointment prep sheet/i }));

    await waitFor(() =>
      expect(mockedApi.generateReport).toHaveBeenCalledWith({ report_type: 'appointment_prep' })
    );
    expect(await screen.findByText(/your report is ready/i)).toBeInTheDocument();
  });

  it('maps the "quick update" intent to a daily summary report', async () => {
    mockedApi.generateReport.mockResolvedValue(buildReport({ report_type: 'daily_summary' }));
    renderPage();
    await screen.findByText('What are you preparing for?');

    await userEvent.click(screen.getByRole('button', { name: /a quick update to share/i }));
    await userEvent.click(await screen.findByRole('button', { name: /create daily summary report/i }));

    await waitFor(() =>
      expect(mockedApi.generateReport).toHaveBeenCalledWith({ report_type: 'daily_summary' })
    );
  });

  it('opens the PDF itself in the desktop shell', async () => {
    renderPage();
    await screen.findAllByText('Appointment prep sheet');

    await userEvent.click(screen.getByRole('button', { name: /open pdf/i }));

    await waitFor(() =>
      expect(openReportFile).toHaveBeenCalledWith('/reports/20260621-120000-appointment_prep-sample.pdf')
    );
    expect(downloadInBrowser).not.toHaveBeenCalled();
  });

  it('reveals the file and saves a copy from the desktop shell', async () => {
    renderPage();
    await screen.findAllByText('Appointment prep sheet');

    await userEvent.click(screen.getByRole('button', { name: /show in finder/i }));
    await waitFor(() =>
      expect(revealReportFile).toHaveBeenCalledWith('/reports/20260621-120000-appointment_prep-sample.pdf')
    );

    await userEvent.click(screen.getByRole('button', { name: /save a copy/i }));
    await waitFor(() => expect(saveReportCopy).toHaveBeenCalled());
    expect(await screen.findByText('Saved a copy.')).toBeInTheDocument();
  });

  it('falls back to a browser download outside the desktop shell', async () => {
    mockedDesktop.mockReturnValue(false);
    renderPage();
    await screen.findAllByText('Appointment prep sheet');

    expect(screen.queryByRole('button', { name: /open pdf/i })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /download pdf/i }));

    await waitFor(() => expect(downloadInBrowser).toHaveBeenCalled());
    expect(vi.mocked(downloadInBrowser).mock.calls[0][1]).toBe('firstlight-appointment-prep-2026-06-21.pdf');
  });

  it('expands a history row to show what is inside the report', async () => {
    renderPage();
    await screen.findAllByText('Appointment prep sheet');
    expect(screen.queryByText('New recruiting EGFR trial')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /what's inside/i }));

    expect(await screen.findByText('New recruiting EGFR trial')).toBeInTheDocument();
    expect(screen.getByText('Performance status')).toBeInTheDocument();
  });

  it('summarizes each history row instead of showing only a timestamp', async () => {
    renderPage();
    await screen.findAllByText('Appointment prep sheet');
    expect(screen.getByText(/1 item · 2 questions · 1 to confirm/)).toBeInTheDocument();
  });

  it('offers to remake a report whose file has been deleted', async () => {
    vi.mocked(saveReportCopy).mockRejectedValue(new ApiError('Report file is missing from disk', 404));
    renderPage();
    await screen.findAllByText('Appointment prep sheet');

    await userEvent.click(screen.getByRole('button', { name: /save a copy/i }));

    expect(await screen.findByText(/no longer on your computer/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /make it again/i }));
    await waitFor(() =>
      expect(mockedApi.generateReport).toHaveBeenCalledWith({ report_type: 'appointment_prep' })
    );
  });

  it('only marks the acted-on history row as busy', async () => {
    mockedApi.getReports.mockResolvedValue([
      buildReport(),
      buildReport({ id: 2, report_type: 'daily_summary', generated_at: '2026-06-20T12:00:00Z' })
    ]);
    let resolveGenerate: (value: ReportExport) => void = () => {};
    mockedApi.generateReport.mockReturnValue(
      new Promise<ReportExport>((resolve) => {
        resolveGenerate = resolve;
      })
    );
    renderPage();
    await screen.findAllByText('Appointment prep sheet');

    const remakeButtons = screen.getAllByRole('button', { name: /make a new one/i });
    await userEvent.click(remakeButtons[0]);

    // The row that was clicked reports progress; the other one does not.
    expect(await screen.findByRole('button', { name: /creating…/i })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /creating…/i })).toHaveLength(1);

    resolveGenerate(buildReport());
    await waitFor(() => expect(mockedApi.getReports).toHaveBeenCalledTimes(2));
  });

  it('prints a report from its stored contents', async () => {
    const print = vi.fn();
    vi.stubGlobal('print', print);
    renderPage();
    await screen.findAllByText('Appointment prep sheet');

    await userEvent.click(screen.getByRole('button', { name: /^print$/i }));

    await waitFor(() => expect(print).toHaveBeenCalled());
    vi.unstubAllGlobals();
  });
});
