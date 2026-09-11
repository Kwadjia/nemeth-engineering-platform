import { EXPERIMENT_STATUSES, type ExperimentStatus } from "@nemeth/domain-types";
import { FlaskConical, Plus } from "lucide-react";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { Identifier, PlaceholderBadge } from "@/components/domain/badges";
import { ExperimentStatusBadge, OutcomeBadge } from "@/components/domain/experimentBadges";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Field, FormError, Input, Select, Textarea } from "@/components/ui/form";
import { EmptyState, ErrorNotice, LoadingRows, PageHeader } from "@/components/ui/layout";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { describeError } from "@/lib/api";
import { useCreateExperiment, useExperiments } from "@/lib/experimentQueries";
import { formatDate, formOptional, formText, titleCase } from "@/lib/format";

export function ExperimentsPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const [creating, setCreating] = useState(false);
  const filters = {
    q: params.get("q") ?? "",
    status: (params.get("status") as ExperimentStatus | null) ?? undefined,
  };
  const experiments = useExperiments(filters);

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
        title="Experiments"
        description="Hypothesis, procedure, observations, conclusion. Watchmaking development recorded like iterative product development, linked to the prototypes and revisions involved."
        actions={
          <Button variant="primary" onClick={() => setCreating((v) => !v)}>
            <Plus className="h-3.5 w-3.5" /> New experiment
          </Button>
        }
      />
      {creating ? <NewExperimentForm onDone={() => setCreating(false)} /> : null}

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
          {EXPERIMENT_STATUSES.map((s) => (
            <option key={s} value={s}>
              {titleCase(s)}
            </option>
          ))}
        </Select>
        {experiments.data ? (
          <span className="ml-auto font-mono text-xs text-fg-subtle">
            {experiments.data.total} experiments
          </span>
        ) : null}
      </div>

      {experiments.isError ? <ErrorNotice error={experiments.error} /> : null}
      <Card>
        {experiments.isLoading ? (
          <LoadingRows />
        ) : experiments.data && experiments.data.items.length > 0 ? (
          <Table>
            <THead>
              <TR>
                <TH className="w-24">Experiment</TH>
                <TH>Title</TH>
                <TH className="w-28">Status</TH>
                <TH className="w-28">Outcome</TH>
                <TH className="w-32">Prototypes</TH>
                <TH className="w-28">Started</TH>
                <TH className="w-28">Completed</TH>
              </TR>
            </THead>
            <TBody>
              {experiments.data.items.map((e) => (
                <TR key={e.id} interactive onClick={() => navigate(`/experiments/${e.identifier}`)}>
                  <TD>
                    <Identifier value={e.identifier} />
                  </TD>
                  <TD className="font-medium">
                    <span className="inline-flex items-center gap-2">
                      {e.title}
                      <PlaceholderBadge show={e.is_placeholder} />
                    </span>
                  </TD>
                  <TD>
                    <ExperimentStatusBadge status={e.status} />
                  </TD>
                  <TD>
                    <OutcomeBadge outcome={e.outcome} />
                  </TD>
                  <TD mono className="text-fg-muted">
                    {e.prototypes.map((l) => l.prototype.identifier).join(", ") || "—"}
                  </TD>
                  <TD className="text-fg-subtle">{formatDate(e.started_on)}</TD>
                  <TD className="text-fg-subtle">{formatDate(e.completed_on)}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        ) : (
          <EmptyState
            icon={FlaskConical}
            title="No experiments"
            description="Start with a hypothesis."
            className="m-4"
          />
        )}
      </Card>
    </div>
  );
}

function NewExperimentForm({ onDone }: { onDone: () => void }) {
  const create = useCreateExperiment();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const fd = new FormData(event.currentTarget);
    create.mutate(
      {
        title: formText(fd, "title"),
        objective: formOptional(fd, "objective"),
        hypothesis: formOptional(fd, "hypothesis"),
        started_on: formOptional(fd, "started_on"),
      },
      {
        onSuccess: (e) => {
          onDone();
          navigate(`/experiments/${e.identifier}`);
        },
        onError: (err) => setError(describeError(err)),
      },
    );
  }

  return (
    <Card className="mb-4">
      <CardHeader eyebrow="New" title="Experiment" />
      <CardContent>
        <form onSubmit={onSubmit} className="grid gap-3 sm:grid-cols-[1fr_10rem]">
          <Field label="Title" htmlFor="e-title">
            <Input
              id="e-title"
              name="title"
              required
              placeholder="Effect of barrel arbor endshake on amplitude"
            />
          </Field>
          <Field label="Started on" htmlFor="e-started">
            <Input id="e-started" name="started_on" type="date" className="font-mono" />
          </Field>
          <Field label="Objective" htmlFor="e-objective" className="sm:col-span-2">
            <Textarea id="e-objective" name="objective" className="min-h-[3rem]" />
          </Field>
          <Field label="Hypothesis" htmlFor="e-hypothesis" className="sm:col-span-2">
            <Textarea
              id="e-hypothesis"
              name="hypothesis"
              className="min-h-[3rem]"
              placeholder="Increasing endshake by 0.015 mm will reduce friction and increase amplitude."
            />
          </Field>
          <div className="sm:col-span-2">
            <FormError message={error} />
          </div>
          <div className="flex gap-2 sm:col-span-2">
            <Button type="submit" variant="primary" disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create experiment"}
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
