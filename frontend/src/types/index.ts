export type PipelineStage = 
  | 'event_generation'
  | 'collection'
  | 'parsing'
  | 'rule_evaluation'
  | 'alert_generation'
  | 'delivery_visibility';

export type StageStatus = 'PASS' | 'FAIL' | 'UNKNOWN' | 'NOT REACHED';

export type DiagnosticOutcome = 'FAILURE_LOCALIZED' | 'HEALTHY' | 'UNDETERMINED';

export interface StageResult {
  id?: string;
  stage: PipelineStage;
  status: StageStatus;
  reason: string;
  evidence_ids: string[];
}

export interface RemediationAction {
  id: string;
  diagnosis_id: string;
  proposed_change: string | null;
  approval_status: 'PENDING' | 'APPROVED' | 'REJECTED';
  execution_status: 'NOT_EXECUTED' | 'SIMULATED_APPLIED';
  approved_by: string | null;
  decided_at: string | null;
  decision_note: string | null;
}

export interface Diagnosis {
  id: string;
  run_id: string;
  outcome: DiagnosticOutcome;
  failure_stage: PipelineStage | null;
  reason: string;
  confidence_label: string;
  evidence_refs: string[];
  limitations: string[];
  created_at: string;
  latency_ms: number;
  review_status: 'ACCEPT' | 'REJECT' | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_note: string | null;
  remediation?: RemediationAction | null;
}

export interface TestRun {
  id: string;
  investigation_id: string;
  scenario_id: string;
  run_type: 'INITIAL' | 'RETEST';
  parent_run_id: string | null;
  started_at: string;
  finished_at: string | null;
  status: 'COMPLETED' | 'ERROR';
  error: string | null;
  stage_results: StageResult[];
  diagnosis: Diagnosis | null;
  remediation: RemediationAction | null;
}

export interface AuditEvent {
  id: string;
  actor: string;
  action: string;
  timestamp: string;
  details: Record<string, any>;
}

export interface Investigation {
  id: string;
  title: string;
  source_mode: 'DEMO' | 'WAZUH';
  kind: 'ANALYST' | 'EVALUATION';
  status: string;
  created_at: string;
  runs: TestRun[];
  audit_events: AuditEvent[];
}

export interface InvestigationSummary {
  id: string;
  title: string;
  source_mode: 'DEMO' | 'WAZUH';
  status: string;
  created_at: string;
  runs_count: number;
  latest_outcome: DiagnosticOutcome | null;
  failure_stage: PipelineStage | null;
}

export interface Scenario {
  id: string;
  family: string;
  variant: string;
  split: string;
  name: string;
  description: string;
  expected_stages: Record<string, any>;
}

export interface EvidenceRecord {
  id: string;
  run_id: string;
  stage: PipelineStage;
  checkpoint_id: string;
  source_label: 'SYNTHETIC' | 'WAZUH';
  availability: 'AVAILABLE' | 'UNAVAILABLE';
  payload: Record<string, any>;
  observed_at: string;
  content_hash: string;
}

export interface RecoveryCheck {
  id: string;
  name: string;
  description: string;
  status: 'PASS' | 'FAIL' | 'NOT_EVALUABLE';
  detail: string;
}

export interface RetestResponse {
  retest_run_id: string;
  parent_run_id: string;
  investigation_id: string;
  status: string;
  stage_results: StageResult[];
  diagnosis: Diagnosis;
  recovery_checks: RecoveryCheck[];
  final_result: 'VERIFIED' | 'UNRESOLVED' | 'UNDETERMINED';
}

export interface MetricDetail {
  numerator: number;
  denominator: number;
  value: number | null;
  display: string;
  definition: string;
}

export interface MetricsData {
  has_data: boolean;
  message?: string;
  batch_id?: string;
  evaluated_at?: string;
  disclaimer?: string;
  combined?: {
    case_count: number;
    failure_localization_accuracy: MetricDetail;
    false_attribution_rate: MetricDetail;
    abstention_quality: {
      supported_abstention: MetricDetail;
      unnecessary_abstention: MetricDetail;
    };
    diagnosis_latency: {
      mean_ms: number | null;
      median_ms: number | null;
      max_ms: number | null;
      manual_baseline: string;
      definition: string;
    };
    retest_verification_accuracy: MetricDetail;
    evidence_coverage: MetricDetail;
  };
  development?: any;
  held_out?: any;
}
