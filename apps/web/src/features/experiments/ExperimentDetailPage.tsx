import {
  EXPERIMENT_OUTCOMES,
  EXPERIMENT_STATUSES,
  type ExperimentOutcome,
  type ExperimentRead,
  type ExperimentStatus,
} from "@nemeth/domain-types";
import { Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { AttachmentsPanel } from "@/components/domain/AttachmentsPanel";
import { Identifier, LifecycleBadge, PlaceholderBadge } from "@/components/domain/badges";
import { ExperimentStatusBadge, OutcomeBadge } from "@/components/domain/experimentBadges";
import { PrototypeStatusBadge } from "@/components/domain/prototypeBadges";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Field, FormError, Input, Select, Textarea } from "@/components/ui/form";
import { EmptyState, ErrorNotice, KV, LoadingRows, PageHeader } from "@/components/ui/layout";
import { ExperimentTestRunsPanel } from "@/features/testing/TestRunsPanel";
import { describeError } from "@/lib/api";
import {
  useExperiment,
  useLinkPrototype,
  useLinkRevision,
  useUnlinkPrototype,
  useUnlinkRevision,
  useUpdateExperiment,
} from "@/lib/experimentQueries";
import { formatDate, formatDateTime, formOptional, formText, titleCase } from "@/lib/format";
import { usePrototypes } from "@/lib/prototypeQueries";
import { useRevisions } from "@/lib/queries";

const SECTIONS: { key: keyof ExperimentRead; label: string; hint?: string }[] = [
  { key: "objective", label: "Objective" },
  { key: "hypothesis", label: "Hypothesis" },
  {
    key: "configuration",
    label: "Configuration",
    hint: "What was on the bench: movement, prototype, revisions, settings.",
  },
  { key: "methodology", label: "Methodology" },
  { key: "equipment", label: "Equipment" },
  { key: "procedure", label: "Procedure" },
  { key: "observations", label: "Observations" },
  {
    key: "results",
    label: "Results",
    hint: "Before/after numbers go here until measurements arrive in slice 9.",
  },
  { key: "conclusion", label: "Conclusion" },
  { key: "follow_up", label: "Follow-up actions" },
  { key: "notes", label: "Notes" },
];

