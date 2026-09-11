import {
  CHANGE_STATUSES,
  type ChangeRead,
  type ChangeRole,
  type ChangeStatus,
} from "@nemeth/domain-types";
import { Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Identifier, LifecycleBadge, PlaceholderBadge } from "@/components/domain/badges";
import { ChangeRoleBadge, ChangeStatusBadge } from "@/components/domain/changeBadges";
import { ExperimentStatusBadge } from "@/components/domain/experimentBadges";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Field, FormError, Input, Select, Textarea } from "@/components/ui/form";
import { ErrorNotice, KV, LoadingRows, PageHeader } from "@/components/ui/layout";
import { describeError } from "@/lib/api";
import {
  useChange,
  useLinkChangeExperiment,
  useLinkChangeRevision,
  useLinkChangeTestRun,
  useUnlinkChangeExperiment,
  useUnlinkChangeRevision,
  useUnlinkChangeTestRun,
  useUpdateChange,
} from "@/lib/changeQueries";
import { useExperiments } from "@/lib/experimentQueries";
import { formatDate, formatDateTime, formOptional, formText, titleCase } from "@/lib/format";
import { useRevisions } from "@/lib/queries";
import { useTestRuns } from "@/lib/testingQueries";

const SECTIONS: { key: "reason" | "description" | "impact" | "notes"; label: string }[] = [
  { key: "reason", label: "Reason" },
  { key: "description", label: "Description of the change" },
  { key: "impact", label: "Impact" },
  { key: "notes", label: "Notes" },
];

