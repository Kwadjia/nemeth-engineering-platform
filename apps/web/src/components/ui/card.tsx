import * as React from "react";

import { cn } from "@/lib/utils";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <section
      className={cn("rounded-md border border-border bg-surface shadow-raised", className)}
      {...props}
    />
  );
}

export function CardHeader({
  className,
  title,
  eyebrow,
  actions,
  children,
  ...props
}: Omit<React.HTMLAttributes<HTMLDivElement>, "title"> & {
  title?: React.ReactNode;
  eyebrow?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <header
      className={cn(
        "flex items-start justify-between gap-4 border-b border-border px-4 py-2.5",
        className,
      )}
      {...props}
    >
      <div className="min-w-0">
        {eyebrow ? <div className="label mb-0.5">{eyebrow}</div> : null}
        {title ? <h2 className="truncate text-sm font-semibold text-fg">{title}</h2> : null}
        {children}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </header>
  );
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-4 py-3", className)} {...props} />;
}
