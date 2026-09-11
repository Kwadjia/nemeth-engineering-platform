import type { TestOutcome } from "@nemeth/domain-types";

import { Badge, type BadgeTone } from "@/components/ui/badge";

const TONE: Record<TestOutcome, BadgeTone> = { PASS: "ok", FAIL: "danger", INFO: "outline" };

export function OutcomeBadgeTest({ outcome }: { outcome: TestOutcome }) {
  return (
    <Badge tone={TONE[outcome]}>
      {outcome === "INFO" ? "Info" : outcome === "PASS" ? "Pass" : "Fail"}
    </Badge>
  );
}

export function TestTypeBadge({ code, name }: { code: string; name: string }) {
  return (
    <Badge tone="steel" title={code}>
      {name}
    </Badge>
  );
}
