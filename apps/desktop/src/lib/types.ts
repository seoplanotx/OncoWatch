export type Biomarker = {
  id?: number;
  name: string;
  variant?: string | null;
  status?: string | null;
  notes?: string | null;
};

export type TherapyHistoryEntry = {
  id?: number;
  therapy_name: string;
  therapy_type?: string | null;
  line_of_therapy?: string | null;
  status?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  notes?: string | null;
};

export type PatientProfile = {
  id?: number;
  profile_name: string;
  display_name?: string | null;
  date_of_birth?: string | null;
  cancer_type: string;
  subtype?: string | null;
  stage_or_context?: string | null;
  current_therapy_status?: string | null;
  location_label?: string | null;
  travel_radius_miles?: number | null;
  notes?: string | null;
  would_consider: string[];
  would_not_consider: string[];
  is_active: boolean;
  biomarkers: Biomarker[];
  therapy_history: TherapyHistoryEntry[];
  created_at?: string;
  updated_at?: string;
};

export type OnboardingState = {
  id: number;
  is_completed: boolean;
  completed_at?: string | null;
  current_step?: string | null;
  show_demo_profile_option: boolean;
  welcome_acknowledged: boolean;
  last_health_check: Record<string, unknown>;
};

export type PrivacyMode = 'local_only' | 'deidentified_ai_assist';

export type AIProvider = 'openrouter' | 'anthropic';

export type AppSettings = {
  id?: number;
  default_profile_id?: number | null;
  daily_run_time: string;
  default_report_style: string;
  default_report_length: string;
  enabled_source_categories?: string[];
  timezone_label?: string;
  report_output_dir?: string | null;
  demo_profile_enabled: boolean;
  privacy_mode: PrivacyMode;
  deidentified_ai_disclosure_acknowledged: boolean;
  active_ai_provider?: AIProvider;
  last_health_check_at?: string | null;
};

export type SourceConfig = {
  id: number;
  category: string;
  name: string;
  connector_key: string;
  enabled: boolean;
  settings_json: Record<string, unknown>;
  last_successful_sync_at?: string | null;
  last_error?: string | null;
};

export type ProviderConfig = {
  id?: number;
  provider_key: string;
  display_name: string;
  is_configured: boolean;
  api_base_url?: string | null;
  selected_model?: string | null;
  last_tested_at?: string | null;
  last_test_success?: boolean | null;
};

export type HealthItem = {
  key: string;
  label: string;
  ok: boolean;
  message: string;
  severity: string;
  blocking: boolean;
};

export type HealthResponse = {
  checked_at: string;
  overall_ok: boolean;
  items: HealthItem[];
};

export type FindingAction = 'none' | 'discuss' | 'dismissed';

export type FindingEvidence = {
  id: number;
  label?: string | null;
  snippet?: string | null;
  source_url?: string | null;
  source_identifier?: string | null;
  published_at?: string | null;
};

export type Finding = {
  id: number;
  profile_id: number;
  monitoring_run_id?: number | null;
  type: string;
  title: string;
  source_name: string;
  source_url?: string | null;
  external_identifier: string;
  retrieved_at: string;
  published_at?: string | null;
  structured_tags: string[];
  raw_summary?: string | null;
  normalized_summary?: string | null;
  why_it_surfaced?: string | null;
  why_it_may_not_fit?: string | null;
  confidence: string;
  score: number;
  relevance_label: string;
  status: string;
  user_action: FindingAction;
  location_summary?: string | null;
  matching_gaps: string[];
  match_debug: Record<string, unknown>;
  llm_provider?: string | null;
  llm_model?: string | null;
  llm_metadata: Record<string, unknown>;
  plain_language_summary?: string | null;
  plain_language_generated_at?: string | null;
  evidence_items: FindingEvidence[];
  primary_evidence_label?: string | null;
  primary_evidence_snippet?: string | null;
  trial_recruitment_status?: string | null;
  trial_phases: string[];
  trial_sponsor?: string | null;
  trial_intervention_summary?: string | null;
  created_at: string;
  updated_at: string;
};

export type PlainLanguageResponse = {
  finding: Finding;
  status: string;
  message?: string | null;
};

export type MonitoringRun = {
  id: number;
  profile_id?: number | null;
  status: string;
  triggered_by: string;
  started_at: string;
  completed_at?: string | null;
  summary_json: Record<string, unknown>;
  new_findings_count: number;
  changed_findings_count: number;
  sources_checked: string[];
  error_text?: string | null;
};

export type BriefingFindingSection = {
  key: string;
  title: string;
  description: string;
  empty_message: string;
  count: number;
  items: Finding[];
};

export type BriefingBlocker = {
  label: string;
  finding_count: number;
  examples: string[];
};

export type BriefingSourceStatus = {
  connector_key: string;
  status: string;
  retrieved: number;
  message?: string | null;
};

