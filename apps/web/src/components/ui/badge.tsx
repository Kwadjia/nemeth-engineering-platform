import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded border px-1.5 py-px font-mono text-2xs font-medium uppercase tracking-label",
  {
    variants: {
      tone: {
        neutral: "border-border-strong bg-surface-2 text-fg-muted",
        outline: "border-border-strong bg-transparent text-fg-muted",
        accent: "border-accent/40 bg-accent/10 text-accent",
        steel: "border-steel/40 bg-steel/10 text-steel",
        ok: "border-ok/40 bg-ok/10 text-ok",
        warn: "border-warn/40 bg-warn/10 text-warn",
        danger: "border-danger/40 bg-danger/10 text-danger",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}

export type BadgeTone = NonNullable<VariantProps<typeof badgeVariants>["tone"]>;
