import { render, screen } from '@testing-library/react';
import { Outlet, RouterProvider, createMemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { appRouteChildren } from '../App';
import { Sidebar } from '../components/Sidebar';
import { api } from '../lib/api';
import type { BootstrapInfo, ClinicianSummary, Dashboard } from '../lib/types';

vi.mock('../lib/api', () => ({
  api: {
    // Findings / trials / research / saved views
    getFindings: vi.fn(),
    getSources: vi.fn(),
    setFindingAction: vi.fn(),
    setFindingActionsBulk: vi.fn(),
    // Doctor visit views
    getClinicianSummary: vi.fn(),
    getReports: vi.fn(),
    generateReport: vi.fn(),
    downloadReport: vi.fn(),
    // Sidebar profile switcher
    getProfiles: vi.fn(),
    getActiveProfile: vi.fn(),
    activateProfile: vi.fn(),
    // Dashboard (index route)
    getDashboard: vi.fn()
  }
}));

const mockedApi = vi.mocked(api);

const bootstrap = { disclaimer: 'test disclaimer' } as unknown as BootstrapInfo;

const emptySummary: ClinicianSummary = {
  generated_at: '2026-06-01T00:00:00Z',
  case_header: {
    cancer_type: 'breast cancer',
    biomarkers: [],
    lines_of_therapy: [],
    would_consider: [],
    would_not_consider: []
  },
  case_framing: { text: 'A short framing.', generation: { mode: 'local_only', status: 'deterministic_fallback' } },
  trial_findings: [],
  research_findings: [],
  discussion_questions: [],
  data_gaps: [],
  disclaimer: 'Review with your care team.'
};

function renderAppAt(path: string) {
  const router = createMemoryRouter(
    [{ element: <Outlet />, children: appRouteChildren(bootstrap) }],
    { initialEntries: [path] }
  );
  return render(<RouterProvider router={router} />);
}

function renderSidebarAt(path: string) {
  const router = createMemoryRouter(
    [{ path: '*', element: <Sidebar /> }],
    { initialEntries: [path] }
  );
  return render(<RouterProvider router={router} />);
}

describe('task-based navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    mockedApi.getFindings.mockResolvedValue({ total: 0, items: [] });
    mockedApi.getSources.mockResolvedValue([]);
    mockedApi.getClinicianSummary.mockResolvedValue(emptySummary);
    mockedApi.getReports.mockResolvedValue({ items: [], other_profiles_count: 0 });
    mockedApi.getProfiles.mockResolvedValue([]);
    mockedApi.getActiveProfile.mockResolvedValue(null);
    mockedApi.getDashboard.mockResolvedValue({
      counts: {},
      recent_findings: [],
      briefing: {
        new_count: 0,
        changed_count: 0,
        sections: [],
        blockers: [],
        source_statuses: [],
        source_failures: [],
        suggested_questions: [],
        question_generation: {}
      },
      disclaimer: 'x'
    } as unknown as Dashboard);
  });

  it('keeps the legacy /trials URL working and shows the Trials tab active under Discoveries', async () => {
    renderAppAt('/trials');
    expect(await screen.findByRole('heading', { name: 'Discoveries' })).toBeInTheDocument();
    const trialsTab = screen.getByRole('link', { name: 'Trials' });
    expect(trialsTab).toHaveAttribute('aria-current', 'page');
  });

  it('keeps the legacy /updates URL working and shows the Research tab active', async () => {
    renderAppAt('/updates');
    expect(await screen.findByRole('heading', { name: 'Discoveries' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Research' })).toHaveAttribute('aria-current', 'page');
  });

  it('renders the new /discoveries route with the findings review experience', async () => {
    renderAppAt('/discoveries');
    expect(await screen.findByRole('heading', { name: 'Discoveries' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: "What's new" })).toHaveAttribute('aria-current', 'page');
  });

  it('renders the Saved for Discussion view under Doctor Visit at /saved-findings', async () => {
    renderAppAt('/saved-findings');
    expect(await screen.findByRole('heading', { name: 'Doctor Visit' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Saved for discussion' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: 'For your doctor' })).toBeInTheDocument();
  });

  it('keeps the legacy /clinician URL working under Doctor Visit', async () => {
    renderAppAt('/clinician');
    expect(await screen.findByRole('heading', { name: 'Doctor Visit' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'For your doctor' })).toHaveAttribute('aria-current', 'page');
  });

  it('keeps the legacy /reports URL working and shows the Reports tab active', async () => {
    renderAppAt('/reports');
    expect(await screen.findByRole('heading', { name: 'Doctor Visit' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Reports' })).toHaveAttribute('aria-current', 'page');
  });

  it('highlights the Discoveries sidebar item on a legacy sub-route', async () => {
    renderSidebarAt('/trials');
    const discoveries = await screen.findByRole('link', { name: 'Discoveries' });
    expect(discoveries.className).toContain('active');
    expect(screen.getByRole('link', { name: 'Doctor Visit' }).className).not.toContain('active');
  });

  it('highlights the Doctor Visit sidebar item on the reports route', async () => {
    renderSidebarAt('/reports');
    const doctorVisit = await screen.findByRole('link', { name: 'Doctor Visit' });
    expect(doctorVisit.className).toContain('active');
  });
});
