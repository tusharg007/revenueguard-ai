"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Activity, ArrowUpRight, CircleAlert, FlaskConical, LoaderCircle, Radar, RefreshCw, ShieldAlert } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getCases, getExperimentResults, getGatewayHealth, getMetrics, simulateBatch, simulateOutage } from "@/lib/api";
import { cn, formatDate, formatInr, formatPercent, titleCase } from "@/lib/utils";

const banks = ["SBI", "HDFC", "ICICI", "Axis", "Kotak", "PNB"];

export default function Home() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const metrics = useQuery({ queryKey: ["metrics"], queryFn: getMetrics, refetchInterval: 5000 });
  const health = useQuery({ queryKey: ["gateway-health"], queryFn: getGatewayHealth, refetchInterval: 5000 });
  const experiment = useQuery({ queryKey: ["experiment"], queryFn: () => getExperimentResults(), refetchInterval: 5000 });
  const cases = useQuery({ queryKey: ["cases", "recent"], queryFn: () => getCases({ pageSize: 6 }), refetchInterval: 5000 });
  const refresh = () => queryClient.invalidateQueries();
  const batch = useMutation({ mutationFn: () => simulateBatch(50), onSuccess: refresh });
  const outage = useMutation({ mutationFn: () => simulateOutage("SBI", "UPI"), onSuccess: refresh });
  const chartData = [{ name: "Baseline", rate: (experiment.data?.control.recovery_rate ?? 0) * 100 }, { name: "Agent", rate: (experiment.data?.variant.recovery_rate ?? 0) * 100 }];
  const recovered = Object.values(metrics.data?.by_experiment_arm ?? {}).reduce((sum, group) => sum + group.recovered, 0);
  const activeFailures = Math.max((metrics.data?.total_events ?? 0) - recovered, 0);

  return <div className="mx-auto max-w-7xl space-y-6">
    <PageHeader eyebrow="Simulation Control Room" title="Recovery operations" description="Live triage, experiment, and gateway signal monitoring."><Button variant="secondary" onClick={refresh}><RefreshCw size={15} /> Refresh</Button></PageHeader>
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><MetricCard icon={Activity} label="Active Failed Payments" value={activeFailures.toLocaleString("en-IN")} tone="teal" loading={metrics.isLoading} /><MetricCard icon={CircleAlert} label="Revenue at Risk" value={formatInr(metrics.data?.revenue_at_risk_paise)} tone="amber" loading={metrics.isLoading} /><MetricCard icon={ArrowUpRight} label="Revenue Recovered" value={formatInr(metrics.data?.revenue_recovered_paise)} tone="green" loading={metrics.isLoading} /><MetricCard icon={Radar} label="Recovery Rate" value={formatPercent(metrics.data?.recovery_rate)} tone="rose" loading={metrics.isLoading} /></section>
    <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
      <Card><CardHeader className="flex flex-row items-center justify-between"><div><h2 className="font-semibold">Gateway Health Map</h2><p className="mt-1 text-xs text-zinc-500">15-minute signal across active payment rails</p></div><StatusBadge value={health.data?.available ? "healthy" : "unknown"} /></CardHeader><CardContent className="space-y-5">{banks.map((bank) => { const item = health.data?.items.find((record) => record.bank.toUpperCase() === bank.toUpperCase()); const rate = item?.success_rate ?? 0; const color = item?.state === "open" ? "bg-rose-500" : item?.state === "half_open" ? "bg-amber-400" : item ? "bg-emerald-500" : "bg-zinc-300 dark:bg-zinc-700"; return <div key={bank} className="grid grid-cols-[58px_1fr_auto] items-center gap-3"><span className="text-sm font-medium">{bank}</span><div className="h-2 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800"><div className={cn("h-full rounded-full", color)} style={{ width: `${Math.max(item ? rate * 100 : 4, 4)}%` }} /></div><span className="min-w-28 text-right text-xs text-zinc-500">{item ? `${formatPercent(rate)} | ${item.sample_size} attempts` : "Awaiting signal"}</span></div>; })}</CardContent></Card>
      <Card><CardHeader><h2 className="font-semibold">Experiment Snapshot</h2><p className="mt-1 text-xs text-zinc-500">Control versus recovery agent</p></CardHeader><CardContent><div className="h-44"><ResponsiveContainer width="100%" height="100%"><BarChart data={chartData} margin={{ top: 8, right: 0, left: -22, bottom: 0 }}><XAxis dataKey="name" tickLine={false} axisLine={false} fontSize={12} /><YAxis tickLine={false} axisLine={false} fontSize={11} unit="%" /><Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} cursor={{ fill: "#f4f4f5" }} /><Bar dataKey="rate" fill="#0f766e" radius={[3, 3, 0, 0]} /></BarChart></ResponsiveContainer></div><div className="grid grid-cols-2 gap-3 border-t border-zinc-100 pt-4 text-sm dark:border-zinc-800"><div><div className="text-xs text-zinc-500">Absolute lift</div><div className="mt-1 font-semibold text-teal-700 dark:text-teal-400">{formatPercent(experiment.data?.absolute_lift)}</div></div><div><div className="text-xs text-zinc-500">P-value</div><div className="mt-1 flex items-center gap-2"><span className="font-semibold">{experiment.data?.p_value?.toFixed(4) ?? "--"}</span><StatusBadge value={experiment.data?.is_significant ? "significant" : "not significant"} /></div></div></div></CardContent></Card>
    </section>
    <section className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
      <Card><CardHeader><h2 className="font-semibold">Simulation controls</h2><p className="mt-1 text-xs text-zinc-500">Inject test traffic into the recovery pipeline</p></CardHeader><CardContent className="space-y-3"><Button className="w-full justify-start" disabled={batch.isPending} onClick={() => batch.mutate()}>{batch.isPending ? <LoaderCircle className="animate-spin" size={16} /> : <FlaskConical size={16} />} Run Recovery Batch</Button><Button className="w-full justify-start" variant="secondary" disabled={outage.isPending} onClick={() => outage.mutate()}>{outage.isPending ? <LoaderCircle className="animate-spin" size={16} /> : <ShieldAlert size={16} />} Simulate SBI Outage</Button><Button className="w-full justify-start" variant="ghost" disabled={!cases.data?.items.length} onClick={() => { const list = cases.data?.items ?? []; router.push(`/cases/${encodeURIComponent(list[Math.floor(Math.random() * list.length)]?.case_id ?? "")}`); }}><Activity size={16} /> Inspect Random Case</Button>{(batch.isError || outage.isError) && <p className="text-xs text-rose-700">The API could not complete this simulation. Check that Redis is running for queue and outage actions.</p>}</CardContent></Card>
      <Card><CardHeader className="flex flex-row items-center justify-between"><div><h2 className="font-semibold">Recent recovery events</h2><p className="mt-1 text-xs text-zinc-500">Refreshed every 5 seconds</p></div><Link className="text-xs font-semibold text-teal-700 hover:underline dark:text-teal-400" href="/cases">View all cases</Link></CardHeader><CardContent className="divide-y divide-zinc-100 p-0 dark:divide-zinc-800">{cases.isLoading ? <div className="space-y-3 p-5"><Skeleton className="h-10" /><Skeleton className="h-10" /><Skeleton className="h-10" /></div> : cases.data?.items.map((item) => <Link className="flex items-center gap-3 px-5 py-3 hover:bg-zinc-50 dark:hover:bg-zinc-900" href={`/cases/${encodeURIComponent(item.case_id)}`} key={item.case_id}><span className="size-2 rounded-full bg-teal-500" /><div className="min-w-0 flex-1"><div className="truncate text-sm font-medium">{item.case_id}</div><div className="text-xs text-zinc-500">{titleCase(item.failure_category)} | {formatDate(item.created_at)}</div></div><div className="text-right"><div className="text-sm font-semibold">{formatInr(item.amount_paise)}</div><StatusBadge value={item.status} /></div></Link>) ?? <div className="p-5 text-sm text-zinc-500">No recovery cases yet.</div>}</CardContent></Card>
    </section>
  </div>;
}

function MetricCard({ icon: Icon, label, value, tone, loading }: { icon: typeof Activity; label: string; value: string; tone: "teal" | "amber" | "green" | "rose"; loading: boolean }) { const tones = { teal: "bg-teal-50 text-teal-700 dark:bg-teal-950/50 dark:text-teal-300", amber: "bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300", green: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300", rose: "bg-rose-50 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300" }; return <Card><CardContent className="flex items-start justify-between"><div><p className="text-xs font-medium text-zinc-500">{label}</p>{loading ? <Skeleton className="mt-3 h-8 w-28" /> : <p className="mt-2 text-2xl font-semibold">{value}</p>}</div><div className={cn("grid size-10 place-items-center rounded-md", tones[tone])}><Icon size={19} /></div></CardContent></Card>; }
