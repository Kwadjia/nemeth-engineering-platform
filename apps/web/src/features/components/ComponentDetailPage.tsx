import type { RevisionRead } from "@nemeth/domain-types";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  FrozenBadge,
  Identifier,
  KindBadge,
  LifecycleBadge,
  PlaceholderBadge,
} from "@/components/domain/badges";
import { BomTree } from "@/components/domain/BomTree";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Field, FormError, Input, Textarea } from "@/components/ui/form";
import { EmptyState, ErrorNotice, KV, LoadingRows, PageHeader } from "@/components/ui/layout";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { describeError } from "@/lib/api";
import { displayValue, formText, formatDateTime, formatNumber, titleCase } from "@/lib/format";
import {
  useBom,
  useComponent,
  useCreateRevision,
  useRevisions,
  useTransitionRevision,
  useUpdateRevision,
  useWhereUsed,
} from "@/lib/queries";
import { cn } from "@/lib/utils";

export function ComponentDetailPage() {
  const { ref = "", label } = useParams();
  const navigate = useNavigate();
  const component = useComponent(ref);
  const revisions = useRevisions(ref);

  if (component.isLoading || revisions.isLoading) return <LoadingRows />;
  if (component.isError) return <ErrorNotice error={component.error} />;
  if (revisions.isError) return <ErrorNotice error={revisions.error} />;
  if (!component.data || !revisions.data) return null;

  const c = component.data;
  const selected =
    (label ? revisions.data.find((r) => r.revision_label === label.toUpperCase()) : undefined) ??
    revisions.data[revisions.data.length - 1];

  return (
    <div>
      <PageHeader
        eyebrow={
          <span>
            <Link to="/components" className="hover:underline">
              Components
            </Link>{" "}
            / {c.family}
          </span>
        }
        title={
          <>
            <Identifier value={c.identifier} className="text-xl" />
            <span>{c.name}</span>
          </>
        }
        description={c.description}
        meta={
          <>
            <KindBadge kind={c.kind} />
            <PlaceholderBadge show={c.is_placeholder} />
            {c.released_revision ? (
              <span className="text-xs text-fg-subtle">
                Released: Rev {c.released_revision.revision_label}
              </span>
            ) : null}
          </>
        }
        actions={
          c.kind === "ASSEMBLY" ? (
            <Button onClick={() => navigate(`/boms/${c.identifier}`)}>Open BOM explorer</Button>
          ) : null
        }
      />

      <div className="grid gap-4 xl:grid-cols-[18rem_1fr]">
        <Card className="self-start">
          <CardHeader eyebrow="History" title="Revisions" />
          <ul className="divide-y divide-border">
            {[...revisions.data].reverse().map((r) => (
              <li key={r.id}>
                <Link
                  to={`/components/${c.identifier}/revisions/${r.revision_label}`}
                  className={cn(
                    "flex flex-col gap-1 px-4 py-2.5 transition-colors hover:bg-surface-2",
                    selected?.id === r.id && "bg-surface-2 shadow-raised",
                  )}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span className="font-mono text-sm font-medium text-fg">
                      Rev {r.revision_label}
                    </span>
                    <LifecycleBadge state={r.lifecycle_state} />
                  </span>
                  <span className="truncate text-xs text-fg-muted">{r.change_summary ?? "—"}</span>
                  <span className="text-2xs text-fg-subtle">{formatDateTime(r.created_at)}</span>
                </Link>
              </li>
            ))}
          </ul>
          <NewRevisionForm componentRef={c.identifier} />
        </Card>

        <div className="grid gap-4">
          {selected ? <RevisionPanel revision={selected} componentRef={c.identifier} /> : null}
          {selected && c.kind === "ASSEMBLY" ? (
            <BomPanel revision={selected} componentRef={c.identifier} />
          ) : null}
          <WhereUsedPanel componentRef={c.identifier} />
        </div>
      </div>
    </div>
  );
}

