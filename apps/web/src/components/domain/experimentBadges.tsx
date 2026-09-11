import type { ExperimentOutcome, ExperimentStatus } from "@nemeth/domain-types";

import { Badge, type BadgeTone } from "@/components/ui/badge";
import { titleCase } from "@/lib/format";

const STATUS_TONE: Record<ExperimentStatus, BadgeTone> = {
  PLANNED: "outline",
  IN_PROGRESS: "warn",
  COMPLETED: "ok",
  ABANDONED: "neutral",
};

const OUTCOME_TONE: Record<ExperimentOutcome, BadgeTone> = {
  IMPROVEMENT: "ok",
  NO_CHANGE: "neutral",
  REGRESSION: "danger",
  INCONCLUSIVE: "outline",
};

export function ExperimentStatusBadge({ status }: { status: ExperimentStatus }) {
  return <Badge tone={STATUS_TONE[status]}>{titleCase(status)}</Badge>;
}

export function OutcomeBadge({ outcome }: { outcome: ExperimentOutcome | null | undefined }) {
  if (!outcome) return null;
  return <Badge tone={OUTCOME_TONE[outcome]}>{titleCase(outcome)}</Badge>;
}
