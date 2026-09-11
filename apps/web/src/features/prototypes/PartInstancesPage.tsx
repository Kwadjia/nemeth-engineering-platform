import {
  PART_INSTANCE_STATUSES,
  PART_SOURCES,
  type PartInstanceStatus,
  type PartSource,
} from "@nemeth/domain-types";
import { Box, Plus } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { Identifier, LifecycleBadge, PlaceholderBadge } from "@/components/domain/badges";
import { InstanceStatusBadge, SourceBadge } from "@/components/domain/prototypeBadges";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Field, FormError, Input, Select, Textarea } from "@/components/ui/form";
import { EmptyState, ErrorNotice, LoadingRows, PageHeader } from "@/components/ui/layout";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { describeError } from "@/lib/api";
import { formatDate, formOptional, formText, titleCase } from "@/lib/format";
import { useCreatePartInstances, usePartInstances } from "@/lib/prototypeQueries";
import { useRevisions } from "@/lib/queries";

export function PartInstancesPage() {
  const [params, setParams] = useSearchParams();
  const [creating, setCreating] = useState(false);
  const filters = {
    q: params.get("q") ?? "",
    status: (params.get("status") as PartInstanceStatus | null) ?? undefined,
  };
  const instances = usePartInstances(filters);

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  }

  return (
    <div>
      <PageHeader
        eyebrow="Development"
        title="Part instances"
        description="Physical parts, each recorded against the exact frozen revision it was made or bought to. Install them into prototypes through build records."
        actions={
          <Button variant="primary" onClick={() => setCreating((v) => !v)}>
            <Plus className="h-3.5 w-3.5" /> Record parts
          </Button>
        }
      />
      {creating ? <NewInstancesForm onDone={() => setCreating(false)} /> : null}

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Input
          placeholder="Search part, serial or component"
          value={filters.q}
          onChange={(e) => setFilter("q", e.target.value)}
          className="w-72"
          aria-label="Search"
        />
        <Select
          value={filters.status ?? ""}
          onChange={(e) => setFilter("status", e.target.value)}
          className="w-40"
          aria-label="Status"
        >
          <option value="">Any status</option>
          {PART_INSTANCE_STATUSES.map((s) => (
            <option key={s} value={s}>
              {titleCase(s)}
            </option>
          ))}
        </Select>
        {instances.data ? (
          <span className="ml-auto font-mono text-xs text-fg-subtle">
            {instances.data.total} parts
          </span>
        ) : null}
      </div>

      {instances.isError ? <ErrorNotice error={instances.error} /> : null}
      <Card>
        {instances.isLoading ? (
          <LoadingRows rows={6} />
        ) : instances.data && instances.data.items.length > 0 ? (
          <Table>
            <THead>
              <TR>
                <TH className="w-24">Part</TH>
                <TH className="w-32">Component</TH>
                <TH>Name</TH>
                <TH className="w-40">Revision</TH>
                <TH className="w-24">Status</TH>
                <TH className="w-24">Source</TH>
                <TH className="w-28">Serial</TH>
                <TH className="w-28">Lot</TH>
                <TH className="w-28">In</TH>
                <TH className="w-28">Recorded</TH>
              </TR>
            </THead>
            <TBody>
              {instances.data.items.map((i) => (
                <TR key={i.id}>
                  <TD>
                    <span className="inline-flex items-center gap-2">
                      <Identifier value={i.identifier} />
                      <PlaceholderBadge show={i.is_placeholder} />
                    </span>
                  </TD>
                  <TD>
                    <Identifier
                      value={i.component.identifier}
                      to={`/components/${i.component.identifier}`}
                    />
                  </TD>
                  <TD>{i.component.name}</TD>
                  <TD>
                    <span className="inline-flex items-center gap-1.5">
                      <Identifier
                        value={`Rev ${i.revision.revision_label}`}
                        to={`/components/${i.component.identifier}/revisions/${i.revision.revision_label}`}
                      />
                      <LifecycleBadge state={i.revision.lifecycle_state} />
                    </span>
                  </TD>
                  <TD>
                    <InstanceStatusBadge status={i.status} />
                  </TD>
                  <TD>
                    <SourceBadge source={i.source} />
                  </TD>
                  <TD mono className="text-fg-muted">
                    {i.serial_number ?? "—"}
                  </TD>
                  <TD mono className="text-fg-muted">
                    {i.lot ?? "—"}
                  </TD>
                  <TD>
                    {i.current_prototype ? (
                      <Identifier
                        value={i.current_prototype.identifier}
                        to={`/prototypes/${i.current_prototype.identifier}`}
                      />
                    ) : (
                      <span className="text-fg-subtle">—</span>
                    )}
                  </TD>
                  <TD className="text-fg-subtle">{formatDate(i.created_at)}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        ) : (
          <EmptyState
            icon={Box}
            title="No part instances"
            description="Record physical parts against a frozen component revision to start building."
            className="m-4"
          />
        )}
      </Card>
    </div>
  );
}

function NewInstancesForm({ onDone }: { onDone: () => void }) {
  const create = useCreatePartInstances();
  const [componentRef, setComponentRef] = useState("");
  const [lookup, setLookup] = useState("");
  const revisions = useRevisions(lookup);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  const frozen = (revisions.data ?? []).filter((r) => r.is_frozen);
  const unfrozen = (revisions.data ?? []).filter((r) => !r.is_frozen);

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setDone(null);
    const form = event.currentTarget;
    const fd = new FormData(form);
    const revisionId = formText(fd, "revision_id");
    if (!revisionId) {
      setError("Choose a frozen revision.");
      return;
    }
    create.mutate(
      {
        component_revision_id: revisionId,
        quantity: Number(formText(fd, "quantity") || "1"),
        serial_number: formOptional(fd, "serial_number"),
        lot: formOptional(fd, "lot"),
        source: (formText(fd, "source") || "IN_HOUSE") as PartSource,
        material_lot: formOptional(fd, "material_lot"),
        heat_treatment_lot: formOptional(fd, "heat_treatment_lot"),
        supplier_note: formOptional(fd, "supplier_note"),
        notes: formOptional(fd, "notes"),
      },
      {
        onSuccess: (created) => {
          setDone(`Recorded ${created.map((c) => c.identifier).join(", ")}`);
          form.reset();
        },
        onError: (err) => setError(describeError(err)),
      },
    );
  }

  return (
    <Card className="mb-4">
      <CardHeader eyebrow="New" title="Record physical parts" />
      <CardContent>
        <form onSubmit={onSubmit} className="grid gap-3 sm:grid-cols-4">
          <Field label="Component identifier" htmlFor="i-component" className="sm:col-span-2">
            <div className="flex gap-2">
              <Input
                id="i-component"
                value={componentRef}
                onChange={(e) => setComponentRef(e.target.value)}
                placeholder="N1-MVT-011"
                className="font-mono uppercase"
              />
              <Button onClick={() => setLookup(componentRef.trim().toUpperCase())}>
                Load revisions
              </Button>
            </div>
          </Field>
          <Field
            label="Frozen revision"
            htmlFor="i-revision"
            className="sm:col-span-2"
            hint={
              revisions.isError
                ? describeError(revisions.error)
                : unfrozen.length > 0 && frozen.length === 0
                  ? `Only ${unfrozen.map((r) => `Rev ${r.revision_label} (${titleCase(r.lifecycle_state)})`).join(", ")} exist; transition one to Prototype first.`
                  : "Physical parts only exist against frozen revisions."
            }
          >
            <Select id="i-revision" name="revision_id" defaultValue="">
              <option value="">
                {lookup
                  ? frozen.length
                    ? "Choose…"
                    : "No frozen revisions"
                  : "Load a component first"}
              </option>
              {frozen.map((r) => (
                <option key={r.id} value={r.id}>
                  Rev {r.revision_label} · {titleCase(r.lifecycle_state)} ·{" "}
                  {r.material ?? "material not set"}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Quantity" htmlFor="i-qty" hint="one instance per physical part">
            <Input
              id="i-qty"
              name="quantity"
              type="number"
              min={1}
              max={100}
              defaultValue={1}
              className="font-mono"
            />
          </Field>
          <Field label="Source" htmlFor="i-source">
            <Select id="i-source" name="source" defaultValue="IN_HOUSE">
              {PART_SOURCES.map((s) => (
                <option key={s} value={s}>
                  {titleCase(s)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Serial number" htmlFor="i-serial" hint="single part only">
            <Input id="i-serial" name="serial_number" className="font-mono" />
          </Field>
          <Field label="Lot" htmlFor="i-lot">
            <Input id="i-lot" name="lot" className="font-mono" />
          </Field>
          <Field label="Material lot" htmlFor="i-mlot">
            <Input id="i-mlot" name="material_lot" className="font-mono" />
          </Field>
          <Field label="Heat treatment lot" htmlFor="i-htlot">
            <Input id="i-htlot" name="heat_treatment_lot" className="font-mono" />
          </Field>
          <Field label="Supplier note" htmlFor="i-supplier" className="sm:col-span-2">
            <Input id="i-supplier" name="supplier_note" />
          </Field>
          <Field label="Notes" htmlFor="i-notes" className="sm:col-span-4">
            <Textarea id="i-notes" name="notes" className="min-h-[3rem]" />
          </Field>
          <div className="sm:col-span-4">
            <FormError message={error} />
            {done ? <p className="text-xs text-ok">{done}</p> : null}
          </div>
          <div className="flex gap-2 sm:col-span-4">
            <Button type="submit" variant="primary" disabled={create.isPending}>
              {create.isPending ? "Recording…" : "Record parts"}
            </Button>
            <Button variant="ghost" onClick={onDone}>
              Close
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
