import { Construction } from "lucide-react";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState, PageHeader } from "@/components/ui/layout";

type Area = "suppliers" | "documents" | "changes";

const AREAS: Record<Area, { title: string; slice: number; summary: string; contents: string[] }> = {
  suppliers: {
    title: "Suppliers",
    slice: 12,
    summary: "Who makes what, linked from component revisions and part instances.",
    contents: [
      "Supplier register",
      "Default supplier per revision",
      "Actual supplier per part instance",
    ],
  },
  documents: {
    title: "Documents",
    slice: 11,
    summary:
      "CAD, drawings, photos, test results and certificates attached to any engineering entity, stored outside the database with SHA-256 verification.",
    contents: [
      "Attachment upload with validation",
      "SHA-256 change detection",
      "Storage backends: local now, object storage later",
    ],
  },
  changes: {
    title: "Engineering changes",
    slice: 12,
    summary:
      "Lightweight ECR records: affected revision, proposed revision, evidence experiments, status.",
    contents: [
      "ECR register",
      "Links from frozen revisions to their successors",
      "Evidence from experiments and test runs",
    ],
  },
};

export function PlannedPage({ area }: { area: Area }) {
  const info = AREAS[area];
  return (
    <div>
      <PageHeader
        eyebrow={`Planned · slice ${info.slice}`}
        title={info.title}
        description={info.summary}
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <EmptyState
            icon={Construction}
            title={`${info.title} are not implemented yet`}
            description={`This area is designed in docs/domain/domain-model.md and arrives in development slice ${info.slice}. No placeholder data is shown.`}
          />
        </div>
        <Card>
          <CardHeader eyebrow="Will contain" />
          <CardContent>
            <ul className="list-disc space-y-1 pl-4 text-sm text-fg-muted">
              {info.contents.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
