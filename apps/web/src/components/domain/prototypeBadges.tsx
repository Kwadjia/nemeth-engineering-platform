import type { PartInstanceStatus, PartSource, PrototypeStatus } from "@nemeth/domain-types";

import { Badge, type BadgeTone } from "@/components/ui/badge";
import { titleCase } from "@/lib/format";

const PROTOTYPE_TONE: Record<PrototypeStatus, BadgeTone> = {
  PLANNED: "outline",
  BUILDING: "warn",
  ACTIVE: "ok",
  RETIRED: "neutral",
};

const INSTANCE_TONE: Record<PartInstanceStatus, BadgeTone> = {
  AVAILABLE: "accent",
  INSTALLED: "ok",
  REMOVED: "outline",
  SCRAPPED: "danger",
};

export function PrototypeStatusBadge({ status }: { status: PrototypeStatus }) {
  return <Badge tone={PROTOTYPE_TONE[status]}>{titleCase(status)}</Badge>;
}

export function InstanceStatusBadge({ status }: { status: PartInstanceStatus }) {
  return <Badge tone={INSTANCE_TONE[status]}>{titleCase(status)}</Badge>;
}

export function SourceBadge({ source }: { source: PartSource }) {
  return <Badge tone="outline">{titleCase(source)}</Badge>;
}
