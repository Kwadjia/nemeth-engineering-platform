import type { ComponentKind, LifecycleState } from "@nemeth/domain-types";
import { Lock, Pin } from "lucide-react";
import { Link } from "react-router-dom";

import { Badge, type BadgeTone } from "@/components/ui/badge";
import { titleCase } from "@/lib/format";
import { cn } from "@/lib/utils";

const LIFECYCLE_TONE: Record<LifecycleState, BadgeTone> = {
  CONCEPT: "outline",
  DESIGN: "accent",
  PROTOTYPE: "warn",
  VALIDATION: "steel",
  RELEASED: "ok",
  OBSOLETE: "danger",
};

export function LifecycleBadge({
  state,
  className,
}: {
  state: LifecycleState;
  className?: string;
}) {
  return (
    <Badge tone={LIFECYCLE_TONE[state]} className={className}>
      {titleCase(state)}
    </Badge>
  );
}

export function KindBadge({ kind }: { kind: ComponentKind }) {
  return <Badge tone={kind === "ASSEMBLY" ? "steel" : "outline"}>{titleCase(kind)}</Badge>;
}

export function PlaceholderBadge({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <Badge tone="warn" title="Sample data from the seed. Replace with real engineering data.">
      Placeholder
    </Badge>
  );
}

export function FrozenBadge({ frozen }: { frozen: boolean }) {
  if (!frozen) return null;
  return (
    <Badge tone="neutral" title="This revision is immutable.">
      <Lock className="h-2.5 w-2.5" /> Frozen
    </Badge>
  );
}

export function PinnedBadge({ pinned }: { pinned: boolean }) {
  if (!pinned) return null;
  return (
    <Badge tone="accent" title="Pinned to an exact child revision.">
      <Pin className="h-2.5 w-2.5" /> Pinned
    </Badge>
  );
}

/** A human identifier, always monospace, optionally a link. */
export function Identifier({
  value,
  to,
  className,
}: {
  value: string;
  to?: string;
  className?: string;
}) {
  const classes = cn("font-mono text-xs font-medium tracking-tight text-fg", className);
  if (to) {
    return (
      <Link to={to} className={cn(classes, "hover:text-accent hover:underline")}>
        {value}
      </Link>
    );
  }
  return <span className={classes}>{value}</span>;
}

export function RevisionChip({
  label,
  state,
  to,
}: {
  label: string;
  state: LifecycleState;
  to?: string;
}) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <Identifier value={`Rev ${label}`} to={to} />
      <LifecycleBadge state={state} />
    </span>
  );
}