function RevisionPanel({
  revision,
  componentRef,
}: {
  revision: RevisionRead;
  componentRef: string;
}) {
  const [editing, setEditing] = useState(false);
  const transition = useTransitionRevision(revision.id);
  const [error, setError] = useState<string | null>(null);

  const dims = revision.dimensions ?? {};
  const tols = revision.tolerances ?? {};
  const dimensionKeys = Array.from(new Set([...Object.keys(dims), ...Object.keys(tols)]));

  return (
    <Card>
      <CardHeader
        eyebrow={`${componentRef} · revision ${revision.revision_number}`}
        title={
          <span className="inline-flex items-center gap-2">
            Rev {revision.revision_label}
            <LifecycleBadge state={revision.lifecycle_state} />
            <FrozenBadge frozen={revision.is_frozen} />
          </span>
        }
        actions={
          <>
            {revision.allowed_transitions.map((target) => (
              <Button
                key={target}
                size="sm"
                variant={target === "OBSOLETE" ? "danger" : "secondary"}
                disabled={transition.isPending}
                onClick={() => {
                  setError(null);
                  transition.mutate(target, { onError: (err) => setError(describeError(err)) });
                }}
              >
                → {titleCase(target)}
              </Button>
            ))}
            {!revision.is_frozen ? (
              <Button size="sm" variant="primary" onClick={() => setEditing((v) => !v)}>
                {editing ? "Close editor" : "Edit content"}
              </Button>
            ) : null}
          </>
        }
      >
        {revision.change_summary ? (
          <p className="mt-1 text-xs text-fg-muted">{revision.change_summary}</p>
        ) : null}
      </CardHeader>
      <CardContent className="grid gap-4">
        <FormError message={error} />
        {revision.is_frozen ? (
          <p className="rounded border border-border bg-bg-elevated px-3 py-2 text-xs text-fg-muted">
            Frozen {formatDateTime(revision.frozen_at)}. Engineering content and BOM lines are
            immutable; create a new revision to change anything.
            {revision.superseded_by_id ? " This revision has been superseded." : ""}
          </p>
        ) : null}
        {editing && !revision.is_frozen ? (
          <RevisionEditor revision={revision} onDone={() => setEditing(false)} />
        ) : (
          <>
            <KV
              columns={3}
              items={[
                { label: "Material", value: revision.material },
                { label: "Heat treatment", value: revision.heat_treatment },
                { label: "Finish", value: revision.finish },
                { label: "Manufacturing method", value: revision.manufacturing_method },
                {
                  label: "Mass",
                  value: revision.mass_g ? formatNumber(revision.mass_g, "g") : null,
                },
                { label: "Supplier", value: revision.supplier_note },
                { label: "Description", value: revision.description, span: 2 },
                { label: "Inspection requirements", value: revision.inspection_requirements },
                { label: "Notes", value: revision.notes, span: 2 },
              ]}
            />
            {dimensionKeys.length > 0 ? (
              <div>
                <div className="label mb-1">Dimensions and tolerances</div>
                <Table>
                  <THead>
                    <TR>
                      <TH>Feature</TH>
                      <TH align="right">Nominal</TH>
                      <TH align="right">Tolerance</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {dimensionKeys.map((k) => (
                      <TR key={k}>
                        <TD mono>{k}</TD>
                        <TD align="right" mono>
                          {displayValue(dims[k])}
                        </TD>
                        <TD align="right" mono className="text-fg-muted">
                          {displayValue(tols[k])}
                        </TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              </div>
            ) : null}
            <KV
              columns={3}
              className="border-t border-border pt-3"
              items={[
                {
                  label: "Created",
                  value: `${formatDateTime(revision.created_at)} · ${revision.created_by}`,
                },
                {
                  label: "Updated",
                  value: `${formatDateTime(revision.updated_at)} · ${revision.updated_by}`,
                },
                { label: "Revision id", value: revision.id, mono: true },
              ]}
            />
          </>
        )}
      </CardContent>
    </Card>
  );
}

function optional(value: FormDataEntryValue | null): string | null {
  const text = typeof value === "string" ? value.trim() : "";
  return text === "" ? null : text;
}

function parseJsonObject(value: FormDataEntryValue | null): Record<string, unknown> | null {
  const text = optional(value);
  if (!text) return null;
  const parsed: unknown = JSON.parse(text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error('Dimensions and tolerances must be JSON objects, e.g. {"diameter_mm": 25.6}');
  }
  return parsed as Record<string, unknown>;
}

function RevisionEditor({ revision, onDone }: { revision: RevisionRead; onDone: () => void }) {
  const update = useUpdateRevision(revision.id);
  const [error, setError] = useState<string | null>(null);

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const fd = new FormData(event.currentTarget);
    let dimensions: Record<string, unknown> | null;
    let tolerances: Record<string, unknown> | null;
    try {
      dimensions = parseJsonObject(fd.get("dimensions"));
      tolerances = parseJsonObject(fd.get("tolerances"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid JSON");
      return;
    }
    const mass = optional(fd.get("mass_g"));
    update.mutate(
      {
        change_summary: optional(fd.get("change_summary")),
        description: optional(fd.get("description")),
        material: optional(fd.get("material")),
        heat_treatment: optional(fd.get("heat_treatment")),
        finish: optional(fd.get("finish")),
        manufacturing_method: optional(fd.get("manufacturing_method")),
        dimensions,
        tolerances,
        mass_g: mass,
        supplier_note: optional(fd.get("supplier_note")),
        inspection_requirements: optional(fd.get("inspection_requirements")),
        notes: optional(fd.get("notes")),
      },
      { onSuccess: onDone, onError: (err) => setError(describeError(err)) },
    );
  }

  return (
    <form onSubmit={onSubmit} className="grid gap-3 sm:grid-cols-2">
      <Field label="Change summary" htmlFor="e-change_summary" className="sm:col-span-2">
        <Input
          id="e-change_summary"
          name="change_summary"
          defaultValue={revision.change_summary ?? ""}
        />
      </Field>
      <Field label="Material" htmlFor="e-material">
        <Input id="e-material" name="material" defaultValue={revision.material ?? ""} />
      </Field>
      <Field label="Heat treatment" htmlFor="e-heat">
        <Input id="e-heat" name="heat_treatment" defaultValue={revision.heat_treatment ?? ""} />
      </Field>
      <Field label="Finish" htmlFor="e-finish">
        <Input id="e-finish" name="finish" defaultValue={revision.finish ?? ""} />
      </Field>
      <Field label="Manufacturing method" htmlFor="e-method">
        <Input
          id="e-method"
          name="manufacturing_method"
          defaultValue={revision.manufacturing_method ?? ""}
        />
      </Field>
      <Field label="Mass (g)" htmlFor="e-mass">
        <Input
          id="e-mass"
          name="mass_g"
          inputMode="decimal"
          defaultValue={revision.mass_g ?? ""}
          className="font-mono"
        />
      </Field>
      <Field label="Supplier note" htmlFor="e-supplier">
        <Input id="e-supplier" name="supplier_note" defaultValue={revision.supplier_note ?? ""} />
      </Field>
      <Field
        label="Dimensions (JSON)"
        htmlFor="e-dims"
        hint='{"diameter_mm": 25.6, "thickness_mm": 1.2}'
      >
        <Textarea
          id="e-dims"
          name="dimensions"
          className="font-mono text-xs"
          defaultValue={revision.dimensions ? JSON.stringify(revision.dimensions, null, 2) : ""}
        />
      </Field>
      <Field label="Tolerances (JSON)" htmlFor="e-tols" hint='{"diameter_mm": "±0.01"}'>
        <Textarea
          id="e-tols"
          name="tolerances"
          className="font-mono text-xs"
          defaultValue={revision.tolerances ? JSON.stringify(revision.tolerances, null, 2) : ""}
        />
      </Field>
      <Field label="Description" htmlFor="e-desc" className="sm:col-span-2">
        <Textarea id="e-desc" name="description" defaultValue={revision.description ?? ""} />
      </Field>
      <Field label="Inspection requirements" htmlFor="e-insp" className="sm:col-span-2">
        <Textarea
          id="e-insp"
          name="inspection_requirements"
          defaultValue={revision.inspection_requirements ?? ""}
        />
      </Field>
      <Field label="Notes" htmlFor="e-notes" className="sm:col-span-2">
        <Textarea id="e-notes" name="notes" defaultValue={revision.notes ?? ""} />
      </Field>
      <div className="sm:col-span-2">
        <FormError message={error} />
      </div>
      <div className="flex gap-2 sm:col-span-2">
        <Button type="submit" variant="primary" disabled={update.isPending}>
          {update.isPending ? "Saving…" : "Save"}
        </Button>
        <Button variant="ghost" onClick={onDone}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

function NewRevisionForm({ componentRef }: { componentRef: string }) {
  const create = useCreateRevision(componentRef);
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const form = event.currentTarget;
    const summary = formText(new FormData(form), "change_summary");
    if (!summary) {
      setError("Say why this revision exists.");
      return;
    }
    create.mutate(
      { change_summary: summary, copy_bom: true },
      {
        onSuccess: (rev) => {
          form.reset();
          navigate(`/components/${componentRef}/revisions/${rev.revision_label}`);
        },
        onError: (err) => setError(describeError(err)),
      },
    );
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-2 border-t border-border px-4 py-3">
      <div className="label">New revision</div>
      <Input
        name="change_summary"
        placeholder="Why does this revision exist?"
        aria-label="Change summary"
      />
      <FormError message={error} />
      <Button type="submit" size="sm" disabled={create.isPending}>
        {create.isPending ? "Creating…" : "Create from latest"}
      </Button>
      <p className="text-2xs text-fg-subtle">
        Copies content and BOM lines from the latest revision. Starts in Concept.
      </p>
    </form>
  );
}

function BomPanel({ revision, componentRef }: { revision: RevisionRead; componentRef: string }) {
  const bom = useBom(revision.id, "latest");
  return (
    <Card>
      <CardHeader
        eyebrow="Design BOM · latest resolution"
        title={`Rev ${revision.revision_label} contents`}
        actions={
          <Link
            to={`/boms/${componentRef}?rev=${revision.revision_label}`}
            className="text-xs text-fg-muted hover:text-fg hover:underline"
          >
            Edit in BOM explorer
          </Link>
        }
      />
      {bom.isLoading ? (
        <LoadingRows />
      ) : bom.isError ? (
        <CardContent>
          <ErrorNotice error={bom.error} />
        </CardContent>
      ) : bom.data ? (
        <BomTree tree={bom.data} />
      ) : null}
    </Card>
  );
}

function WhereUsedPanel({ componentRef }: { componentRef: string }) {
  const used = useWhereUsed(componentRef);
  return (
    <Card>
      <CardHeader eyebrow="Traceability" title="Where used" />
      {used.isLoading ? (
        <LoadingRows rows={2} />
      ) : used.data && used.data.length > 0 ? (
        <Table>
          <THead>
            <TR>
              <TH>Parent assembly</TH>
              <TH>Name</TH>
              <TH className="w-40">Parent revision</TH>
              <TH className="w-16" align="right">
                Find
              </TH>
              <TH className="w-16" align="right">
                Qty
              </TH>
              <TH className="w-40">Pinned to</TH>
            </TR>
          </THead>
          <TBody>
            {used.data.map((row) => (
              <TR key={row.line.id}>
                <TD>
                  <Identifier
                    value={row.parent_component.identifier}
                    to={`/components/${row.parent_component.identifier}`}
                  />
                </TD>
                <TD>{row.parent_component.name}</TD>
                <TD>
                  <span className="inline-flex items-center gap-1.5">
                    <Identifier
                      value={`Rev ${row.parent_revision.revision_label}`}
                      to={`/components/${row.parent_component.identifier}/revisions/${row.parent_revision.revision_label}`}
                    />
                    <LifecycleBadge state={row.parent_revision.lifecycle_state} />
                  </span>
                </TD>
                <TD align="right" mono>
                  {row.line.find_number}
                </TD>
                <TD align="right" mono>
                  {formatNumber(row.line.quantity)}
                </TD>
                <TD mono className="text-fg-muted">
                  {row.line.child_revision
                    ? `Rev ${row.line.child_revision.revision_label}`
                    : "floating"}
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      ) : (
        <CardContent>
          <EmptyState
            title="Not used in any assembly"
            description="This component does not appear on any BOM line."
            className="py-6"
          />
        </CardContent>
      )}
    </Card>
  );
}
