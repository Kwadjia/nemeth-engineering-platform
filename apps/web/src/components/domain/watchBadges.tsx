import type { WatchStatus } from "@nemeth/domain-types";

import { Badge, type BadgeTone } from "@/components/ui/badge";
import { titleCase } from "@/lib/format";

const TONE: Record<WatchStatus, BadgeTone> = {
  PLANNED: "outline",
  IN_BUILD: "warn",
  BUILT: "steel",
  PERSONAL_PROTOTYPE: "accent",
  DELIVERED: "ok",
  IN_SERVICE: "warn",
  RETIRED: "neutral",
};

export function WatchStatusBadge({ status }: { status: WatchStatus }) {
  return <Badge tone={TONE[status]}>{titleCase(status)}</Badge>;
}
