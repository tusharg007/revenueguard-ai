export type ExperimentArm = "control" | "treatment" | "unassigned";

export type CaseStatus =
  | "detected"
  | "triaging"
  | "diagnosing"
  | "strategizing"
  | "executing"
  | "recovered"
  | "failed"
  | "escalated"
  | "stopped";

export interface CaseItem {
  case_id: string;
  status: CaseStatus;
  event_type: string;
  amount_paise: number;
  currency: string;
  failure_category: string;
  recovery_probability: number | null;
  experiment_arm: ExperimentArm | null;
  created_at: string;
}

export interface CasesResponse {
  items: CaseItem[];
  page: number;
  page_size: number;
  total: number;
}

export interface GatewayHealth {
  bank: string;
  rail: string;
  state: "closed" | "open" | "half_open";
  success_rate: number;
  technical_failure_rate: number;
  business_decline_rate: number;
  timeout_rate: number;
  baseline_success_rate: number;
  sample_size: number;
  recommended_action: string;
  retry_after_seconds: number;
  confidence: string;
}

export interface Metrics {
  total_events: number;
  revenue_at_risk_paise: number;
  revenue_recovered_paise: number;
  recovery_rate: number;
  by_experiment_arm: Record<
    string,
    { total: number; recovered: number; recovery_rate: number }
  >;
}

export interface ExperimentResults {
  experiment_id: string;
  control: { recovered: number; total: number; recovery_rate: number };
  variant: { recovered: number; total: number; recovery_rate: number };
  sample_size: number;
  absolute_lift: number;
  relative_lift: number;
  ci_lower: number;
  ci_upper: number;
  z_statistic: number;
  p_value: number;
  is_significant: boolean;
  srm: { chi_square: number; p_value: number; pass: boolean };
}

export interface RecoveryAction {
  id: string;
  action_type: string;
  channel: string | null;
  status: string;
  input_state: Record<string, unknown>;
  output_result: Record<string, unknown>;
  cost_paise: number;
  created_at: string;
}

export interface AuditEntry {
  id: string;
  action_id: string | null;
  agent_name: string;
  step: string;
  input_summary: string;
  output_summary: string;
  reasoning: string;
  guardrails_applied: string[];
  duration_ms: number;
  created_at: string;
}

export interface TimelineItem {
  type: string;
  at: string;
  action_type?: string;
  step?: string;
}

export interface CaseDetail {
  case: CaseItem & {
    external_payment_id: string;
    external_order_id: string | null;
    failure_source: string;
    failure_reason: string;
    error_code: string;
    customer: Record<string, unknown>;
    merchant_id: string;
    shap_reason_codes: string[];
    gateway_health_state: string | null;
    retry_count: number;
    updated_at: string | null;
  };
  triage: { recovery_probability: number | null; shap_reason_codes: string[] };
  gateway_health: GatewayHealth | null;
  actions: RecoveryAction[];
  audit_trail: AuditEntry[];
  approvals: Array<{ approval_id: string; status: string; expires_at: string }>;
  timeline: TimelineItem[];
}

export interface RazorpayOrder {
  order_id: string;
  amount: number;
  currency: string;
  key_id: string;
  receipt: string;
}
