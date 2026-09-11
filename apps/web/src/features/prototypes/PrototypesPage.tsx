import { Layers, Plus } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Identifier, PlaceholderBadge } from "@/components/domain/badges";
import { PrototypeStatusBadge } from "@/components/domain/prototypeBadges";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Field, FormError, Input, Textarea } from "@/components/ui/form";
import { EmptyState, ErrorNotice, LoadingRows, PageHeader } from "@/components/ui/layout";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { describeError } from "@/lib/api";
import { formatDate, formOptional, formText } from "@/lib/format";
import { useCreatePrototype, usePrototypes } from "@/lib/prototypeQueries";

export function PrototypesPage() {
  const prototypes = usePrototypes();
  const navigate = useNavigate();
  const [creating, setCreating] = useState(false);

  return (
    <div>
      <PageHeader
        eyebrow="Development"
        title="Prototypes"
        description="Physical development builds. Each prototype carries an append-only build log and a derived configuration: the exact revision of every part inside it right now."
        actions={
          <Button variant="primary" onClick={() => setCreating((v) => !v)}>
            <Plus className="h-3.5 w-3.5" /> New prototype
          </Button>
        }
      />
      {creating ? <NewPrototypeForm onDone={() => setCreating(false)} /> : null}
      {prototypes.isError ? <ErrorNotice error={prototypes.error} /> : null}
      <Card>
        {prototypes.isLoading ? (
          <LoadingRows />
        ) : prototypes.data && prototypes.data.items.length > 0 ? (
          <Table>
            <THead>
              <TR>
                <TH className="w-28">Prototype</TH>
                <TH>Name</TH>
                <TH className="w-24">Status</TH>
                <TH className="w-24">Model</TH>
                <TH className="w-24">Caliber</TH>
                <TH className="w-20" align="right">
                  Parts
                </TH>
                <TH className="w-20" align="right">
                  Builds
                </TH>
                <TH className="w-28">Started</TH>
              </TR>
            </THead>
            <TBody>
              {prototypes.data.items.map((p) => (
                <TR key={p.id} interactive onClick={() => navigate(`/prototypes/${p.identifier}`)}>
                  <TD>
                    <Identifier value={p.identifier} />
                  </TD>
                  <TD className="font-medium">
                    <span className="inline-flex items-center gap-2">
                      {p.name}
                      <PlaceholderBadge show={p.is_placeholder} />
                    </span>
                  </TD>
                  <TD>
                    <PrototypeStatusBadge status={p.status} />
                  </TD>
                  <TD mono className="text-fg-muted">
                    {p.product_model?.identifier ?? "—"}
                  </TD>
                  <TD mono className="text-fg-muted">
                    {p.caliber?.identifier ?? "—"}
                  </TD>
                  <TD align="right" mono>
                    {p.installed_count}
                  </TD>
                  <TD align="right" mono>
                    {p.build_count}
                  </TD>
                  <TD className="text-fg-subtle">{formatDate(p.started_on)}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        ) : (
          <EmptyState
            icon={Layers}
            title="No prototypes"
            description="Create the first prototype to start a build log."
            className="m-4"
          />
        )}
      </Card>
    </div>
  );
}

function NewPrototypeForm({ onDone }: { onDone: () => void }) {
  const create = useCreatePrototype();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const fd = new FormData(event.currentTarget);
    create.mutate(
      {
        product_code: formText(fd, "product_code") || "N1",
        name: formText(fd, "name"),
        purpose: formOptional(fd, "purpose"),
        started_on: formOptional(fd, "started_on"),
      },
      {
        onSuccess: (p) => {
          onDone();
          navigate(`/prototypes/${p.identifier}`);
        },
        onError: (err) => setError(describeError(err)),
      },
    );
  }

  return (
    <Card className="mb-4">
      <CardHeader eyebrow="New" title="Prototype" />
      <CardContent>
        <form onSubmit={onSubmit} className="grid gap-3 sm:grid-cols-[8rem_1fr_10rem]">
          <Field label="Product code" htmlFor="p-code" hint="N1 → N1-P00n">
            <Input
              id="p-code"
              name="product_code"
              defaultValue="N1"
              className="font-mono uppercase"
            />
          </Field>
          <Field label="Name" htmlFor="p-name">
            <Input id="p-name" name="name" required placeholder="Movement bench build" />
          </Field>
          <Field label="Started on" htmlFor="p-started">
            <Input id="p-started" name="started_on" type="date" className="font-mono" />
          </Field>
          <Field label="Purpose" htmlFor="p-purpose" className="sm:col-span-3">
            <Textarea
              id="p-purpose"
              name="purpose"
              placeholder="What this build is meant to prove."
            />
          </Field>
          <div className="sm:col-span-3">
            <FormError message={error} />
          </div>
          <div className="flex gap-2 sm:col-span-3">
            <Button type="submit" variant="primary" disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create prototype"}
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
