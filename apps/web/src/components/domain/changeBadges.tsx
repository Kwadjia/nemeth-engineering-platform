import type { ChangeRole, ChangeStatus, SupplierKind } from "@nemeth/domain-types";

import { Badge, type BadgeTone } from "@/components/ui/badge";
import { titleCase } from "@/lib/format";

const STATUS_TONE: Record<ChangeStatus, BadgeTone> = {
  DRAFT: "outline",
  PROPOSED: "accent",
  APPROVED: "warn",
  IMPLEMENTED: "ok",
  REJECTED: "danger",
};

export function ChangeStatusBadge({ status }: { status: ChangeStatus }) {
  return <Badge tone={STATUS_TONE[status]}>{titleCase(status)}</Badge>;
}

export function ChangeRoleBadge({ role }: { role: ChangeRole }) {
  return (
    <Badge tone={role === "AFFECTED" ? "warn" : "ok"}>{role === "AFFECTED" ? "From" : "To"}</Badge>
  );
}

export function SupplierKindBadge({ kind }: { kind: SupplierKind }) {
  return <Badge tone={kind === "IN_HOUSE" ? "accent" : "outline"}>{titleCase(kind)}</Badge>;
}
