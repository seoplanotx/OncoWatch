import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ClinicianSummaryPage } from './ClinicianSummaryPage';
import { api } from '../lib/api';
import type { ClinicianSummary } from '../lib/types';

vi.mock('../lib/api', () => ({
  api: {
    getClinicianSummary: vi.fn(),
    generateReport: vi.fn(),
    downloadReport: vi.fn()
  }
}));

vi.mock('../lib/reportFile', () => ({
  isDesktopShell: () => true,
  openReportFile: vi.fn().mockResolvedValue(true),
  saveReportCopy: vi.fn().mockResolvedValue('saved'),
  downloadInBrowser: vi.fn(),
  suggestedFileName: () => 'firstlight-appointment-prep-2026-06-21.pdf'
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <ClinicianSummaryPage />
    </MemoryRouter>
  );
}

const mockedApi = vi.mocked(api);

const summary: ClinicianSummary = {
  generated_at: '2026-06-21T12:00:00Z',
  case_header: {
    cancer_type: 'Non-small cell lung cancer',
    subtype: 'Adenocarcinoma',
    stage_or_context: 'Metastatic',
    current_therapy_status: 'Discussing next line therapy',
    location_label: 'Dallas, Texas',
    travel_radius_miles: 100,
    biomarkers: [{ name: 'EGFR', variant: 'Exon 19 deletion', status: 'positive' }],
    lines_of_therapy: [
      { therapy_name: 'Osimertinib', therapy_type: 'targeted', line_of_therapy: '1L', status: 'active' }
    ],
    would_consider: ['clinical trials'],
    would_not_consider: ['chemotherapy']
  },
  case_framing: {
    text: 'Metastatic NSCLC case: 1 trial and 1 research item flagged for clinician review.',
    generation: { mode: 'local_only', status: 'deterministic_fallback', provider: null, model: null }
  },
  trial_findings: [
    {
      id: 1,
      type: 'clinical_trials',
      title: 'New recruiting EGFR trial',
      source_name: 'ClinicalTrials.gov',
      source_url: 'https://clinicaltrials.gov/study/NCT1',
      identifier: 'NCT1',
      relevance_label: 'High relevance',
      score: 91,
      status: 'new',
      recruitment_bucket: 'open',
      freshness_bucket: 'very_recent',
      why_it_surfaced: 'Matches EGFR biomarker.',
      why_it_may_not_fit: null,
      matching_gaps: ['Performance status was not available.'],
      user_action: 'none'
    }
  ],
  research_findings: [
    {
      id: 2,
      type: 'literature',
      title: 'EGFR literature update',
      source_name: 'PubMed',
      source_url: null,
      identifier: 'LIT-1',
      relevance_label: 'Worth reviewing',
      score: 73,
      status: 'changed',
      recruitment_bucket: null,
      freshness_bucket: 'recent',
      why_it_surfaced: 'Recent EGFR review.',
      why_it_may_not_fit: null,
      matching_gaps: [],
      user_action: 'none'
    }
  ],
  discussion_questions: ['Is this trial a fit given my current therapy?'],
  data_gaps: [{ label: 'Performance status', finding_count: 1, examples: ['New recruiting EGFR trial'] }],
  disclaimer: 'Firstlight is not medical advice.'
};

describe('ClinicianSummaryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedApi.getClinicianSummary.mockResolvedValue(summary);
    mockedApi.generateReport.mockResolvedValue({
      id: 10,
      report_type: 'appointment_prep',
      status: 'completed',
      file_path: '/reports/prep.pdf',
      generated_at: '2026-06-21T12:01:00Z',
      summary_json: {}
    });
  });

  it('renders the case snapshot, framing, trials and research', async () => {
    renderPage();
    expect(await screen.findByText('For your doctor')).toBeInTheDocument();
    expect(screen.getByText('Non-small cell lung cancer')).toBeInTheDocument();
    expect(screen.getByText(/1 trial and 1 research item/i)).toBeInTheDocument();
    expect(screen.getByText('New recruiting EGFR trial')).toBeInTheDocument();
    expect(screen.getByText('EGFR literature update')).toBeInTheDocument();
    expect(screen.getByText('Is this trial a fit given my current therapy?')).toBeInTheDocument();
  });

  it('generates an appointment prep sheet and offers to open it right away', async () => {
    renderPage();
    await screen.findByText('For your doctor');

    await userEvent.click(screen.getByRole('button', { name: /make appointment prep sheet/i }));

    await waitFor(() =>
      expect(mockedApi.generateReport).toHaveBeenCalledWith({ report_type: 'appointment_prep' })
    );
    expect(await screen.findByText(/created on this computer/i)).toBeInTheDocument();
    // The old flow dead-ended here with prose; the sheet must be reachable.
    expect(screen.getByRole('button', { name: /open prep sheet/i })).toBeInTheDocument();
  });
});
