import type { Metadata } from "next";
import { AppSidebar } from "@/components/app-sidebar";
import { Providers } from "@/components/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "RevenueGuard AI",
  description: "Intelligent payment recovery operations dashboard",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-zinc-50 text-zinc-950 dark:bg-[#111416] dark:text-zinc-100">
        <Providers>
          <AppSidebar />
          <main className="min-h-screen px-4 py-6 lg:ml-64 lg:px-8 lg:py-8">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
