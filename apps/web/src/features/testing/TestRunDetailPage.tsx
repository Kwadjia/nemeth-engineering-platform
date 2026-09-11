import { TEST_OUTCOMES, type TestOutcome, type TestRunRead } from "@nemeth/domain-types";
import { Plus } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { AttachmentsPanel } from "@/components/domain/AttachmentsPanel";
import { Identifier, PlaceholderBadge } from "@/components/domain/badges";
import { OutcomeBadgeTest, TestTypeBadge } from "@/components/domain/testingBadges";
import { TimingTable } from "@/components/domain/TimingTable";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Field, FormError, Input, Select, Textarea } from "@/components/ui/form";
import { EmptyState, ErrorNotice, KV, LoadingRows, PageHeader } from "@/components/ui/layout";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { describeError } from "@/lib/api";
import { displayValue, formatDateTime, formatQuantity, formOptional, formText } from "@/lib/format";
import { useAddMeasurements, useTestRun, useUpdateTestRun } from "@/lib/testingQueries";

export function TestRunDetailPage() {
  const { ref = "" } = useParams();
  const run = useTestRun(ref);

  if (run.isLoading) return <LoadingRows />;
  if (run.isError) return <ErrorNotice error={run.error} />;
  if (!run.data) return null;
  const r = run.data;

  return (
    <div>
      <PageHeader
        eyebrow={
          <span>
            <Link to="/testing" className="hover:underline">
              Testing
            </Link>{" "}
            / {r.identifier}
          </span>
        }
        title={
          <>
            <Identifier value={r.identifier} className="text-xl" />
            <span>{r.title ?? r.test_type.name}</span>
          </>
        }
        meta={
          <>
            <TestTypeBadge code={r.test_type.code} name={r.test_type.name} />
            <OutcomeBadgeTest outcome={r.outcome} />
            <PlaceholderBadge show={r.is_placeholder} />
            <span className="text-xs text-fg-subtle">
              {formatDateTime(r.performed_at)} · {r.performed_by}
            </span>
          </>
        }
        actions={<OutcomeControl run={r} />}
      />

      <div className="grid gap-4 xl:grid-cols-3">
        <div className="grid gap-4 xl:col-span-2">
          {r.timing ? (
            <Card>
              <CardHeader eyebrow="Timegrapher" title="Timing summary" />
              <CardContent>
                <TimingTable timing={r.timing} />
              </CardContent>
            </Card>
          ) : null}
          <Card>
            <CardHeader eyebrow="Long format · one row per observation" title="Measurements" />
            {r.measurements.length > 0 ? (
              <Table>
                <THead>
                  <TR>
                    <TH className="w-10" align="right">
                      #
                    </TH>
                    <TH>Metric</TH>
                    <TH className="w-28" align="right">
                      Value
                    </TH>
                    <TH className="w-20">Unit</TH>
                    <TH className="w-20">Position</TH>
                    <TH className="w-40">Recorded</TH>
                    <TH>Notes</TH>
                  </TR>
                </THead>
                <TBody>
                  {r.measurements.map((m) => (
                    <TR key={m.id}>
                      <TD align="right" mono className="text-fg-subtle">
                        {m.sequence}
                      </TD>
                      <TD mono>{m.metric}</TD>
                      <TD align="right" mono className="text-fg">
                        {formatQuantity(m.value)}
                      </TD>
                      <TD className="text-fg-muted">{m.unit ?? "—"}</TD>
                      <TD mono className="text-fg-muted">
                        {m.position ?? "—"}
                      </TD>
                      <TD className="text-fg-subtle">{formatDateTime(m.recorded_at)}</TD>
                      <TD className="text-fg-muted">
                        {m.notes ?? (m.extra ? displayValue(m.extra) : "—")}
                      </TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            ) : (
              <CardContent>
                <EmptyState
                  title="No measurements"
                  description="Append observations below."
                  className="py-6"
                />
              </CardContent>
            )}
          </Card>
          <AppendForm run={r} />
          <AttachmentsPanel entityType="test_run" entityId={r.id} defaultKind="TEST_RESULT" />
        </div>
        <Card className="self-start">
          <CardHeader eyebrow="Record" title="Details" />
          <CardContent>
            <KV
              columns={1}
              items={[
                {
                  label: "Subject",
                  value: r.prototype ? (
                    <Identifier
                      value={r.prototype.identifier}
                      to={`/prototypes/${r.prototype.identifier}`}
                    />
                  ) : r.part_instance ? (
                    <Identifier
                      value={r.part_instance.identifier}
                      to={`/part-instances?q=${r.part_instance.identifier}`}
                    />
                  ) : r.component && r.revision ? (
                    <Identifier
                      value={`${r.component.identifier} Rev ${r.revision.revision_label}`}
                      to={`/components/${r.component.identifier}/revisions/${r.revision.revision_label}`}
                    />
                  ) : null,
                },
                {
                  label: "Experiment",
                  value: r.experiment ? (
                    <Identifier
                      value={r.experiment.identifier}
                      to={`/experiments/${r.experiment.identifier}`}
                    />
                  ) : null,
                },
                { label: "Equipment", value: r.equipment },
                {
                  label: "Conditions",
                  value: r.conditions ? displayValue(r.conditions) : null,
                  mono: true,
                },
                { label: "Notes", value: r.notes },
                { label: "Created", value: `${formatDateTime(r.created_at)} · ${r.created_by}` },
                { label: "Internal id", value: r.id, mono: true },
              ]}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function OutcomeControl({ run }: { run: TestRunRead }) {
  const update = useUpdateTestRun(run.identifier);
  const [error, setError] = useState<string | null>(null);
  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center gap-2">
        <span className="label">Outcome</span>
        <Select
          value={run.outcome}
          aria-label="Outcome"
          className="w-28"
          disabled={update.isPending}
          onChange={(e) => {
            setError(null);
            update.mutate(
              { outcome: e.target.value as TestOutcome },
              { onError: (err) => setError(describeError(err)) },
            );
          }}
        >
          {TEST_OUTCOMES.map((o) => (
            <option key={o} value={o}>
              {o === "INFO" ? "Info" : o === "PASS" ? "Pass" : "Fail"}
            </option>
          ))}
        </Select>
      </div>
      <FormError message={error} />
    </div>
  );
}

function AppendForm({ run }: { run: TestRunRead }) {
  const add = useAddMeasurements(run.identifier);
  const [error, setError] = useState<string | null>(null);

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const form = event.currentTarget;
    const fd = new FormData(form);
    add.mutate(
      [
        {
          metric: formText(fd, "metric"),
          value: formText(fd, "value"),
          unit: formOptional(fd, "unit"),
          position: formOptional(fd, "position"),
          notes: formOptional(fd, "notes"),
        },
      ],
      { onSuccess: () => form.reset(), onError: (err) => setError(describeError(err)) },
    );
  }

  return (
    <Card>
      <CardHeader eyebrow="Append" title="Add a measurement" />
      <CardContent>
        <form
          onSubmit={onSubmit}
          className="grid items-end gap-3 sm:grid-cols-[1fr_8rem_6rem_6rem_1fr_auto]"
        >
          <Field label="Metric" htmlFor="a-metric">
            <Input
              id="a-metric"
              name="metric"
              required
              className="font-mono"
              placeholder="rate_sec_day"
            />
          </Field>
          <Field label="Value" htmlFor="a-value">
            <Input id="a-value" name="value" required inputMode="decimal" className="font-mono" />
          </Field>
          <Field label="Unit" htmlFor="a-unit">
            <Input id="a-unit" name="unit" />
          </Field>
          <Field label="Position" htmlFor="a-pos">
            <Input id="a-pos" name="position" className="font-mono uppercase" />
          </Field>
          <Field label="Notes" htmlFor="a-notes">
            <Textarea id="a-notes" name="notes" className="min-h-[2rem]" />
          </Field>
          <Button type="submit" variant="primary" disabled={add.isPending}>
            <Plus className="h-3.5 w-3.5" /> {add.isPending ? "Adding…" : "Add"}
          </Button>
        </form>
        <div className="mt-2">
          <FormError message={error} />
        </div>
      </CardContent>
    </Card>
  );
}
