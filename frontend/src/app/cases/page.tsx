"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronRight, Search } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table } from "@/components/ui/table";
import { getCases } from "@/lib/api";
import { formatDate, formatInr, formatPercent, titleCase } from "@/lib/utils";

const detailHref = (caseId: string) =>
  `/cases/${encodeURIComponent(caseId)}`;

export default function CasesPage() {
  const [status, setStatus] = useState("");
  const [arm, setArm] = useState("");
  const [search, setSearch] = useState("");
  const cases = useQuery({
    queryKey: ["cases", status, arm],
    queryFn: () => getCases({ status, experimentArm: arm, pageSize: 100 }),
    refetchInterval: 5000,
  });
  const rows = (cases.data?.items ?? []).filter((item) =>
    item.case_id.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <PageHeader
        eyebrow="Recovery Cases"
        title="Payment failure queue"
        description="Inspect every recovery decision and its operational state."
      />
      <Card>
        <CardContent className="space-y-5">
          <div className="grid gap-3 md:grid-cols-[1fr_180px_180px]">
            <div className="relative">
              <Search className="absolute left-3 top-3 text-zinc-400" size={16} />
              <Input
                className="pl-9"
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search case ID"
                value={search}
              />
            </div>
            <Select onChange={(event) => setStatus(event.target.value)} value={status}>
              <option value="">All statuses</option>
              {["detected", "triaging", "executing", "recovered", "failed", "escalated", "stopped"].map(
                (value) => (
                  <option key={value} value={value}>
                    {titleCase(value)}
                  </option>
                ),
              )}
            </Select>
            <Select onChange={(event) => setArm(event.target.value)} value={arm}>
              <option value="">All experiment arms</option>
              <option value="control">Control</option>
              <option value="treatment">Treatment</option>
            </Select>
          </div>
          <div className="overflow-x-auto">
            <Table>
              <thead className="border-y border-zinc-200 text-xs uppercase tracking-wide text-zinc-500 dark:border-zinc-800">
                <tr>
                  <th className="px-3 py-3 font-medium">Case</th>
                  <th className="px-3 py-3 font-medium">Failure</th>
                  <th className="px-3 py-3 font-medium">Amount</th>
                  <th className="px-3 py-3 font-medium">Probability</th>
                  <th className="px-3 py-3 font-medium">Arm</th>
                  <th className="px-3 py-3 font-medium">Status</th>
                  <th className="px-3 py-3" />
                </tr>
              </thead>
              <tbody>
                {cases.isLoading
                  ? Array.from({ length: 6 }).map((_, index) => (
                      <tr key={index}>
                        <td className="px-3 py-3" colSpan={7}>
                          <Skeleton className="h-8" />
                        </td>
                      </tr>
                    ))
                  : rows.map((item) => (
                      <tr
                        className="border-b border-zinc-100 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-900"
                        key={item.case_id}
                      >
                        <td className="px-3 py-3">
                          <div className="font-mono text-xs font-medium">
                            {item.case_id}
                          </div>
                          <div className="mt-1 text-xs text-zinc-500">
                            {formatDate(item.created_at)}
                          </div>
                        </td>
                        <td className="px-3 py-3 text-sm">
                          {titleCase(item.failure_category)}
                        </td>
                        <td className="px-3 py-3 font-medium">
                          {formatInr(item.amount_paise)}
                        </td>
                        <td className="px-3 py-3">
                          {item.recovery_probability === null
                            ? "--"
                            : formatPercent(item.recovery_probability)}
                        </td>
                        <td className="px-3 py-3 text-sm">
                          {titleCase(item.experiment_arm)}
                        </td>
                        <td className="px-3 py-3">
                          <StatusBadge value={item.status} />
                        </td>
                        <td className="px-3 py-3">
                          <Link
                            aria-label={`Inspect ${item.case_id}`}
                            className="inline-flex text-teal-700 hover:text-teal-900 dark:text-teal-400"
                            href={detailHref(item.case_id)}
                          >
                            <ChevronRight size={18} />
                          </Link>
                        </td>
                      </tr>
                    ))}
              </tbody>
            </Table>
            {!cases.isLoading && rows.length === 0 && (
              <div className="py-12 text-center text-sm text-zinc-500">
                No cases match these filters.
              </div>
            )}
          </div>
          <div className="text-xs text-zinc-500">
            {cases.data?.total ?? 0} recovery cases in the queue
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
