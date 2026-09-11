import { Construction } from "lucide-react";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState, PageHeader } from "@/components/ui/layout";

type Area = "experiments" | "testing" | "watches" | "suppliers" | "documents" | "changes";

const AREAS: Record<Area, { title: string; slice: number; summary: string; contents: string[] }> = {
  experiments: {
    title: "Experiments",
    slice: 8,
    summary:
      "Watchmaking development treated like iterative product development: hypothesis, procedure, measurements, conclusion.",
    contents: [
      "EXP-001 ST36 complete disassembly",
      "EXP-002 ST36 reassembly",
      "EXP-003 ST36 baseline timing",
      "Before/after comparisons",
    ],
  },
  testing: {
    title: "Testing",
    slice: 9,
    summary:
      "An extensible measurement model. Timegrapher first (rate, amplitude, beat error, lift angle, six positions), then power reserve, water resistance, dimensional inspection and custom test types.",
    contents: [
      "Test type registry with payload schemas",
      "Test runs with equipment and conditions",
      "Measurements queryable across types",
    ],
  },
  watches: {
    title: "Watches",
    slice: 10,
    summary:
      "Serialized watches (N1-001 …) with a complete digital build record: BOM genealogy, exact revisions, assembly, test, regulation and service history.",
    contents: [
      "Serial register",
      "Build records shared with prototypes",
      "Part instances with supplier and lot traceability",
    ],
  },
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
