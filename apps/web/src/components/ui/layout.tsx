import type { LucideIcon } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  meta,
}: {
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  meta?: React.ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-4 border-b border-border pb-4">
      <div className="min-w-0">
        {eyebrow ? <div className="label mb-1">{eyebrow}</div> : null}
        <h1 className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xl font-semibold tracking-tight text-fg">
          {title}
        </h1>
        {description ? <p className="mt-1 max-w-3xl text-sm text-fg-muted">{description}</p> : null}
        {meta ? <div className="mt-2 flex flex-wrap items-center gap-2">{meta}</div> : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: {
  icon?: LucideIcon;
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded border border-dashed border-border-strong px-6 py-10 text-center",
        className,
      )}
    >
      {Icon ? <Icon className="h-5 w-5 text-fg-subtle" strokeWidth={1.5} /> : null}
      <div className="text-sm font-medium text-fg">{title}</div>
      {description ? <p className="max-w-md text-xs text-fg-muted">{description}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}

export interface KVItem {
  label: React.ReactNode;
  value: React.ReactNode;
  mono?: boolean;
  span?: 1 | 2;
}

export function KV({
  items,
  columns = 2,
  className,
}: {
  items: KVItem[];
  columns?: 1 | 2 | 3;
  className?: string;
}) {
  return (
    <dl
      className={cn(
        "grid gap-x-6 gap-y-3",
        columns === 1 && "grid-cols-1",
        columns === 2 && "grid-cols-1 sm:grid-cols-2",
        columns === 3 && "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
        className,
      )}
    >
      {items.map((item, i) => (
        <div key={i} className={cn("min-w-0", item.span === 2 && "sm:col-span-2")}>
          <dt className="label mb-0.5">{item.label}</dt>
          <dd
            className={cn(
              "break-words text-sm text-fg",
              item.mono && "font-mono text-xs",
              (item.value === null || item.value === undefined || item.value === "") &&
                "text-fg-subtle",
            )}
          >
            {item.value === null || item.value === undefined || item.value === ""
              ? "—"
              : item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded bg-surface-2", className)} />;
}

export function LoadingRows({ rows = 4 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-2 p-4">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-5 w-full" />
      ))}
    </div>
  );
}

export function ErrorNotice({
  error,
  title = "Could not load data",
}: {
  error: unknown;
  title?: string;
}) {
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div
      role="alert"
      className="rounded border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-danger"
    >
      <div className="font-medium">{title}</div>
      <div className="mt-0.5 text-xs opacity-90">{message}</div>
    </div>
  );
}

export function Stat({
  label,
  value,
  hint,
}: {
  label: React.ReactNode;
  value: React.ReactNode;
  hint?: React.ReactNode;
}) {
  return (
    <div className="rounded border border-border bg-bg-elevated px-3 py-2">
      <div className="label">{label}</div>
      <div className="mt-0.5 font-mono text-lg font-medium text-fg">{value}</div>
      {hint ? <div className="text-xs text-fg-subtle">{hint}</div> : null}
    </div>
  );
}