export function ExperimentDetailPage() {
  const { ref = "" } = useParams();
  const experiment = useExperiment(ref);
  const [editing, setEditing] = useState(false);

  if (experiment.isLoading) return <LoadingRows />;
  if (experiment.isError) return <ErrorNotice error={experiment.error} />;
  if (!experiment.data) return null;
  const e = experiment.data;
  const closed = e.status === "COMPLETED" || e.status === "ABANDONED";

  return (
    <div>
      <PageHeader
        eyebrow={
          <span>
            <Link to="/experiments" className="hover:underline">
              Experiments
            </Link>{" "}
            / {e.identifier}
          </span>
        }
        title={
          <>
            <Identifier value={e.identifier} className="text-xl" />
            <span>{e.title}</span>
          </>
        }
        meta={
          <>
            <ExperimentStatusBadge status={e.status} />
            <OutcomeBadge outcome={e.outcome} />
            <PlaceholderBadge show={e.is_placeholder} />
            {e.started_on ? (
              <span className="text-xs text-fg-subtle">Started {formatDate(e.started_on)}</span>
            ) : null}
            {e.completed_on ? (
              <span className="text-xs text-fg-subtle">Completed {formatDate(e.completed_on)}</span>
            ) : null}
          </>
        }
        actions={
          <>
            <StatusControls experiment={e} />
            <Button variant="primary" onClick={() => setEditing((v) => !v)}>
              {editing ? "Close editor" : "Edit notebook"}
            </Button>
          </>
        }
      />

      <div className="grid gap-4 xl:grid-cols-3">
        <div className="grid gap-4 xl:col-span-2">
          {editing ? (
            <NotebookEditor experiment={e} onDone={() => setEditing(false)} />
          ) : (
            <Card>
              <CardHeader eyebrow="Lab notebook" title={e.title} />
              <CardContent className="grid gap-5">
                {SECTIONS.map((section) => {
                  const value = e[section.key];
                  return (
                    <section key={section.key}>
                      <div className="label mb-1">{section.label}</div>
                      {typeof value === "string" && value.trim() ? (
                        <p className="whitespace-pre-wrap text-sm leading-relaxed text-fg">
                          {value}
                        </p>
                      ) : (
                        <p className="text-sm text-fg-subtle">—</p>
                      )}
                    </section>
                  );
                })}
              </CardContent>
            </Card>
          )}
          <ExperimentTestRunsPanel experimentRef={e.identifier} />
          <AttachmentsPanel entityType="experiment" entityId={e.id} defaultKind="PHOTO" />
        </div>
        <div className="grid gap-4 self-start">
          <LinksPanel experiment={e} locked={closed} />
          <Card>
            <CardHeader eyebrow="Record" title="Details" />
            <CardContent>
              <KV
                columns={1}
                items={[
                  { label: "Created", value: `${formatDateTime(e.created_at)} · ${e.created_by}` },
                  { label: "Updated", value: `${formatDateTime(e.updated_at)} · ${e.updated_by}` },
                  { label: "Internal id", value: e.id, mono: true },
                ]}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function StatusControls({ experiment }: { experiment: ExperimentRead }) {
  const update = useUpdateExperiment(experiment.identifier);
  const [error, setError] = useState<string | null>(null);
  const closed = experiment.status === "COMPLETED" || experiment.status === "ABANDONED";
  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center gap-2">
        <Select
          value={experiment.status}
          disabled={closed || update.isPending}
          aria-label="Experiment status"
          className="w-36"
          onChange={(ev) => {
            setError(null);
            update.mutate(
              { status: ev.target.value as ExperimentStatus },
              { onError: (err) => setError(describeError(err)) },
            );
          }}
        >
          {EXPERIMENT_STATUSES.map((s) => (
            <option key={s} value={s}>
              {titleCase(s)}
            </option>
          ))}
        </Select>
        <Select
          value={experiment.outcome ?? ""}
          disabled={update.isPending}
          aria-label="Outcome"
          className="w-40"
          onChange={(ev) => {
            setError(null);
            update.mutate(
              { outcome: (ev.target.value || null) as ExperimentOutcome | null },
              { onError: (err) => setError(describeError(err)) },
            );
          }}
        >
          <option value="">No outcome yet</option>
          {EXPERIMENT_OUTCOMES.map((o) => (
            <option key={o} value={o}>
              {titleCase(o)}
            </option>
          ))}
        </Select>
      </div>
      <FormError message={error} />
    </div>
  );
}

function NotebookEditor({
  experiment,
  onDone,
}: {
  experiment: ExperimentRead;
  onDone: () => void;
}) {
  const update = useUpdateExperiment(experiment.identifier);
  const [error, setError] = useState<string | null>(null);

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const fd = new FormData(event.currentTarget);
    const body: Record<string, string | null> = {
      title: formText(fd, "title"),
      started_on: formOptional(fd, "started_on"),
      completed_on: formOptional(fd, "completed_on"),
    };
    for (const section of SECTIONS) body[section.key] = formOptional(fd, section.key);
    update.mutate(body, { onSuccess: onDone, onError: (err) => setError(describeError(err)) });
  }

  return (
    <Card>
      <CardHeader eyebrow="Editing" title="Lab notebook" />
      <CardContent>
        <form onSubmit={onSubmit} className="grid gap-4">
          <div className="grid gap-3 sm:grid-cols-[1fr_10rem_10rem]">
            <Field label="Title" htmlFor="n-title">
              <Input id="n-title" name="title" defaultValue={experiment.title} required />
            </Field>
            <Field label="Started on" htmlFor="n-started">
              <Input
                id="n-started"
                name="started_on"
                type="date"
                defaultValue={experiment.started_on ?? ""}
                className="font-mono"
              />
            </Field>
            <Field label="Completed on" htmlFor="n-completed">
              <Input
                id="n-completed"
                name="completed_on"
                type="date"
                defaultValue={experiment.completed_on ?? ""}
                className="font-mono"
              />
            </Field>
          </div>
          {SECTIONS.map((section) => {
            const value = experiment[section.key];
            return (
              <Field
                key={section.key}
                label={section.label}
                htmlFor={`n-${section.key}`}
                hint={section.hint}
              >
                <Textarea
                  id={`n-${section.key}`}
                  name={section.key}
                  defaultValue={typeof value === "string" ? value : ""}
                />
              </Field>
            );
          })}
          <FormError message={error} />
          <div className="flex gap-2">
            <Button type="submit" variant="primary" disabled={update.isPending}>
              {update.isPending ? "Saving…" : "Save notebook"}
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

function LinksPanel({ experiment, locked }: { experiment: ExperimentRead; locked: boolean }) {
  const prototypes = usePrototypes();
  const linkPrototype = useLinkPrototype(experiment.identifier);
  const unlinkPrototype = useUnlinkPrototype(experiment.identifier);
  const linkRevision = useLinkRevision(experiment.identifier);
  const unlinkRevision = useUnlinkRevision(experiment.identifier);
  const [componentRef, setComponentRef] = useState("");
  const [lookup, setLookup] = useState("");
  const revisions = useRevisions(lookup);
  const [error, setError] = useState<string | null>(null);

  const linkedPrototypeIds = new Set(experiment.prototypes.map((l) => l.prototype.id));
  const candidates = (prototypes.data?.items ?? []).filter((p) => !linkedPrototypeIds.has(p.id));

  return (
    <Card>
      <CardHeader eyebrow="Involved" title="Prototypes and revisions" />
      <CardContent className="grid gap-4">
        <div>
          <div className="label mb-1">Prototypes</div>
          {experiment.prototypes.length === 0 ? (
            <p className="text-xs text-fg-subtle">None linked.</p>
          ) : (
            <ul className="divide-y divide-border rounded border border-border">
              {experiment.prototypes.map((l) => (
                <li key={l.id} className="flex items-center gap-2 px-2 py-1.5">
                  <Identifier
                    value={l.prototype.identifier}
                    to={`/prototypes/${l.prototype.identifier}`}
                  />
                  <span className="flex-1 truncate text-xs text-fg-muted">{l.prototype.name}</span>
                  {l.role ? (
                    <span className="text-2xs uppercase tracking-label text-fg-subtle">
                      {l.role}
                    </span>
                  ) : null}
                  <PrototypeStatusBadge status={l.prototype.status} />
                  {!locked ? (
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Unlink ${l.prototype.identifier}`}
                      onClick={() => unlinkPrototype.mutate(l.prototype.identifier)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
          {!locked ? (
            <Select
              value=""
              className="mt-2"
              aria-label="Link prototype"
              onChange={(ev) => {
                if (!ev.target.value) return;
                setError(null);
                linkPrototype.mutate(
                  { prototype_identifier: ev.target.value },
                  { onError: (err) => setError(describeError(err)) },
                );
              }}
            >
              <option value="">Link a prototype…</option>
              {candidates.map((p) => (
                <option key={p.id} value={p.identifier}>
                  {p.identifier} · {p.name}
                </option>
              ))}
            </Select>
          ) : null}
        </div>

        <div>
          <div className="label mb-1">Component revisions</div>
          {experiment.revisions.length === 0 ? (
            <p className="text-xs text-fg-subtle">None linked.</p>
          ) : (
            <ul className="divide-y divide-border rounded border border-border">
              {experiment.revisions.map((l) => (
                <li key={l.id} className="flex items-center gap-2 px-2 py-1.5">
                  <Identifier
                    value={`${l.component.identifier} Rev ${l.revision.revision_label}`}
                    to={`/components/${l.component.identifier}/revisions/${l.revision.revision_label}`}
                  />
                  <span className="flex-1 truncate text-xs text-fg-muted">{l.component.name}</span>
                  {l.role ? (
                    <span className="text-2xs uppercase tracking-label text-fg-subtle">
                      {l.role}
                    </span>
                  ) : null}
                  <LifecycleBadge state={l.revision.lifecycle_state} />
                  {!locked ? (
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Unlink ${l.component.identifier}`}
                      onClick={() => unlinkRevision.mutate(l.revision.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
          {!locked ? (
            <div className="mt-2 grid gap-2">
              <div className="flex gap-2">
                <Input
                  value={componentRef}
                  onChange={(ev) => setComponentRef(ev.target.value)}
                  placeholder="N1-MVT-006"
                  className="font-mono uppercase"
                  aria-label="Component identifier"
                />
                <Button onClick={() => setLookup(componentRef.trim().toUpperCase())}>Load</Button>
              </div>
              {lookup ? (
                <Select
                  value=""
                  aria-label="Link revision"
                  onChange={(ev) => {
                    if (!ev.target.value) return;
                    setError(null);
                    linkRevision.mutate(
                      { component_revision_id: ev.target.value },
                      { onError: (err) => setError(describeError(err)) },
                    );
                  }}
                >
                  <option value="">
                    {revisions.isLoading
                      ? "Loading…"
                      : revisions.isError
                        ? describeError(revisions.error)
                        : "Link a revision…"}
                  </option>
                  {(revisions.data ?? []).map((r) => (
                    <option key={r.id} value={r.id}>
                      Rev {r.revision_label} · {titleCase(r.lifecycle_state)}
                    </option>
                  ))}
                </Select>
              ) : null}
            </div>
          ) : null}
        </div>
        <FormError message={error} />
        {locked ? (
          <p className="text-2xs text-fg-subtle">
            Links are fixed once an experiment is completed or abandoned.
          </p>
        ) : null}
        {experiment.prototypes.length === 0 && experiment.revisions.length === 0 && locked ? (
          <EmptyState title="Nothing linked" className="py-4" />
        ) : null}
      </CardContent>
    </Card>
  );
}
