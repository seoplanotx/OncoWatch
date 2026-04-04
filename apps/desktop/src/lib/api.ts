import type {
  AppSettings,
  BootstrapInfo,
  Dashboard,
  Finding,
  HealthResponse,
  MonitoringRun,
  OnboardingState,
  PatientProfile,
  ProviderConfig,
  ReportExport,
  SourceConfig
} from './types';

export const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:17845';

export class ApiError extends Error {
  status: number;
  body?: unknown;

  constructor(message: string, status: number, body?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

function errorMessageFromBody(body: unknown, fallback: string): string {
  if (typeof body === 'string' && body.trim()) {
    return body;
  }
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
    if (detail && typeof detail === 'object' && 'message' in detail) {
      const message = (detail as { message?: unknown }).message;
      if (typeof message === 'string' && message.trim()) {
        return message;
      }
    }
  }
  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}/api${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {})
    },
    ...init
  });

  if (!response.ok) {
    const fallback = `Request failed: ${response.status}`;
    const contentType = response.headers.get('content-type') || '';

    if (contentType.includes('application/json')) {
      const body = await response.json();
      throw new ApiError(errorMessageFromBody(body, fallback), response.status, body);
    }

    const text = await response.text();
    throw new ApiError(errorMessageFromBody(text, fallback), response.status, text);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  getBootstrap: () => request<BootstrapInfo>('/bootstrap'),
  getOnboardingState: () => request<OnboardingState>('/onboarding/state'),
  completeOnboarding: (payload: Record<string, unknown>) =>
    request<OnboardingState>('/onboarding/complete', { method: 'POST', body: JSON.stringify(payload) }),
  createDemoProfile: () => request<{ profile_id: number }>('/onboarding/demo-profile', { method: 'POST' }),

  getProfiles: () => request<PatientProfile[]>('/profiles'),
  getActiveProfile: () => request<PatientProfile | null>('/profiles/active'),
  createProfile: (payload: PatientProfile) => request<PatientProfile>('/profiles', { method: 'POST', body: JSON.stringify(payload) }),
  updateProfile: (id: number, payload: PatientProfile) =>
    request<PatientProfile>(`/profiles/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),

  getSettings: () => request<AppSettings>('/settings'),
  updateSettings: (payload: Partial<AppSettings>) =>
    request<AppSettings>('/settings', { method: 'PUT', body: JSON.stringify(payload) }),
  getProviderConfig: () => request<ProviderConfig | null>('/settings/provider/openrouter'),
  saveProviderConfig: (payload: Record<string, unknown>) =>
    request<ProviderConfig>('/settings/provider/openrouter/save', { method: 'POST', body: JSON.stringify(payload) }),
  testOpenRouterKey: (payload: Record<string, unknown>) =>
    request<{ ok: boolean; message: string; discovered_models: string[] }>('/settings/provider/openrouter/test', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  getOpenRouterModels: () => request<string[]>('/settings/provider/openrouter/models'),

  getSources: () => request<SourceConfig[]>('/sources'),
  updateSource: (id: number, payload: Partial<SourceConfig>) =>
    request<SourceConfig>(`/sources/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),

  getHealth: () => request<HealthResponse>('/health'),
  getDashboard: () => request<Dashboard>('/dashboard'),
  triggerRun: (payload?: Record<string, unknown>) =>
    request<MonitoringRun>('/runs/trigger', { method: 'POST', body: JSON.stringify(payload || {}) }),
  getRuns: () => request<MonitoringRun[]>('/runs'),

  getFindings: (params?: { finding_type?: string; q?: string; profile_id?: number }) => {
    const query = new URLSearchParams();
    if (params?.finding_type) query.set('finding_type', params.finding_type);
    if (params?.q) query.set('q', params.q);
    if (typeof params?.profile_id === 'number') query.set('profile_id', String(params.profile_id));
    return request<{ total: number; items: Finding[] }>(`/findings${query.toString() ? `?${query.toString()}` : ''}`);
  },

  getReports: () => request<ReportExport[]>('/reports'),
  generateReport: (payload: Record<string, unknown>) =>
    request<ReportExport>('/reports/generate', { method: 'POST', body: JSON.stringify(payload) }),
  downloadReport: async (reportId: number) => {
    const response = await fetch(`${API_BASE}/api/reports/${reportId}/download`);
    if (!response.ok) throw new Error('Could not download report');
    return response.blob();
  }
};
