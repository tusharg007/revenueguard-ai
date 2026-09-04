import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Tabs({ children }: { children: React.ReactNode }) {
  return <div className="inline-flex rounded-md bg-zinc-100 p-1 dark:bg-zinc-900">{children}</div>;
}

export function Tab({ className, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={cn("rounded px-3 py-1.5 text-xs font-medium", className)} {...props} />;
}
