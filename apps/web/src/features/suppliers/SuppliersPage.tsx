import { SUPPLIER_KINDS, type SupplierKind } from "@nemeth/domain-types";
import { Plus, Truck } from "lucide-react";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { Identifier, PlaceholderBadge } from "@/components/domain/badges";
import { SupplierKindBadge } from "@/components/domain/changeBadges";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Field, FormError, Input, Select, Textarea } from "@/components/ui/form";
import { EmptyState, ErrorNotice, LoadingRows, PageHeader } from "@/components/ui/layout";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { describeError } from "@/lib/api";
import { formOptional, formText, titleCase } from "@/lib/format";
import { useCreateSupplier, useSuppliers } from "@/lib/supplierQueries";

export function SuppliersPage() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const suppliers = useSuppliers(q);
  const navigate = useNavigate();
  const [creating, setCreating] = useState(false);

  return (
    <div>
      <PageHeader
        eyebrow="Manufacturing & quality"
        title="Suppliers"
        description="Who makes or supplies what. A revision names its default source; each physical part records where it actually came from."
        actions={
          <Button variant="primary" onClick={() => setCreating((v) => !v)}>
            <Plus className="h-3.5 w-3.5" /> New supplier
          </Button>
        }
      />
      {creating ? <NewSupplierForm onDone={() => setCreating(false)} /> : null}
      <div className="mb-3 flex items-center gap-2">
        <Input
          placeholder="Search name, identifier or capabilities"
          value={q}
          onChange={(e) => {
            const next = new URLSearchParams(params);
            if (e.target.value) next.set("q", e.target.value);
            else next.delete("q");
            setParams(next, { replace: true });
          }}
          className="w-80"
          aria-label="Search"
        />
        {suppliers.data ? (
          <span className="ml-auto font-mono text-xs text-fg-subtle">
            {suppliers.data.total} suppliers
          </span>
        ) : null}
      </div>
      {suppliers.isError ? <ErrorNotice error={suppliers.error} /> : null}
      <Card>
        {suppliers.isLoading ? (
          <LoadingRows />
        ) : suppliers.data && suppliers.data.items.length > 0 ? (
          <Table>
            <THead>
              <TR>
                <TH className="w-24">Supplier</TH>
                <TH>Name</TH>
                <TH className="w-36">Kind</TH>
                <TH>Capabilities</TH>
                <TH className="w-28">Country</TH>
                <TH className="w-20">Active</TH>
              </TR>
            </THead>
            <TBody>
              {suppliers.data.items.map((s) => (
                <TR key={s.id} interactive onClick={() => navigate(`/suppliers/${s.identifier}`)}>
                  <TD>
                    <Identifier value={s.identifier} />
                  </TD>
                  <TD className="font-medium">
                    <span className="inline-flex items-center gap-2">
                      {s.name}
                      <PlaceholderBadge show={s.is_placeholder} />
                    </span>
                  </TD>
                  <TD>
                    <SupplierKindBadge kind={s.kind} />
                  </TD>
                  <TD className="max-w-md truncate text-fg-muted">{s.capabilities ?? "—"}</TD>
                  <TD className="text-fg-muted">{s.country ?? "—"}</TD>
                  <TD>
                    {s.is_active ? (
                      <Badge tone="ok">Active</Badge>
                    ) : (
                      <Badge tone="neutral">Inactive</Badge>
                    )}
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        ) : (
          <EmptyState
            icon={Truck}
            title="No suppliers"
            description="Add the shops, platers and material sources you work with."
            className="m-4"
          />
        )}
      </Card>
    </div>
  );
}

function NewSupplierForm({ onDone }: { onDone: () => void }) {
  const create = useCreateSupplier();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const fd = new FormData(event.currentTarget);
    create.mutate(
      {
        name: formText(fd, "name"),
        kind: (formText(fd, "kind") || "OTHER") as SupplierKind,
        capabilities: formOptional(fd, "capabilities"),
        contact_name: formOptional(fd, "contact_name"),
        email: formOptional(fd, "email"),
        phone: formOptional(fd, "phone"),
        website: formOptional(fd, "website"),
        country: formOptional(fd, "country"),
        notes: formOptional(fd, "notes"),
      },
      {
        onSuccess: (s) => {
          onDone();
          navigate(`/suppliers/${s.identifier}`);
        },
        onError: (err) => setError(describeError(err)),
      },
    );
  }

  return (
    <Card className="mb-4">
      <CardHeader eyebrow="New" title="Supplier" />
      <CardContent>
        <form onSubmit={onSubmit} className="grid gap-3 sm:grid-cols-4">
          <Field label="Name" htmlFor="s-name" className="sm:col-span-2">
            <Input id="s-name" name="name" required placeholder="Detroit Precision Machining" />
          </Field>
          <Field label="Kind" htmlFor="s-kind">
            <Select id="s-kind" name="kind" defaultValue="MACHINE_SHOP">
              {SUPPLIER_KINDS.map((k) => (
                <option key={k} value={k}>
                  {titleCase(k)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Country" htmlFor="s-country">
            <Input id="s-country" name="country" placeholder="USA" />
          </Field>
          <Field label="Capabilities" htmlFor="s-cap" className="sm:col-span-4">
            <Textarea
              id="s-cap"
              name="capabilities"
              className="min-h-[3rem]"
              placeholder="5-axis milling, wire EDM, Swiss-type turning"
            />
          </Field>
          <Field label="Contact" htmlFor="s-contact">
            <Input id="s-contact" name="contact_name" />
          </Field>
          <Field label="Email" htmlFor="s-email">
            <Input id="s-email" name="email" type="email" />
          </Field>
          <Field label="Phone" htmlFor="s-phone">
            <Input id="s-phone" name="phone" />
          </Field>
          <Field label="Website" htmlFor="s-web">
            <Input id="s-web" name="website" />
          </Field>
          <Field label="Notes" htmlFor="s-notes" className="sm:col-span-4">
            <Textarea id="s-notes" name="notes" className="min-h-[3rem]" />
          </Field>
          <div className="sm:col-span-4">
            <FormError message={error} />
          </div>
          <div className="flex gap-2 sm:col-span-4">
            <Button type="submit" variant="primary" disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create supplier"}
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