export function ChangeDetailPage() {
  const { ref = "" } = useParams();
  const change = useChange(ref);
  const [editing, setEditing] = useState(false);

  if (change.isLoading) return <LoadingRows />;
  if (change.isError) return <ErrorNotice error={change.error} />;
  if (!change.data) return null;
  const c = change.data;
  const closed = c.status === "IMPLEMENTED" || c.status === "REJECTED";

  return (
    <div>
      <PageHeader
        eyebrow={
          <span>
            <Link to="/changes" className="hover:underline">
              Engineering changes
            </Link>{" "}
            / {c.identifier}
          </span>
        }
        title={
          <>
            <Identifier value={c.identifier} className="text-xl" />
            <span>{c.title}</span>
          </>
        }
        meta={
          <>
            <ChangeStatusBadge status={c.status} />
            <PlaceholderBadge show={c.is_placeholder} />
            <span className="text-xs text-fg-subtle">Requested by {c.requested_by}</span>
            {c.approved_on ? (
              <span className="text-xs text-fg-subtle">
                Approved {formatDate(c.approved_on)} by {c.approved_by}
              </span>
            ) : null}
            {c.implemented_on ? (
              <span className="text-xs text-fg-subtle">
                Implemented {formatDate(c.implemented_on)}
              </span>
            ) : null}
          </>
        }
        actions={
          <>
            <StatusControl change={c} />
            <Button variant="primary" onClick={() => setEditing((v) => !v)}>
              {editing ? "Close editor" : "Edit"}
            </Button>
          </>
        }
      />
      <div className="grid gap-4 xl:grid-cols-3">
        <div className="grid gap-4 xl:col-span-2">
          {editing ? (
            <Editor change={c} onDone={() => setEditing(false)} />
          ) : (
            <Card>
              <CardHeader eyebrow="Record" title="Change" />
              <CardContent className="grid gap-5">
                {SECTIONS.map((section) => (
                  <section key={section.key}>
                    <div className="label mb-1">{section.label}</div>
                    {c[section.key] ? (
                      <p className="whitespace-pre-wrap text-sm leading-relaxed text-fg">
                        {c[section.key]}
                      </p>
                    ) : (
                      <p className="text-sm text-fg-subtle">—</p>
                    )}
                  </section>
                ))}
              </CardContent>
            </Card>
          )}
          <RevisionsPanel change={c} locked={closed} />
          <EvidencePanel change={c} locked={closed} />
        </div>
        <Card className="self-start">
          <CardHeader eyebrow="Record" title="Details" />
          <CardContent>
            <KV
              columns={1}
              items={[
                { label: "Created", value: `${formatDateTime(c.created_at)} · ${c.created_by}` },
                { label: "Updated", value: `${formatDateTime(c.updated_at)} · ${c.updated_by}` },
                { label: "Internal id", value: c.id, mono: true },
              ]}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StatusControl({ change }: { change: ChangeRead }) {
  const update = useUpdateChange(change.identifier);
  const [error, setError] = useState<string | null>(null);
  const closed = change.status === "IMPLEMENTED" || change.status === "REJECTED";
  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center gap-2">
        <span className="label">Status</span>
        <Select
          value={change.status}
          className="w-40"
          disabled={closed || update.isPending}
          aria-label="Change status"
          onChange={(e) => {
            setError(null);
            update.mutate(
              { status: e.target.value as ChangeStatus },
              { onError: (err) => setError(describeError(err)) },
            );
          }}
        >
          {CHANGE_STATUSES.map((s) => (
            <option key={s} value={s}>
              {titleCase(s)}
            </option>
          ))}
        </Select>
      </div>
      <FormError message={error} />
    </div>
  );
}

function Editor({ change, onDone }: { change: ChangeRead; onDone: () => void }) {
  const update = useUpdateChange(change.identifier);
  const [error, setError] = useState<string | null>(null);
  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const fd = new FormData(event.currentTarget);
    update.mutate(
      {
        title: formText(fd, "title"),
        reason: formOptional(fd, "reason"),
        description: formOptional(fd, "description"),
        impact: formOptional(fd, "impact"),
        notes: formOptional(fd, "notes"),
      },
      { onSuccess: onDone, onError: (err) => setError(describeError(err)) },
    );
  }
  return (
    <Card>
      <CardHeader eyebrow="Editing" title="Change" />
      <CardContent>
        <form onSubmit={onSubmit} className="grid gap-3">
          <Field label="Title" htmlFor="ce-title">
            <Input id="ce-title" name="title" defaultValue={change.title} required />
          </Field>
          {SECTIONS.map((s) => (
            <Field key={s.key} label={s.label} htmlFor={`ce-${s.key}`}>
              <Textarea id={`ce-${s.key}`} name={s.key} defaultValue={change[s.key] ?? ""} />
            </Field>
          ))}
          <FormError message={error} />
          <div className="flex gap-2">
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

function RevisionsPanel({ change, locked }: { change: ChangeRead; locked: boolean }) {
  const link = useLinkChangeRevision(change.identifier);
  const unlink = useUnlinkChangeRevision(change.identifier);
  const [componentRef, setComponentRef] = useState("");
  const [lookup, setLookup] = useState("");
  const [role, setRole] = useState<ChangeRole>("AFFECTED");
  const revisions = useRevisions(lookup);
  const [error, setError] = useState<string | null>(null);

  return (
    <Card>
      <CardHeader eyebrow="From → To" title="Revisions" />
      <CardContent className="grid gap-3">
        {change.revisions.length === 0 ? (
          <p className="text-xs text-fg-subtle">
            No revisions linked. Name the revision being changed (From) and the revision that
            replaces it (To).
          </p>
        ) : (
          <ul className="divide-y divide-border rounded border border-border">
            {change.revisions.map((l) => (
              <li key={l.id} className="flex items-center gap-2 px-2 py-1.5">
                <ChangeRoleBadge role={l.role} />
                <Identifier
                  value={`${l.component.identifier} Rev ${l.revision.revision_label}`}
                  to={`/components/${l.component.identifier}/revisions/${l.revision.revision_label}`}
                />
                <span className="flex-1 truncate text-xs text-fg-muted">{l.component.name}</span>
                <LifecycleBadge state={l.revision.lifecycle_state} />
                {!locked ? (
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Unlink ${l.component.identifier}`}
                    onClick={() => unlink.mutate({ revision_id: l.revision.id, role: l.role })}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
        {!locked ? (
          <div className="grid gap-2 sm:grid-cols-[1fr_auto_8rem_1fr]">
            <Input
              value={componentRef}
              onChange={(e) => setComponentRef(e.target.value)}
              placeholder="N1-MVT-004"
              className="font-mono uppercase"
              aria-label="Component identifier"
            />
            <Button onClick={() => setLookup(componentRef.trim().toUpperCase())}>Load</Button>
            <Select
              value={role}
              onChange={(e) => setRole(e.target.value as ChangeRole)}
              aria-label="Role"
            >
              <option value="AFFECTED">From (affected)</option>
              <option value="PROPOSED">To (proposed)</option>
            </Select>
            <Select
              value=""
              aria-label="Link revision"
              disabled={!lookup}
              onChange={(e) => {
                if (!e.target.value) return;
                setError(null);
                link.mutate(
                  { component_revision_id: e.target.value, role },
                  { onError: (err) => setError(describeError(err)) },
                );
              }}
            >
              <option value="">
                {lookup
                  ? revisions.isLoading
                    ? "Loading…"
                    : revisions.isError
                      ? describeError(revisions.error)
                      : "Choose a revision…"
                  : "Load a component first"}
              </option>
              {(revisions.data ?? []).map((r) => (
                <option key={r.id} value={r.id}>
                  Rev {r.revision_label} · {titleCase(r.lifecycle_state)}
                </option>
              ))}
            </Select>
          </div>
        ) : null}
        <FormError message={error} />
      </CardContent>
    </Card>
  );
}

function EvidencePanel({ change, locked }: { change: ChangeRead; locked: boolean }) {
  const experiments = useExperiments({});
  const runs = useTestRuns({});
  const linkExp = useLinkChangeExperiment(change.identifier);
  const unlinkExp = useUnlinkChangeExperiment(change.identifier);
  const linkRun = useLinkChangeTestRun(change.identifier);
  const unlinkRun = useUnlinkChangeTestRun(change.identifier);
  const [error, setError] = useState<string | null>(null);
  const linkedExp = new Set(change.experiments.map((e) => e.id));
  const linkedRuns = new Set(change.test_runs.map((r) => r.id));

  return (
    <Card>
      <CardHeader eyebrow="Why we believe it" title="Evidence" />
      <CardContent className="grid gap-4">
        <div>
          <div className="label mb-1">Experiments</div>
          {change.experiments.length === 0 ? (
            <p className="text-xs text-fg-subtle">None linked.</p>
          ) : (
            <ul className="divide-y divide-border rounded border border-border">
              {change.experiments.map((e) => (
                <li key={e.id} className="flex items-center gap-2 px-2 py-1.5">
                  <Identifier value={e.identifier} to={`/experiments/${e.identifier}`} />
                  <span className="flex-1 truncate text-xs text-fg-muted">{e.title}</span>
                  <ExperimentStatusBadge status={e.status} />
                  {!locked ? (
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Unlink ${e.identifier}`}
                      onClick={() => unlinkExp.mutate(e.identifier)}
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
              aria-label="Link experiment"
              onChange={(e) => {
                if (!e.target.value) return;
                setError(null);
                linkExp.mutate(e.target.value, { onError: (err) => setError(describeError(err)) });
              }}
            >
              <option value="">Link an experiment…</option>
              {(experiments.data?.items ?? [])
                .filter((e) => !linkedExp.has(e.id))
                .map((e) => (
                  <option key={e.id} value={e.identifier}>
                    {e.identifier} · {e.title}
                  </option>
                ))}
            </Select>
          ) : null}
        </div>
        <div>
          <div className="label mb-1">Test runs</div>
          {change.test_runs.length === 0 ? (
            <p className="text-xs text-fg-subtle">None linked.</p>
          ) : (
            <ul className="divide-y divide-border rounded border border-border">
              {change.test_runs.map((r) => (
                <li key={r.id} className="flex items-center gap-2 px-2 py-1.5">
                  <Identifier value={r.identifier} to={`/testing/${r.identifier}`} />
                  <span className="flex-1 truncate text-xs text-fg-muted">
                    {r.test_type.name}
                    {r.title ? ` · ${r.title}` : ""}
                  </span>
                  <span className="text-xs text-fg-subtle">{formatDateTime(r.performed_at)}</span>
                  {!locked ? (
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Unlink ${r.identifier}`}
                      onClick={() => unlinkRun.mutate(r.identifier)}
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
              aria-label="Link test run"
              onChange={(e) => {
                if (!e.target.value) return;
                setError(null);
                linkRun.mutate(e.target.value, { onError: (err) => setError(describeError(err)) });
              }}
            >
              <option value="">Link a test run…</option>
              {(runs.data?.items ?? [])
                .filter((r) => !linkedRuns.has(r.id))
                .map((r) => (
                  <option key={r.id} value={r.identifier}>
                    {r.identifier} · {r.test_type.name}
                    {r.title ? ` · ${r.title}` : ""}
                  </option>
                ))}
            </Select>
          ) : null}
        </div>
        <FormError message={error} />
        {locked ? (
          <p className="text-2xs text-fg-subtle">
            Links are fixed once a change is implemented or rejected.
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
