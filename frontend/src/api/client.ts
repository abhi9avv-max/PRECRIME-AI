import {
  Investigation,
  InvestigationSummary,
  Scenario,
  EvidenceRecord,
  RetestResponse,
  MetricsData,
} from '../types';

const API_BASE = '/api';

export async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    let errorDetail = 'API Request failed';
    try {
      const data = await res.json();
      errorDetail = data.detail?.message || data.message || JSON.stringify(data);
    } catch {
      errorDetail = await res.text();
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export const api = {
  getHealth: () => fetchJson<{ status: string; timestamp: string }>('/api/health'),

  listScenarios: () => fetchJson<Scenario[]>(`${API_BASE}/scenarios`),

  listInvestigations: () => fetchJson<InvestigationSummary[]>(`${API_BASE}/investigations`),

  getInvestigation: (id: string) => fetchJson<Investigation>(`${API_BASE}/investigations/${id}`),

  createInvestigation: (title: string, source_mode: 'DEMO' | 'WAZUH') =>
    fetchJson<{ id: string; title: string; source_mode: string; status: string }>(
      `${API_BASE}/investigations`,
      {
        method: 'POST',
        body: JSON.stringify({ title, source_mode }),
      }
    ),

  startRun: (invId: string, scenarioId: string) =>
    fetchJson<{ run_id: string; status: string; stage_results: any[]; diagnosis: any }>(
      `${API_BASE}/investigations/${invId}/runs`,
      {
        method: 'POST',
        body: JSON.stringify({ scenario_id: scenarioId }),
      }
    ),

  getRunEvidence: (runId: string) =>
    fetchJson<EvidenceRecord[]>(`${API_BASE}/runs/${runId}/evidence`),

  reviewDiagnosis: (diagId: string, decision: 'ACCEPT' | 'REJECT', reviewer: string, note?: string) =>
    fetchJson<{ diagnosis_id: string; review_status: string }>(
      `${API_BASE}/diagnoses/${diagId}/review`,
      {
        method: 'POST',
        body: JSON.stringify({ decision, reviewer, note: note || '' }),
      }
    ),

  approveRemediation: (remId: string, decision: 'APPROVE' | 'REJECT', reviewer: string, note?: string) =>
    fetchJson<{ remediation_id: string; approval_status: string }>(
      `${API_BASE}/remediations/${remId}/approve`,
      {
        method: 'POST',
        body: JSON.stringify({ decision, reviewer, note: note || '' }),
      }
    ),

  executeRetest: (runId: string) =>
    fetchJson<RetestResponse>(`${API_BASE}/runs/${runId}/retest`, {
      method: 'POST',
    }),

  getMetrics: () => fetchJson<MetricsData>(`${API_BASE}/metrics`),

  runEvaluationSuite: () =>
    fetchJson<{ status: string; batch_id: string; metrics: MetricsData }>(
      `${API_BASE}/evaluation/run`,
      { method: 'POST' }
    ),

  testWazuh: () =>
    fetchJson<{ connected: boolean; message: string }>(`${API_BASE}/integrations/wazuh/test`, {
      method: 'POST',
    }),

  getReportDownloadUrl: (invId: string, format: 'json' | 'md') =>
    `${API_BASE}/investigations/${invId}/report?format=${format}`,
};
