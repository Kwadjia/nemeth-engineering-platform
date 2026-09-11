import type { RevisionRead } from "@nemeth/domain-types";
import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import {
  FrozenBadge,
  Identifier,
  LifecycleBadge,
  PlaceholderBadge,
} from "@/components/domain/badges";
import { BomFlatTable } from "@/components/domain/BomFlatTable";
import { BomTree } from "@/components/domain/BomTree";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Field, FormError, Input, Select } from "@/components/ui/form";
import { ErrorNotice, LoadingRows, PageHeader, Stat } from "@/components/ui/layout";
import { describeError } from "@/lib/api";
import { formOptional, formText } from "@/lib/format";
import {
  useAddBomLine,
  useBom,
  useBomFlat,
  useComponent,
  useDeleteBomLine,
  useRevisions,
  type ResolveMode,
} from "@/lib/queries";

export function BomExplorerPage() {
  const { ref = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const component = useComponent(ref);
  const revisions = useRevisions(ref);
  const [mode, setMode] = useState<ResolveMode>("latest");
  const [view, setView] = useState<"tree" | "flat">("tree");

  if (component.isLoading || revisions.isLoading) return <LoadingRows />;
  if (component.isError) return <ErrorNotice error={component.error} />;
  if (revisions.isError) return <ErrorNotice error={revisions.error} />;
  if (!component.data || !revisions.data) return null;

  const c = component.data;
  const wanted = params.get("rev")?.toUpperCase();
  const revision =
    revisions.data.find((r) => r.revision_label === wanted) ??
    revisions.data[revisions.data.length - 1];

  if (c.kind !== "ASSEMBLY") {
    return (
      <ErrorNotice
        title="Not an assembly"
        error={
          new Error(`${c.identifier} is a part and has no BOM. Only assemblies own BOM lines.`)
        }
      />
    );
  }

  return (
    <div>
      <PageHeader
        eyebrow={
          <span>
            <Link to="/boms" className="hover:underline">
              BOMs
            </Link>{" "}
            / {c.family}
          </span>
        }
        title={
          <>
            <Identifier
              value={c.identifier}
              className="text-xl"
              to={`/components/${c.identifier}`}
            />
            <span>{c.name}</span>
          </>
        }
        description={c.description}
        meta={<PlaceholderBadge show={c.is_placeholder} />}
        actions={
          <div className="flex items-center gap-3">
            <Select
              value={revision?.revision_label ?? ""}
              onChange={(e) => {
                const next = new URLSearchParams(params);
                next.set("rev", e.target.value);
                setParams(next, { replace: true });
              }}
              className="w-40"
              aria-label="Revision"
            >
              {[...revisions.data].reverse().map((r) => (
                <option key={r.id} value={r.revision_label}>
                  Rev {r.revision_label} · {r.lifecycle_state}
                </option>
              ))}
            </Select>
            <div className="flex items-center rounded border border-border-strong">
              <Button
                size="sm"
                variant={mode === "latest" ? "primary" : "ghost"}
                onClick={() => setMode("latest")}
              >
                Latest
              </Button>
              <Button
                size="sm"
                variant={mode === "released" ? "primary" : "ghost"}
                onClick={() => setMode("released")}
              >
                Released
              </Button>
            </div>
            <div className="flex items-center rounded border border-border-strong">
              <Button
                size="sm"
                variant={view === "tree" ? "primary" : "ghost"}
                onClick={() => setView("tree")}
              >
                Tree
              </Button>
              <Button
                size="sm"
                variant={view === "flat" ? "primary" : "ghost"}
                onClick={() => setView("flat")}
              >
                Indented
              </Button>
            </div>
          </div>
        }
      />
      {revision ? <Explorer revision={revision} mode={mode} view={view} /> : null}
    </div>
  );
}

function Explorer({
  revision,
  mode,
  view,
}: {
  revision: RevisionRead;
  mode: ResolveMode;
  view: "tree" | "flat";
}) {
  const tree = useBom(revision.id, mode);
  const flat = useBomFlat(revision.id, mode);
  const remove = useDeleteBomLine();
  const [error, setError] = useState<string | null>(null);
  const editable = !revision.is_frozen;

  return (
    <div className="grid gap-4">
      <div className="grid gap-2 sm:grid-cols-4">
        <Stat
          label="Revision"
          value={
            <span className="inline-flex items-center gap-2">
              Rev {revision.revision_label}
              <LifecycleBadge state={revision.lifecycle_state} />
              <FrozenBadge frozen={revision.is_frozen} />
            </span>
          }
        />
        <Stat label="Lines (all levels)" value={tree.data?.line_count ?? "—"} />
        <Stat label="Max depth" value={tree.data?.max_depth ?? "—"} />
        <Stat
          label={`Unresolved in ${mode}`}
          value={tree.data?.unresolved_count ?? "—"}
          hint={
            mode === "released"
              ? "children without a released revision"
              : "children with only obsolete revisions"
          }
        />
      </div>

      <FormError message={error} />

      <Card>
        <CardHeader
          eyebrow={view === "tree" ? "Tree" : "Indented list with extended quantities"}
          title={`${revision.component.identifier} Rev ${revision.revision_label}`}
        />
        {(view === "tree" ? tree : flat).isLoading ? (
          <LoadingRows rows={6} />
        ) : view === "tree" && tree.data ? (
          <BomTree
            tree={tree.data}
            onRemoveLine={
              editable
                ? (id) => {
                    setError(null);
                    remove.mutate(id, { onError: (err) => setError(describeError(err)) });
                  }
                : undefined
            }
            removing={remove.isPending}
          />
        ) : view === "flat" && flat.data ? (
          <BomFlatTable flat={flat.data} />
        ) : tree.isError || flat.isError ? (
          <CardContent>
            <ErrorNotice error={tree.error ?? flat.error} />
          </CardContent>
        ) : null}
      </Card>

      {editable ? (
        <AddLineForm revisionId={revision.id} />
      ) : (
        <p className="text-xs text-fg-subtle">
          Rev {revision.revision_label} is frozen. To change its contents, create a new revision of{" "}
          <Link
            to={`/components/${revision.component.identifier}`}
            className="text-accent hover:underline"
          >
            {revision.component.identifier}
          </Link>
          .
        </p>
      )}
    </div>
  );
}

function AddLineForm({ revisionId }: { revisionId: string }) {
  const add = useAddBomLine(revisionId);
  const [error, setError] = useState<string | null>(null);

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const form = event.currentTarget;
    const fd = new FormData(form);
    const find = formText(fd, "find_number");
    add.mutate(
      {
        child_component_identifier: formText(fd, "child"),
        quantity: formText(fd, "quantity") || "1",
        find_number: find ? Number(find) : null,
        reference_designator: formOptional(fd, "reference_designator"),
      },
      { onSuccess: () => form.reset(), onError: (err) => setError(describeError(err)) },
    );
  }

  return (
    <Card>
      <CardHeader eyebrow="Editable revision" title="Add BOM line" />
      <CardContent>
        <form
          onSubmit={onSubmit}
          className="grid items-end gap-3 sm:grid-cols-[1fr_6rem_6rem_1fr_auto]"
        >
          <Field label="Child component identifier" htmlFor="child">
            <Input
              id="child"
              name="child"
              required
              placeholder="N1-MVT-011"
              className="font-mono uppercase"
            />
          </Field>
          <Field label="Quantity" htmlFor="quantity">
            <Input
              id="quantity"
              name="quantity"
              defaultValue="1"
              inputMode="decimal"
              className="font-mono"
            />
          </Field>
          <Field label="Find no." htmlFor="find_number" hint="auto">
            <Input id="find_number" name="find_number" inputMode="numeric" className="font-mono" />
          </Field>
          <Field label="Reference designator" htmlFor="reference_designator">
            <Input
              id="reference_designator"
              name="reference_designator"
              placeholder="screw at 11 o'clock"
            />
          </Field>
          <Button type="submit" variant="primary" disabled={add.isPending}>
            {add.isPending ? "Adding…" : "Add line"}
          </Button>
        </form>
        <div className="mt-2">
          <FormError message={error} />
        </div>
        <p className="mt-2 text-2xs text-fg-subtle">
          Lines are floating by default (they resolve to the child's latest revision). Pinning to an
          exact revision is available through the API and arrives in the UI with the
          engineering-change slice.
        </p>
      </CardContent>
    </Card>
  );
}
