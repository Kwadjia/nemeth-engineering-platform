import { Plus, Watch as WatchIcon } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Identifier, PlaceholderBadge } from "@/components/domain/badges";
import { WatchStatusBadge } from "@/components/domain/watchBadges";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Field, FormError, Input, Select, Textarea } from "@/components/ui/form";
import { EmptyState, ErrorNotice, LoadingRows, PageHeader } from "@/components/ui/layout";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { describeError } from "@/lib/api";
import { formatDate, formOptional, formText } from "@/lib/format";
import { usePrototypes } from "@/lib/prototypeQueries";
import { useProducts } from "@/lib/queries";
import { useCreateWatch, useWatches } from "@/lib/watchQueries";

export function WatchesPage() {
  const watches = useWatches();
  const navigate = useNavigate();
  const [creating, setCreating] = useState(false);

  return (
    <div>
      <PageHeader
        eyebrow="Development"
        title="Watches"
        description="Serialized watches. Each one carries a digital build record: exact revisions installed, assembly history, test history, and the prototype and experiments it came from."
        actions={
          <Button variant="primary" onClick={() => setCreating((v) => !v)}>
            <Plus className="h-3.5 w-3.5" /> New watch
          </Button>
        }
      />
      {creating ? <NewWatchForm onDone={() => setCreating(false)} /> : null}
      {watches.isError ? <ErrorNotice error={watches.error} /> : null}
      <Card>
        {watches.isLoading ? (
          <LoadingRows />
        ) : watches.data && watches.data.items.length > 0 ? (
          <Table>
            <THead>
              <TR>
                <TH className="w-28">Watch</TH>
                <TH className="w-20">Serial</TH>
                <TH className="w-24">Model</TH>
                <TH className="w-36">Status</TH>
                <TH>Owner</TH>
                <TH className="w-20" align="right">
                  Parts
                </TH>
                <TH className="w-20" align="right">
                  Builds
                </TH>
                <TH className="w-28">Assembled</TH>
              </TR>
            </THead>
            <TBody>
              {watches.data.items.map((w) => (
                <TR key={w.id} interactive onClick={() => navigate(`/watches/${w.identifier}`)}>
                  <TD>
                    <span className="inline-flex items-center gap-2">
                      <Identifier value={w.identifier} />
                      <PlaceholderBadge show={w.is_placeholder} />
                    </span>
                  </TD>
                  <TD mono>{w.serial_number}</TD>
                  <TD mono className="text-fg-muted">
                    {w.product_model.identifier}
                  </TD>
                  <TD>
                    <WatchStatusBadge status={w.status} />
                  </TD>
                  <TD className="text-fg">{w.owner_name ?? "—"}</TD>
                  <TD align="right" mono>
                    {w.installed_count}
                  </TD>
                  <TD align="right" mono>
                    {w.build_count}
                  </TD>
                  <TD className="text-fg-subtle">{formatDate(w.assembled_on)}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        ) : (
          <EmptyState
            icon={WatchIcon}
            title="No watches yet"
            description="The first serialized watch starts here. Prototypes stay prototypes until you decide one deserves a serial number."
            className="m-4"
          />
        )}
      </Card>
    </div>
  );
}

function NewWatchForm({ onDone }: { onDone: () => void }) {
  const products = useProducts();
  const prototypes = usePrototypes();
  const create = useCreateWatch();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const models = (products.data?.items ?? []).flatMap((p) => p.models);

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const fd = new FormData(event.currentTarget);
    const identifier = formOptional(fd, "identifier");
    create.mutate(
      {
        product_model_ref: formText(fd, "product_model_ref"),
        identifier,
        serial_number: identifier ? formOptional(fd, "serial_number") : null,
        owner_name: formOptional(fd, "owner_name"),
        origin_prototype_ref: formOptional(fd, "origin_prototype_ref"),
        assembled_on: formOptional(fd, "assembled_on"),
        notes: formOptional(fd, "notes"),
      },
      {
        onSuccess: (w) => {
          onDone();
          navigate(`/watches/${w.identifier}`);
        },
        onError: (err) => setError(describeError(err)),
      },
    );
  }

  return (
    <Card className="mb-4">
      <CardHeader eyebrow="New" title="Serialized watch" />
      <CardContent>
        <form onSubmit={onSubmit} className="grid gap-3 sm:grid-cols-4">
          <Field label="Model" htmlFor="w-model">
            <Select
              id="w-model"
              name="product_model_ref"
              required
              defaultValue={models[0]?.identifier ?? ""}
            >
              {models.map((m) => (
                <option key={m.id} value={m.identifier}>
                  {m.identifier} · {m.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Identifier" htmlFor="w-id" hint="blank = next serial, e.g. N1-001">
            <Input
              id="w-id"
              name="identifier"
              placeholder="N1-001"
              className="font-mono uppercase"
            />
          </Field>
          <Field label="Serial" htmlFor="w-serial" hint="only with an explicit identifier">
            <Input id="w-serial" name="serial_number" className="font-mono" />
          </Field>
          <Field label="Assembled on" htmlFor="w-assembled">
            <Input id="w-assembled" name="assembled_on" type="date" className="font-mono" />
          </Field>
          <Field label="Owner" htmlFor="w-owner" className="sm:col-span-2">
            <Input id="w-owner" name="owner_name" placeholder="Arthur Nemeth" />
          </Field>
          <Field label="Origin prototype" htmlFor="w-proto" className="sm:col-span-2">
            <Select id="w-proto" name="origin_prototype_ref" defaultValue="">
              <option value="">None</option>
              {(prototypes.data?.items ?? []).map((p) => (
                <option key={p.id} value={p.identifier}>
                  {p.identifier} · {p.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Notes" htmlFor="w-notes" className="sm:col-span-4">
            <Textarea id="w-notes" name="notes" className="min-h-[3rem]" />
          </Field>
          <div className="sm:col-span-4">
            <FormError message={error} />
          </div>
          <div className="flex gap-2 sm:col-span-4">
            <Button type="submit" variant="primary" disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create watch"}
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
