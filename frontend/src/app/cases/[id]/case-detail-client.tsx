"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  BrainCircuit,
  CheckCircle2,
  Clock3,
  ReceiptText,
  ShieldCheck,
  XCircle,
} from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { approveAction, getCase, rejectAction } from "@/lib/api";
import { formatDate, formatInr, formatPercent, titleCase } from "@/lib/utils";

export default function CaseDetailPage({ caseId }: { caseId: string }) {
  const searchParams = useSearchParams();
  const resolvedCaseId = searchParams.get("caseId") ?? caseId;
  const queryClient = useQueryClient();
  const detail = useQuery({
    queryKey: ["case", resolvedCaseId],
    queryFn: () => getCase(resolvedCaseId),
    refetchInterval: 5000,
  });

  const approve = useMutation({
    mutationFn: (approvalId: string) => approveAction(approvalId, "dashboard_user"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["case", resolvedCaseId] }),
  });

  const reject = useMutation({
    mutationFn: (approvalId: string) => rejectAction(approvalId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["case", resolvedCaseId] }),
  });

  if (detail.isLoading)
    return (
      <div className="mx-auto max-w-7xl space-y-5">
        <Skeleton className="h-20" />
        <Skeleton className="h-80" />
      </div>
    );

  if (detail.isError || !detail.data)
    return (
      <div className="mx-auto max-w-7xl">
        <Link className="text-sm font-medium text-teal-700" href="/cases">
          Back to cases
        </Link>
        <p className="mt-6 text-rose-700">This recovery case could not be loaded.</p>
      </div>
    );

  const data = detail.data;
  const pendingApprovals = (data.approvals ?? []).filter((a) => a.status === "PENDING");

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <PageHeader
        eyebrow="Case Inspection"
        title={data.case.case_id}
        description={`${titleCase(data.case.failure_reason)} | ${formatInr(data.case.amount_paise)}`}
      >
        <Link className="inline-flex items-center gap-2 text-sm font-medium text-teal-700" href="/cases">
          <ArrowLeft size={16} /> All cases
        </Link>
      </PageHeader>

      <section className="grid gap-6 xl:grid-cols-[0.7fr_1.3fr]">
        <div className="space-y-6">
          {/* Recovery State */}
          <Card>
            <CardHeader>
              <h2 className="font-semibold">Recovery state</h2>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-zinc-500">Status</span>
                <StatusBadge value={data.case.status} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-zinc-500">Experiment</span>
                <span className="text-sm font-medium">{titleCase(data.case.experiment_arm)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-zinc-500">Retry count</span>
                <span className="text-sm font-medium">{data.case.retry_count}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-zinc-500">Gateway</span>
                <StatusBadge value={data.case.gateway_health_state} />
              </div>
            </CardContent>
          </Card>

          {/* ML Triage */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <BrainCircuit size={17} className="text-teal-700" />
                <h2 className="font-semibold">ML triage</h2>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-semibold text-teal-700 dark:text-teal-400">
                {formatPercent(data.triage.recovery_probability)}
              </div>
              <div className="mt-1 text-xs text-zinc-500">Recovery probability</div>
              <div className="mt-5 flex flex-wrap gap-2">
                {data.triage.shap_reason_codes.map((code) => (
                  <span
                    className="rounded bg-teal-50 px-2 py-1 font-mono text-xs font-semibold text-teal-800 dark:bg-teal-950 dark:text-teal-200"
                    key={code}
                  >
                    {code}
                  </span>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* HITL Approval Panel */}
          {pendingApprovals.length > 0 && (
            <Card className="border-amber-300 dark:border-amber-700">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <ShieldCheck size={17} className="text-amber-600" />
                  <h2 className="font-semibold text-amber-800 dark:text-amber-200">
                    Approval Required
                  </h2>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-zinc-600 dark:text-zinc-300">
                  This high-value recovery action requires human approval before execution.
                  Amount: <span className="font-semibold">{formatInr(data.case.amount_paise)}</span>
                </p>
                {pendingApprovals.map((approval) => (
                  <div key={approval.approval_id} className="space-y-3">
                    <div className="flex items-center justify-between text-xs text-zinc-500">
                      <span>Approval ID: {approval.approval_id}</span>
                      <span>Expires: {formatDate(approval.expires_at)}</span>
                    </div>
                    <div className="flex gap-3">
                      <Button
                        className="flex-1 bg-emerald-600 text-white hover:bg-emerald-700"
                        disabled={approve.isPending || reject.isPending}
                        onClick={() => approve.mutate(approval.approval_id)}
                      >
                        <CheckCircle2 size={16} />
                        {approve.isPending ? " Approving…" : " Approve"}
                      </Button>
                      <Button
                        className="flex-1"
                        variant="danger"
                        disabled={approve.isPending || reject.isPending}
                        onClick={() => reject.mutate(approval.approval_id)}
                      >
                        <XCircle size={16} />
                        {reject.isPending ? " Rejecting…" : " Reject"}
                      </Button>
                    </div>
                    {(approve.isError || reject.isError) && (
                      <p className="text-xs text-rose-600">
                        Action failed. The approval may have expired.
                      </p>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Resolved Approvals */}
          {(data.approvals ?? []).filter((a) => a.status !== "PENDING").length > 0 && (
            <Card>
              <CardHeader>
                <h2 className="text-sm font-semibold">Approval history</h2>
              </CardHeader>
              <CardContent className="space-y-2">
                {data.approvals
                  .filter((a) => a.status !== "PENDING")
                  .map((a) => (
                    <div
                      key={a.approval_id}
                      className="flex items-center justify-between rounded border border-zinc-200 px-3 py-2 dark:border-zinc-800"
                    >
                      <StatusBadge value={a.status.toLowerCase()} />
                      <span className="text-xs text-zinc-500">{formatDate(a.expires_at)}</span>
                    </div>
                  ))}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Decision Timeline */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Clock3 size={17} className="text-teal-700" />
              <h2 className="font-semibold">Decision timeline</h2>
            </div>
          </CardHeader>
          <CardContent>
            <ol className="relative ml-2 border-l border-zinc-200 pl-6 dark:border-zinc-800">
              {data.timeline.map((item, index) => (
                <li className="relative pb-6 last:pb-0" key={`${item.type}-${item.at}-${index}`}>
                  <span className="absolute -left-[31px] top-1 size-3 rounded-full border-2 border-white bg-teal-600 dark:border-zinc-950" />
                  <div className="text-sm font-medium">
                    {titleCase(item.action_type ?? item.step ?? item.type)}
                  </div>
                  <div className="mt-1 text-xs text-zinc-500">{formatDate(item.at)}</div>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        {/* Recovery Actions */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <ReceiptText size={17} className="text-teal-700" />
              <h2 className="font-semibold">Recovery actions</h2>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.actions.length ? (
              data.actions.map((action) => (
                <div
                  className="rounded-md border border-zinc-200 p-3 dark:border-zinc-800"
                  key={action.id}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{titleCase(action.action_type)}</span>
                    <StatusBadge value={action.status} />
                  </div>
                  <div className="mt-2 text-xs text-zinc-500">
                    {action.channel ? `Channel: ${action.channel}` : "No customer channel"} | Cost:{" "}
                    {formatInr(action.cost_paise)}
                  </div>
                </div>
              ))
            ) : (
              <Empty text="No actions have been executed yet." />
            )}
          </CardContent>
        </Card>

        {/* Agent Trace */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <ShieldCheck size={17} className="text-teal-700" />
              <h2 className="font-semibold">Agent trace</h2>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.audit_trail.length ? (
              data.audit_trail.map((entry) => (
                <div
                  className="rounded-md border border-zinc-200 p-3 dark:border-zinc-800"
                  key={entry.id}
                >
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-sm font-medium">{titleCase(entry.step)}</span>
                    <span className="text-xs text-zinc-500">{entry.agent_name}</span>
                  </div>
                  <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-300">
                    {entry.reasoning || entry.output_summary}
                  </p>
                  {entry.guardrails_applied.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {entry.guardrails_applied.map((g) => (
                        <span
                          key={g}
                          className="rounded bg-amber-50 px-1.5 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-950 dark:text-amber-300"
                        >
                          {g}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <Empty text="The agent trace will appear after processing." />
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="py-5 text-sm text-zinc-500">{text}</p>;
}
