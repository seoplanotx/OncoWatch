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
};

export type HealthResponse = {
  checked_at: string;
  overall_ok: boolean;
  items: HealthItem[];
};

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
  location_summary?: string | null;
  matching_gaps: string[];
  match_debug: Record<string, unknown>;
  llm_provider?: string | null;
  llm_model?: string | null;
  llm_metadata: Record<string, unknown>;
  evidence_items: FindingEvidence[];
  created_at: string;
  updated_at: string;
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

export type Dashboard = {
  latest_run?: MonitoringRun | null;
  next_scheduled_run?: string | null;
  counts: Record<string, number>;
  recent_findings: Finding[];
  disclaimer: string;
};

export type ReportExport = {
  id: number;
  profile_id?: number | null;
  report_type: string;
  status: string;
  file_path: string;
  generated_at: string;
  summary_json: Record<string, unknown>;
};

export type BootstrapInfo = {
  app_name: string;
  disclaimer: string;
  onboarding_completed: boolean;
  active_profile_id?: number | null;
  data_dir: string;
  reports_dir: string;
};