export type BriefingSnapshot = {
  latest_run_started_at?: string | null;
  latest_run_completed_at?: string | null;
  new_count: number;
  changed_count: number;
  sections: BriefingFindingSection[];
  blockers: BriefingBlocker[];
  source_statuses: BriefingSourceStatus[];
  source_failures: BriefingSourceStatus[];
  suggested_questions: string[];
  question_generation: Record<string, unknown>;
};

export type Dashboard = {
  latest_run?: MonitoringRun | null;
  next_scheduled_run?: string | null;
  counts: Record<string, number>;
  recent_findings: Finding[];
  briefing: BriefingSnapshot;
  disclaimer: string;
};

export type ReportOutlineItem = {
  id: number;
  title: string;
  source_name: string;
  source_url?: string | null;
  identifier: string;
  relevance_label: string;
  status: string;
  status_line: string;
  why_it_surfaced?: string | null;
  saved_for_discussion?: boolean;
};

export type ReportOutlineSection = {
  key: string;
  title: string;
  description: string;
  empty_message: string;
  count: number;
  items: ReportOutlineItem[];
};

export type ReportOutlineGap = {
  label: string;
  finding_count: number;
  examples: string[];
};

/** What a report contains — the same shape whether it exists yet or not. */
export type ReportOutline = {
  report_type: string;
  report_title: string;
  sections: ReportOutlineSection[];
  questions: string[];
  gaps: ReportOutlineGap[];
  counts: {
    findings?: number;
    new?: number;
    changed?: number;
    questions?: number;
    gaps?: number;
    appendix?: number;
  };
};

export type ReportSummary = {
  finding_count?: number;
  report_title?: string;
  report_type?: string;
  generated_at?: string | null;
  latest_run_started_at?: string | null;
  latest_run_completed_at?: string | null;
  new_count?: number;
  changed_count?: number;
  sections?: BriefingFindingSection[];
  blockers?: BriefingBlocker[];
  /** Absent on reports generated before the in-app report view shipped. */
  outline?: ReportOutline;
};

export type ReportExport = {
  id: number;
  profile_id?: number | null;
  report_type: string;
  status: string;
  file_path: string;
  generated_at: string;
  summary_json: ReportSummary;
  /** Whether the PDF is still on disk — computed by the backend per request. */
  file_exists?: boolean;
};

export type ReportList = {
  items: ReportExport[];
  /** Reports belonging to non-active profiles, hidden from this view. */
  other_profiles_count: number;
};

export type ReportType = 'daily_summary' | 'full_review' | 'appointment_prep';

export type CaseBiomarker = {
  name: string;
  variant?: string | null;
  status?: string | null;
};

export type CaseTherapyLine = {
  therapy_name: string;
  therapy_type?: string | null;
  line_of_therapy?: string | null;
  status?: string | null;
  start_date?: string | null;
  end_date?: string | null;
};

export type CaseHeader = {
  cancer_type: string;
  subtype?: string | null;
  stage_or_context?: string | null;
  current_therapy_status?: string | null;
  location_label?: string | null;
  travel_radius_miles?: number | null;
  biomarkers: CaseBiomarker[];
  lines_of_therapy: CaseTherapyLine[];
  would_consider: string[];
  would_not_consider: string[];
};

export type CaseFramingGeneration = {
  mode: string;
  status: string;
  provider?: string | null;
  model?: string | null;
  message?: string | null;
};

export type CaseFraming = {
  text: string;
  generation: CaseFramingGeneration;
};

export type CondensedFinding = {
  id: number;
  type: string;
  title: string;
  source_name: string;
  source_url?: string | null;
  identifier: string;
  relevance_label: string;
  score: number;
  status: string;
  recruitment_bucket?: string | null;
  freshness_bucket?: string | null;
  why_it_surfaced?: string | null;
  why_it_may_not_fit?: string | null;
  matching_gaps: string[];
  user_action: string;
};

export type ClinicianSummary = {
  generated_at: string;
  case_header: CaseHeader;
  case_framing: CaseFraming;
  trial_findings: CondensedFinding[];
  research_findings: CondensedFinding[];
  discussion_questions: string[];
  data_gaps: BriefingBlocker[];
  disclaimer: string;
};

export type AuditEvent = {
  timestamp: string;
  action: string;
  detail: Record<string, unknown>;
};

export type DataDeletionSummary = {
  profiles: number;
  findings: number;
  monitoring_runs: number;
  reports: number;
  report_files_removed: number;
};

export type BootstrapInfo = {
  app_name: string;
  app_version: string;
  disclaimer: string;
  onboarding_completed: boolean;
  active_profile_id?: number | null;
  config_dir: string;
  data_dir: string;
  logs_dir: string;
  reports_dir: string;
  monitoring_mode: string;
  privacy_summary: string;
  product_scope: string;
};

export type McpAccessStatus = {
  enabled: boolean;
  has_token: boolean;
};

export type McpEnableResponse = {
  enabled: boolean;
  connection_code: string;
};
