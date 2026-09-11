import { CHANGE_STATUSES, type ChangeStatus } from "@nemeth/domain-types";
import { GitBranch, Plus } from "lucide-react";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { Identifier, PlaceholderBadge } from "@/components/domain/badges";
import { ChangeStatusBadge } from "@/components/domain/changeBadges";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Field, FormError, Input, Select, Textarea } from "@/components/ui/form";
import { EmptyState, ErrorNotice, LoadingRows, PageHeader } from "@/components/ui/layout";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { describeError } from "@/lib/api";
import { useChanges, useCreateChange } from "@/lib/changeQueries";
import { formatDate, formOptional, formText, titleCase } from "@/lib/format";

export function ChangesPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const [creating, setCreating] = useState(false);
  const filters = {
    q: params.get("q") ?? "",
    status: (params.get("status") as ChangeStatus | null) ?? undefined,
  };
  const changes = useChanges(filters);

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  }

  return (
    <div>
      <PageHeader
        eyebrow="Manufacturing & quality"
        title="Engineering changes"
        description="Why a revision became the next one. Each record names the affected revisions, the proposed revisions, and the experiments and test runs that justify the change."
        actions={
          <Button variant="primary" onClick={() => setCreating((v) => !v)}>
            <Plus className="h-3.5 w-3.5" /> New change
          </Button>
        }
      />
      {creating ? <NewChangeForm onDone={() => setCreating(false)} /> : null}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Input
          placeholder="Search identifier or title"
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
          {CHANGE_STATUSES.map((s) => (
            <option key={s} value={s}>
              {titleCase(s)}
            </option>
          ))}
        </Select>
        {changes.data ? (
          <span className="ml-auto font-mono text-xs text-fg-subtle">
            {changes.data.total} changes
          </span>
        ) : null}
      </div>
      {changes.isError ? <ErrorNotice error={changes.error} /> : null}
      <Card>
        {changes.isLoading ? (
          <LoadingRows />
        ) : changes.data && changes.data.items.length > 0 ? (
          <Table>
            <THead>
              <TR>
                <TH className="w-24">Change</TH>
                <TH>Title</TH>
                <TH className="w-28">Status</TH>
                <TH className="w-48">From → To</TH>
                <TH className="w-24">Evidence</TH>
                <TH className="w-32">Requested by</TH>
                <TH className="w-28">Approved</TH>
              </TR>
            </THead>
            <TBody>
              {changes.data.items.map((c) => {
                const from = c.revisions.filter((r) => r.role === "AFFECTED");
                const to = c.revisions.filter((r) => r.role === "PROPOSED");
                return (
                  <TR key={c.id} interactive onClick={() => navigate(`/changes/${c.identifier}`)}>
                    <TD>
                      <Identifier value={c.identifier} />
                    </TD>
                    <TD className="font-medium">
                      <span className="inline-flex items-center gap-2">
                        {c.title}
                        <PlaceholderBadge show={c.is_placeholder} />
                      </span>
                    </TD>
                    <TD>
                      <ChangeStatusBadge status={c.status} />
                    </TD>
                    <TD mono className="text-fg-muted">
                      {from
                        .map((r) => `${r.component.identifier} ${r.revision.revision_label}`)
                        .join(", ") || "—"}
                      {" → "}
                      {to.map((r) => r.revision.revision_label).join(", ") || "—"}
                    </TD>
                    <TD mono className="text-fg-muted">
                      {c.experiments.length + c.test_runs.length || "—"}
                    </TD>
                    <TD className="text-fg-muted">{c.requested_by}</TD>
                    <TD className="text-fg-subtle">{formatDate(c.approved_on)}</TD>
                  </TR>
                );
              })}
            </TBody>
          </Table>
        ) : (
          <EmptyState
            icon={GitBranch}
            title="No engineering changes"
            description="Open one when a revision needs to become the next revision for a reason worth recording."
            className="m-4"
          />
        )}
      </Card>
    </div>
  );
}

function NewChangeForm({ onDone }: { onDone: () => void }) {
  const create = useCreateChange();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const fd = new FormData(event.currentTarget);
    create.mutate(
      {
        title: formText(fd, "title"),
        reason: formOptional(fd, "reason"),
        description: formOptional(fd, "description"),
      },
      {
        onSuccess: (c) => {
          onDone();
          navigate(`/changes/${c.identifier}`);
        },
        onError: (err) => setError(describeError(err)),
      },
    );
  }

  return (
    <Card className="mb-4">
      <CardHeader eyebrow="New" title="Engineering change" />
      <CardContent>
        <form onSubmit={onSubmit} className="grid gap-3">
          <Field label="Title" htmlFor="c-title">
            <Input
              id="c-title"
              name="title"
              required
              placeholder="Increase clearance between third wheel and bridge"
            />
          </Field>
          <Field label="Reason" htmlFor="c-reason">
            <Textarea
              id="c-reason"
              name="reason"
              className="min-h-[3rem]"
              placeholder="Intermittent contact observed in prototype P004."
            />
          </Field>
          <Field label="Description" htmlFor="c-desc">
            <Textarea id="c-desc" name="description" className="min-h-[3rem]" />
          </Field>
          <FormError message={error} />
          <div className="flex gap-2">
            <Button type="submit" variant="primary" disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create change"}
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
