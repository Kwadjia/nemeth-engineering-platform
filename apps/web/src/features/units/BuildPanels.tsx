/**
 * Configuration, build log and new-build form shared by prototypes and watches
 * (ADR-008: one genealogy structure, two kinds of unit).
 */
import type {
  BuildAction,
  BuildRecordCreate,
  BuildRecordRead,
  PartInstanceRead,
  UnitConfiguration,
} from "@nemeth/domain-types";
import type { UseMutationResult, UseQueryResult } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Identifier, LifecycleBadge } from "@/components/domain/badges";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Field, FormError, Input, Select, Textarea } from "@/components/ui/form";
import { EmptyState, ErrorNotice, LoadingRows } from "@/components/ui/layout";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { describeError } from "@/lib/api";
import { formatDate, formOptional, formText, titleCase } from "@/lib/format";
import { usePartInstances } from "@/lib/prototypeQueries";

export function ConfigurationPanel({
  configuration,
}: {
  configuration: UseQueryResult<UnitConfiguration>;
}) {
  const config = configuration;
  return (
    <Card>
      <CardHeader
        eyebrow="As built · derived from the build log"
        title="Current configuration"
        actions={
          config.data ? (
            <span className="font-mono text-xs text-fg-subtle">{config.data.count} parts</span>
          ) : null
        }
      />
      {config.isLoading ? (
        <LoadingRows />
      ) : config.isError ? (
        <CardContent>
          <ErrorNotice error={config.error} />
        </CardContent>
      ) : config.data && config.data.rows.length > 0 ? (
        <Table>
          <THead>
            <TR>
              <TH className="w-24">Part</TH>
              <TH className="w-32">Component</TH>
              <TH>Name</TH>
              <TH className="w-40">Exact revision</TH>
              <TH className="w-32">Position</TH>
              <TH className="w-32">Serial</TH>
              <TH className="w-40">Installed by</TH>
            </TR>
          </THead>
          <TBody>
            {config.data.rows.map((row) => (
              <TR key={row.part_instance.id}>
                <TD>
                  <Identifier
                    value={row.part_instance.identifier}
                    to={`/part-instances?q=${row.part_instance.identifier}`}
                  />
                </TD>
                <TD>
                  <Identifier
                    value={row.component.identifier}
                    to={`/components/${row.component.identifier}`}
                  />
                </TD>
                <TD>{row.component.name}</TD>
                <TD>
                  <span className="inline-flex items-center gap-1.5">
                    <Identifier
                      value={`Rev ${row.revision.revision_label}`}
                      to={`/components/${row.component.identifier}/revisions/${row.revision.revision_label}`}
                    />
                    <LifecycleBadge state={row.revision.lifecycle_state} />
                  </span>
                </TD>
                <TD className="text-fg-muted">{row.position ?? "—"}</TD>
                <TD mono className="text-fg-muted">
                  {row.part_instance.serial_number ?? "—"}
                </TD>
                <TD className="text-fg-muted">
                  {row.installed_by ? (
                    <span className="inline-flex items-center gap-1.5">
                      <Identifier value={row.installed_by.identifier} />
                      <span className="text-xs text-fg-subtle">
                        {formatDate(row.installed_by.performed_on)}
                      </span>
                    </span>
                  ) : (
                    "—"
                  )}
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      ) : (
        <CardContent>
          <EmptyState
            title="Nothing installed yet"
            description="Record a build with install entries below. Parts must exist as part instances against a frozen revision."
            className="py-6"
          />
        </CardContent>
      )}
    </Card>
  );
}

export function BuildLogPanel({ builds }: { builds: UseQueryResult<BuildRecordRead[]> }) {
  return (
    <Card>
      <CardHeader eyebrow="History · append-only" title="Build log" />
      {builds.isLoading ? (
        <LoadingRows rows={2} />
      ) : builds.data && builds.data.length > 0 ? (
        <ul className="divide-y divide-border">
          {builds.data.map((b) => (
            <BuildRow key={b.id} build={b} />
          ))}
        </ul>
      ) : (
        <CardContent>
          <EmptyState
            title="No build records"
            description="The first build record starts this unit's history."
            className="py-6"
          />
        </CardContent>
      )}
    </Card>
  );
}

function BuildRow({ build }: { build: BuildRecordRead }) {
  const [open, setOpen] = useState(false);
  return (
    <li>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-surface-2"
      >
        {open ? (
          <ChevronDown className="h-3.5 w-3.5 text-fg-subtle" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 text-fg-subtle" />
        )}
        <Identifier value={build.identifier} />
        <span className="font-mono text-xs text-fg-subtle">{formatDate(build.performed_on)}</span>
        <span className="flex-1 truncate text-sm text-fg">{build.title}</span>
        <span className="text-xs text-fg-subtle">{build.performed_by}</span>
        <span className="font-mono text-xs text-fg-muted">
          {build.entries.length} {build.entries.length === 1 ? "entry" : "entries"}
        </span>
      </button>
      {open ? (
        <div className="border-t border-border bg-bg-elevated px-4 py-3">
          {build.procedure ? (
            <div className="mb-3">
              <div className="label mb-1">Procedure</div>
              <pre className="whitespace-pre-wrap font-sans text-sm text-fg-muted">
                {build.procedure}
              </pre>
            </div>
          ) : null}
          {build.entries.length > 0 ? (
            <Table>
              <THead>
                <TR>
                  <TH className="w-10" align="right">
                    #
                  </TH>
                  <TH className="w-20">Action</TH>
                  <TH className="w-24">Part</TH>
                  <TH className="w-32">Component</TH>
                  <TH>Name</TH>
                  <TH className="w-20">Rev</TH>
                  <TH className="w-32">Position</TH>
                  <TH>Notes</TH>
                </TR>
              </THead>
              <TBody>
                {build.entries.map((e) => (
                  <TR key={e.id}>
                    <TD align="right" mono className="text-fg-subtle">
                      {e.sequence}
                    </TD>
                    <TD>
                      <span className={e.action === "INSTALL" ? "text-ok" : "text-warn"}>
                        {titleCase(e.action)}
                      </span>
                    </TD>
                    <TD>
                      <Identifier value={e.part_instance.identifier} />
                    </TD>
                    <TD>
                      <Identifier
                        value={e.component.identifier}
                        to={`/components/${e.component.identifier}`}
                      />
                    </TD>
                    <TD>{e.component.name}</TD>
                    <TD mono>Rev {e.revision.revision_label}</TD>
                    <TD className="text-fg-muted">{e.position ?? "—"}</TD>
                    <TD className="text-fg-muted">{e.notes ?? "—"}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          ) : null}
          {build.notes ? <p className="mt-3 text-sm text-fg-muted">{build.notes}</p> : null}
        </div>
      ) : null}
    </li>
  );
}

interface EntryDraft {
  key: number;
  identifier: string;
  action: BuildAction;
  position: string;
}

export function NewBuildForm({
  unitKind,
  unitId,
  create,
}: {
  unitKind: "prototype" | "watch";
  unitId: string;
  create: UseMutationResult<BuildRecordRead, Error, BuildRecordCreate>;
}) {
  const available = usePartInstances({ status: "AVAILABLE" });
  const removed = usePartInstances({ status: "REMOVED" });
  const installed = usePartInstances(
    unitKind === "watch" ? { watch_id: unitId } : { prototype_id: unitId },
  );
  const [entries, setEntries] = useState<EntryDraft[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [nextKey, setNextKey] = useState(1);

  const installable: PartInstanceRead[] = [
    ...(available.data?.items ?? []),
    ...(removed.data?.items ?? []),
  ].filter((i) => !i.current_prototype && !i.current_watch);
  const removable: PartInstanceRead[] = installed.data?.items ?? [];

  function addEntry(identifier: string, action: BuildAction) {
    if (!identifier) return;
    setEntries((list) => [...list, { key: nextKey, identifier, action, position: "" }]);
    setNextKey((k) => k + 1);
  }

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const form = event.currentTarget;
    const fd = new FormData(form);
    create.mutate(
      {
        title: formText(fd, "title"),
        performed_on: formText(fd, "performed_on"),
        performed_by: formOptional(fd, "performed_by"),
        procedure: formOptional(fd, "procedure"),
        notes: formOptional(fd, "notes"),
        entries: entries.map((e) => ({
          part_instance_identifier: e.identifier,
          action: e.action,
          position: e.position.trim() || null,
        })),
      },
      {
        onSuccess: () => {
          form.reset();
          setEntries([]);
        },
        onError: (err) => setError(describeError(err)),
      },
    );
  }

  const today = new Date().toISOString().slice(0, 10);
  const label = (i: PartInstanceRead) =>
    `${i.identifier} · ${i.component.identifier} ${i.component.name} · Rev ${i.revision.revision_label}${i.serial_number ? ` · ${i.serial_number}` : ""}`;

  return (
    <Card>
      <CardHeader eyebrow="Record what happened at the bench" title="New build record" />
      <CardContent>
        <form onSubmit={onSubmit} className="grid gap-3">
          <div className="grid gap-3 sm:grid-cols-[1fr_10rem_12rem]">
            <Field label="Title" htmlFor="b-title">
              <Input
                id="b-title"
                name="title"
                required
                placeholder="Fit gear train and escapement"
              />
            </Field>
            <Field label="Performed on" htmlFor="b-date">
              <Input
                id="b-date"
                name="performed_on"
                type="date"
                defaultValue={today}
                required
                className="font-mono"
              />
            </Field>
            <Field label="Performed by" htmlFor="b-by" hint="defaults to you">
              <Input id="b-by" name="performed_by" />
            </Field>
          </div>
          <Field
            label="Procedure"
            htmlFor="b-proc"
            hint="Steps, lubrication, torque, sequence, as performed."
          >
            <Textarea id="b-proc" name="procedure" />
          </Field>

          <div className="rounded border border-border bg-bg-elevated p-3">
            <div className="mb-2 flex flex-wrap items-end gap-2">
              <Field label="Install a part instance" className="min-w-[18rem] flex-1">
                <Select
                  value=""
                  onChange={(e) => addEntry(e.target.value, "INSTALL")}
                  aria-label="Install part instance"
                >
                  <option value="">Choose an available part…</option>
                  {installable.map((i) => (
                    <option key={i.id} value={i.identifier}>
                      {label(i)}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Remove an installed part" className="min-w-[18rem] flex-1">
                <Select
                  value=""
                  onChange={(e) => addEntry(e.target.value, "REMOVE")}
                  aria-label="Remove part instance"
                >
                  <option value="">Choose an installed part…</option>
                  {removable.map((i) => (
                    <option key={i.id} value={i.identifier}>
                      {label(i)}
                    </option>
                  ))}
                </Select>
              </Field>
              <Link
                to="/part-instances"
                className="pb-2 text-xs text-fg-muted hover:text-fg hover:underline"
              >
                <Plus className="mr-1 inline h-3 w-3" />
                Record new parts
              </Link>
            </div>
            {entries.length > 0 ? (
              <Table>
                <THead>
                  <TR>
                    <TH className="w-10" align="right">
                      #
                    </TH>
                    <TH className="w-24">Action</TH>
                    <TH className="w-28">Part</TH>
                    <TH>Position</TH>
                    <TH className="w-10" />
                  </TR>
                </THead>
                <TBody>
                  {entries.map((e, index) => (
                    <TR key={e.key}>
                      <TD align="right" mono className="text-fg-subtle">
                        {index + 1}
                      </TD>
                      <TD>
                        <span className={e.action === "INSTALL" ? "text-ok" : "text-warn"}>
                          {titleCase(e.action)}
                        </span>
                      </TD>
                      <TD>
                        <Identifier value={e.identifier} />
                      </TD>
                      <TD>
                        <Input
                          value={e.position}
                          placeholder="e.g. train bridge, 3 o'clock"
                          aria-label={`Position for ${e.identifier}`}
                          onChange={(ev) =>
                            setEntries((list) =>
                              list.map((x) =>
                                x.key === e.key ? { ...x, position: ev.target.value } : x,
                              ),
                            )
                          }
                        />
                      </TD>
                      <TD align="right">
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={`Drop ${e.identifier}`}
                          onClick={() => setEntries((list) => list.filter((x) => x.key !== e.key))}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            ) : (
              <p className="text-xs text-fg-subtle">
                No entries yet. A record without entries is a valid note in the log.
              </p>
            )}
          </div>

          <Field label="Notes" htmlFor="b-notes">
            <Textarea id="b-notes" name="notes" className="min-h-[3rem]" />
          </Field>
          <FormError message={error} />
          <div>
            <Button type="submit" variant="primary" disabled={create.isPending}>
              {create.isPending ? "Saving…" : "Save build record"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
