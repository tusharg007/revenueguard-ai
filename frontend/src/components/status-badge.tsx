import { Badge } from "@/components/ui/badge";
import { cn, titleCase } from "@/lib/utils";

export function StatusBadge({ value }: { value: string | null | undefined }) {
  const normalized = (value ?? "unknown").toLowerCase();
  const style =
    normalized === "closed" || normalized === "recovered" || normalized === "healthy"
      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
      : normalized === "open" || normalized === "failed" || normalized === "stopped"
        ? "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
        : normalized === "half_open" || normalized === "escalated"
          ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
          : "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300";
  return <Badge className={cn(style)}>{titleCase(value)}</Badge>;
}
