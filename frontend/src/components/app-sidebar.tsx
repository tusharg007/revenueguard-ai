"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  FlaskConical,
  LayoutDashboard,
  RadioTower,
  ShieldCheck,
} from "lucide-react";

import { cn } from "@/lib/utils";

const items = [
  { href: "/", label: "Control Room", icon: LayoutDashboard },
  { href: "/sandbox", label: "Sandbox", icon: FlaskConical },
  { href: "/cases", label: "Cases", icon: Activity },
  { href: "/experiments", label: "Experiments", icon: BarChart3 },
  { href: "/gateway-health", label: "Gateway Health", icon: RadioTower },
];

export function AppSidebar() {
  const pathname = usePathname();
  return (
    <aside className="border-b border-zinc-200 bg-white lg:fixed lg:inset-y-0 lg:w-64 lg:border-b-0 lg:border-r dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex h-16 items-center gap-3 px-5 lg:h-20">
        <div className="grid size-9 place-items-center rounded-md bg-teal-700 text-white">
          <ShieldCheck size={20} />
        </div>
        <div>
          <div className="text-sm font-bold text-zinc-900 dark:text-white">RevenueGuard AI</div>
          <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-teal-700 dark:text-teal-400">Recovery Operations</div>
        </div>
      </div>
      <nav className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-col lg:px-3 lg:py-4">
        {items.map((item) => {
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              className={cn(
                "flex shrink-0 items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-teal-50 text-teal-800 dark:bg-teal-950/60 dark:text-teal-200"
                  : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-900",
              )}
              href={item.href}
              key={item.href}
            >
              <Icon size={17} />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="hidden border-t border-zinc-100 px-5 py-4 lg:block dark:border-zinc-800">
        <div className="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
          <span className="size-2 rounded-full bg-emerald-500" /> Live operations
        </div>
      </div>
    </aside>
  );
}
