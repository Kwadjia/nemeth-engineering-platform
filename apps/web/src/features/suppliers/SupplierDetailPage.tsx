import { SUPPLIER_KINDS, type SupplierKind, type SupplierRead } from "@nemeth/domain-types";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Identifier, LifecycleBadge, PlaceholderBadge } from "@/components/domain/badges";
import { SupplierKindBadge } from "@/components/domain/changeBadges";
import { InstanceStatusBadge } from "@/components/domain/prototypeBadges";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Field, FormError, Input, Select, Textarea } from "@/components/ui/form";
import { EmptyState, ErrorNotice, KV, LoadingRows, PageHeader } from "@/components/ui/layout";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { describeError } from "@/lib/api";
import { formatDateTime, formOptional, formText, titleCase } from "@/lib/format";
import {
  useSupplier,
  useSupplierPartInstances,
  useSupplierRevisions,
  useUpdateSupplier,
} from "@/lib/supplierQueries";

export function SupplierDetailPage() {
  const { ref = "" } = useParams();
  const supplier = useSupplier(ref);
  const revisions = useSupplierRevisions(ref);
  const instances = useSupplierPartInstances(ref);
  const [editing, setEditing] = useState(false);

  if (supplier.isLoading) return <LoadingRows />;
  if (supplier.isError) return <ErrorNotice error={supplier.error} />;
  if (!supplier.data) return null;
  const s = supplier.data;

  return (
    <div>
      <PageHeader
        eyebrow={
          <span>
            <Link to="/suppliers" className="hover:underline">
              Suppliers
            </Link>{" "}
            / {s.identifier}
          </span>
        }
        title={
          <>
            <Identifier value={s.identifier} className="text-xl" />
            <span>{s.name}</span>
          </>
        }
        description={s.capabilities}
        meta={
          <>
            <SupplierKindBadge kind={s.kind} />
            {s.is_active ? <Badge tone="ok">Active</Badge> : <Badge tone="neutral">Inactive</Badge>}
            <PlaceholderBadge show={s.is_placeholder} />
          </>
        }
        actions={
          <Button variant="primary" onClick={() => setEditing((v) => !v)}>
            {editing ? "Close editor" : "Edit"}
          </Button>
        }
      />
      <div className="grid gap-4 xl:grid-cols-3">
        <div className="grid gap-4 xl:col-span-2">
          {editing ? <SupplierEditor supplier={s} onDone={() => setEditing(false)} /> : null}
          <Card>
            <CardHeader eyebrow="Design intent" title="Default source for revisions" />
            {revisions.isLoading ? (
              <LoadingRows rows={2} />
            ) : revisions.data && revisions.data.length > 0 ? (
              <Table>
                <THead>
                  <TR>
                    <TH className="w-44">Revision</TH>
                    <TH>Component</TH>
                    <TH className="w-28">State</TH>
                    <TH>Method</TH>
                  </TR>
                </THead>
                <TBody>
                  {revisions.data.map((r) => (
                    <TR key={r.id}>
                      <TD>
                        <Identifier
                          value={r.display_identifier}
                          to={`/components/${r.component.identifier}/revisions/${r.revision_label}`}
                        />
                      </TD>
                      <TD>{r.component.name}</TD>
                      <TD>
                        <LifecycleBadge state={r.lifecycle_state} />
                      </TD>
                      <TD className="text-fg-muted">{r.manufacturing_method ?? "—"}</TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            ) : (
              <CardContent>
                <EmptyState
                  title="No revisions name this supplier"
                  description="Set it on a revision's engineering content."
                  className="py-6"
                />
              </CardContent>
            )}
          </Card>
          <Card>
            <CardHeader eyebrow="Physical fact" title="Parts sourced" />
            {instances.isLoading ? (
              <LoadingRows rows={2} />
            ) : instances.data && instances.data.length > 0 ? (
              <Table>
                <THead>
                  <TR>
                    <TH className="w-24">Part</TH>
                    <TH className="w-32">Component</TH>
                    <TH>Name</TH>
                    <TH className="w-20">Rev</TH>
                    <TH className="w-24">Status</TH>
                    <TH className="w-28">Lot</TH>
                    <TH className="w-28">In</TH>
                  </TR>
                </THead>
                <TBody>
                  {instances.data.map((i) => (
                    <TR key={i.id}>
                      <TD>
                        <Identifier value={i.identifier} to={`/part-instances?q=${i.identifier}`} />
                      </TD>
                      <TD>
                        <Identifier
                          value={i.component.identifier}
                          to={`/components/${i.component.identifier}`}
                        />
                      </TD>
                      <TD>{i.component.name}</TD>
                      <TD mono>Rev {i.revision.revision_label}</TD>
                      <TD>
                        <InstanceStatusBadge status={i.status} />
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
                        ) : i.current_watch ? (
                          <Identifier
                            value={i.current_watch.identifier}
                            to={`/watches/${i.current_watch.identifier}`}
                          />
                        ) : (
                          <span className="text-fg-subtle">—</span>
                        )}
                      </TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            ) : (
              <CardContent>
                <EmptyState title="No parts recorded from this supplier" className="py-6" />
              </CardContent>
            )}
          </Card>
        </div>
        <Card className="self-start">
          <CardHeader eyebrow="Record" title="Details" />
          <CardContent>
            <KV
              columns={1}
              items={[
                { label: "Contact", value: s.contact_name },
                { label: "Email", value: s.email },
                { label: "Phone", value: s.phone },
                { label: "Website", value: s.website },
                { label: "Address", value: s.address },
                { label: "Country", value: s.country },
                { label: "Notes", value: s.notes },
                { label: "Created", value: `${formatDateTime(s.created_at)} · ${s.created_by}` },
                { label: "Internal id", value: s.id, mono: true },
              ]}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function SupplierEditor({ supplier, onDone }: { supplier: SupplierRead; onDone: () => void }) {
  const update = useUpdateSupplier(supplier.identifier);
  const [error, setError] = useState<string | null>(null);

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const fd = new FormData(event.currentTarget);
    update.mutate(
      {
        name: formText(fd, "name"),
        kind: formText(fd, "kind") as SupplierKind,
        capabilities: formOptional(fd, "capabilities"),
        contact_name: formOptional(fd, "contact_name"),
        email: formOptional(fd, "email"),
        phone: formOptional(fd, "phone"),
        website: formOptional(fd, "website"),
        address: formOptional(fd, "address"),
        country: formOptional(fd, "country"),
        notes: formOptional(fd, "notes"),
        is_active: fd.get("is_active") === "on",
      },
      { onSuccess: onDone, onError: (err) => setError(describeError(err)) },
    );
  }

  return (
    <Card>
      <CardHeader eyebrow="Editing" title="Supplier" />
      <CardContent>
        <form onSubmit={onSubmit} className="grid gap-3 sm:grid-cols-4">
          <Field label="Name" htmlFor="e-name" className="sm:col-span-2">
            <Input id="e-name" name="name" defaultValue={supplier.name} required />
          </Field>
          <Field label="Kind" htmlFor="e-kind">
            <Select id="e-kind" name="kind" defaultValue={supplier.kind}>
              {SUPPLIER_KINDS.map((k) => (
                <option key={k} value={k}>
                  {titleCase(k)}
                </option>
              ))}
            </Select>
          </Field>
          <label className="flex items-end gap-2 pb-2 text-sm text-fg-muted">
            <input type="checkbox" name="is_active" defaultChecked={supplier.is_active} /> Active
          </label>
          <Field label="Capabilities" htmlFor="e-cap" className="sm:col-span-4">
            <Textarea id="e-cap" name="capabilities" defaultValue={supplier.capabilities ?? ""} />
          </Field>
          <Field label="Contact" htmlFor="e-contact">
            <Input id="e-contact" name="contact_name" defaultValue={supplier.contact_name ?? ""} />
          </Field>
          <Field label="Email" htmlFor="e-email">
            <Input id="e-email" name="email" defaultValue={supplier.email ?? ""} />
          </Field>
          <Field label="Phone" htmlFor="e-phone">
            <Input id="e-phone" name="phone" defaultValue={supplier.phone ?? ""} />
          </Field>
          <Field label="Website" htmlFor="e-web">
            <Input id="e-web" name="website" defaultValue={supplier.website ?? ""} />
          </Field>
          <Field label="Address" htmlFor="e-address" className="sm:col-span-3">
            <Textarea
              id="e-address"
              name="address"
              className="min-h-[3rem]"
              defaultValue={supplier.address ?? ""}
            />
          </Field>
          <Field label="Country" htmlFor="e-country">
            <Input id="e-country" name="country" defaultValue={supplier.country ?? ""} />
          </Field>
          <Field label="Notes" htmlFor="e-notes" className="sm:col-span-4">
            <Textarea id="e-notes" name="notes" defaultValue={supplier.notes ?? ""} />
          </Field>
          <div className="sm:col-span-4">
            <FormError message={error} />
          </div>
          <div className="flex gap-2 sm:col-span-4">
            <Button type="submit" variant="primary" disabled={update.isPending}>
              {update.isPending ? "Saving…" : "Save"}
            </Button>
            <Button variant="ghost" onClick={onDone}>
              Cancel
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
