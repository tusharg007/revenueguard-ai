import axios from "axios";

import type {
  CaseDetail,
  CasesResponse,
  ExperimentResults,
  GatewayHealth,
  Metrics,
  RazorpayOrder,
} from "@/lib/types";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  timeout: 12_000,
});

export async function getCases(params?: {
  status?: string;
  experimentArm?: string;
  page?: number;
  pageSize?: number;
}) {
  const { data } = await api.get<CasesResponse>("/api/cases", {
    params: {
      status: params?.status || undefined,
      experiment_arm: params?.experimentArm || undefined,
      page: params?.page ?? 1,
      page_size: params?.pageSize ?? 20,
    },
  });
  return data;
}

export async function getCase(caseId: string) {
  const { data } = await api.get<CaseDetail>(`/api/cases/${caseId}`);
  return data;
}

export async function getMetrics() {
  const { data } = await api.get<Metrics>("/api/metrics");
  return data;
}

export async function getGatewayHealth() {
  const { data } = await api.get<{ items: GatewayHealth[]; available: boolean }>(
    "/api/gateway-health",
  );
  return data;
}

export async function getExperimentResults(experimentId = "recovery_agent_v1") {
  const { data } = await api.get<ExperimentResults>(
    `/api/experiments/${experimentId}/results`,
  );
  return data;
}

export async function simulateBatch(count = 50) {
  const { data } = await api.post<{ created: number; queued: number; case_ids: string[] }>(
    "/api/simulate/batch",
    { count },
  );
  return data;
}

export async function simulateOutage(bank = "SBI", rail = "UPI") {
  const { data } = await api.post("/api/simulate/outage", { bank, rail });
  return data;
}

export async function createOrder(amountPaise: number, receipt?: string) {
  const { data } = await api.post<RazorpayOrder>("/api/orders", {
    amount_paise: amountPaise,
    receipt,
  });
  return data;
}

export async function getRazorpayStatus() {
  const { data } = await api.get<{ connected: boolean; environment: string }>(
    "/api/razorpay/status",
  );
  return data;
}

export async function approveAction(approvalId: string, approvedBy: string) {
  const { data } = await api.post<{ approval_id: string; status: string; queued: boolean }>(
    `/api/approvals/${approvalId}/approve`,
    { approved_by: approvedBy },
  );
  return data;
}

export async function rejectAction(approvalId: string) {
  const { data } = await api.post<{ approval_id: string; status: string }>(
    `/api/approvals/${approvalId}/reject`,
  );
  return data;
}

