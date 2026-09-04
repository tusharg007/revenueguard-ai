export function PageHeader({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="flex flex-col gap-4 border-b border-zinc-200 pb-5 sm:flex-row sm:items-end sm:justify-between dark:border-zinc-800">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-teal-700 dark:text-teal-400">{eyebrow}</p>
        <h1 className="mt-1 text-2xl font-semibold text-zinc-950 dark:text-white">{title}</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">{description}</p>
      </div>
      {children}
    </header>
  );
}
