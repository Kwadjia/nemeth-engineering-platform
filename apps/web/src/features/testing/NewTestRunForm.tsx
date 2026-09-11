import {
  POSITIONS,
  TEST_OUTCOMES,
  type MeasurementCreate,
  type TestOutcome,
  type TestTypeRead,
} from "@nemeth/domain-types";
import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Field, FormError, Input, Select, Textarea } from "@/components/ui/form";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { describeError } from "@/lib/api";
import { useExperiments } from "@/lib/experimentQueries";
import { formOptional, formText } from "@/lib/format";
import { usePrototypes } from "@/lib/prototypeQueries";
import { useCreateTestRun, useTestTypes } from "@/lib/testingQueries";

interface Row {
  key: number;
  metric: string;
  value: string;
  unit: string;
  position: string;
}

const TIMEGRAPHER_METRICS = ["rate_sec_day", "amplitude_deg", "beat_error_ms"] as const;

export function NewTestRunForm({
  onDone,
  defaultPrototype,
  defaultExperiment,
}: {
  onDone: () => void;
  defaultPrototype?: string;
  defaultExperiment?: string;
}) {
  const types = useTestTypes();
  const prototypes = usePrototypes();
  const experiments = useExperiments({});
  const create = useCreateTestRun();
  const navigate = useNavigate();
  const [typeCode, setTypeCode] = useState("TIMEGRAPHER");
  const [rows, setRows] = useState<Row[]>([]);
  const [nextKey, setNextKey] = useState(1);
  const [grid, setGrid] = useState<Record<string, Record<string, string>>>({});
  const [liftAngle, setLiftAngle] = useState("");
  const [error, setError] = useState<string | null>(null);

  const type: TestTypeRead | undefined = types.data?.find((t) => t.code === typeCode);
  const isTimegrapher = typeCode === "TIMEGRAPHER";

  function addRow() {
    setRows((list) => [
      ...list,
      { key: nextKey, metric: type?.metrics[0]?.key ?? "", value: "", unit: "", position: "" },
    ]);
    setNextKey((k) => k + 1);
  }

  function gridMeasurements(): MeasurementCreate[] {
    const out: MeasurementCreate[] = [];
    if (liftAngle.trim()) out.push({ metric: "lift_angle_deg", value: liftAngle.trim() });
    for (const p of POSITIONS) {
      const cells = grid[p.code] ?? {};
      for (const metric of TIMEGRAPHER_METRICS) {
        const v = cells[metric]?.trim();
        if (v) out.push({ metric, value: v, position: p.code });
      }
    }
    return out;
  }

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const fd = new FormData(event.currentTarget);
    const measurements: MeasurementCreate[] = isTimegrapher
      ? gridMeasurements()
      : rows
          .filter((r) => r.metric.trim() && r.value.trim())
          .map((r) => ({
            metric: r.metric.trim(),
            value: r.value.trim(),
            unit: r.unit.trim() || null,
            position: r.position.trim() || null,
          }));
    const temperature = formText(fd, "temperature_c");
    const wind = formText(fd, "state_of_wind");
    const conditions: Record<string, unknown> = {};
    if (temperature) conditions.temperature_c = Number(temperature);
    if (wind) conditions.state_of_wind = wind;
    create.mutate(
      {
        test_type_code: typeCode,
        title: formOptional(fd, "title"),
        prototype_ref: formOptional(fd, "prototype_ref"),
        experiment_ref: formOptional(fd, "experiment_ref"),
        performed_at: formOptional(fd, "performed_at"),
        performed_by: formOptional(fd, "performed_by"),
        equipment: formOptional(fd, "equipment"),
        conditions: Object.keys(conditions).length ? conditions : null,
        outcome: (formText(fd, "outcome") || "INFO") as TestOutcome,
        notes: formOptional(fd, "notes"),
        measurements,
      },
      {
        onSuccess: (run) => {
          onDone();
          navigate(`/testing/${run.identifier}`);
        },
        onError: (err) => setError(describeError(err)),
      },
    );
  }

  const nowLocal = new Date(Date.now() - new Date().getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);

  return (
    <Card className="mb-4">
      <CardHeader eyebrow="New" title="Test run" />
      <CardContent>
        <form onSubmit={onSubmit} className="grid gap-4">
          <div className="grid gap-3 sm:grid-cols-4">
            <Field label="Test type" htmlFor="t-type">
              <Select
                id="t-type"
                value={typeCode}
                onChange={(e) => {
                  setTypeCode(e.target.value);
                  setRows([]);
                }}
              >
                {(types.data ?? []).map((t) => (
                  <option key={t.id} value={t.code}>
                    {t.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Prototype" htmlFor="t-proto" hint="the subject, if any">
              <Select id="t-proto" name="prototype_ref" defaultValue={defaultPrototype ?? ""}>
                <option value="">None</option>
                {(prototypes.data?.items ?? []).map((p) => (
                  <option key={p.id} value={p.identifier}>
                    {p.identifier} · {p.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Experiment" htmlFor="t-exp">
              <Select id="t-exp" name="experiment_ref" defaultValue={defaultExperiment ?? ""}>
                <option value="">None</option>
                {(experiments.data?.items ?? []).map((e) => (
                  <option key={e.id} value={e.identifier}>
                    {e.identifier} · {e.title}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Outcome" htmlFor="t-outcome">
              <Select id="t-outcome" name="outcome" defaultValue="INFO">
                {TEST_OUTCOMES.map((o) => (
                  <option key={o} value={o}>
                    {o === "INFO" ? "Info" : o === "PASS" ? "Pass" : "Fail"}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Title" htmlFor="t-title" className="sm:col-span-2">
              <Input id="t-title" name="title" placeholder="Baseline after cleaning" />
            </Field>
            <Field label="Performed at" htmlFor="t-at">
              <Input
                id="t-at"
                name="performed_at"
                type="datetime-local"
                defaultValue={nowLocal}
                className="font-mono"
              />
            </Field>
            <Field label="Performed by" htmlFor="t-by" hint="defaults to you">
              <Input id="t-by" name="performed_by" />
            </Field>
            <Field label="Equipment" htmlFor="t-equipment" className="sm:col-span-2">
              <Input id="t-equipment" name="equipment" placeholder="Weishi 1000" />
            </Field>
            <Field label="Temperature °C" htmlFor="t-temp">
              <Input id="t-temp" name="temperature_c" inputMode="decimal" className="font-mono" />
            </Field>
            <Field label="State of wind" htmlFor="t-wind">
              <Input id="t-wind" name="state_of_wind" placeholder="full / 24 h" />
            </Field>
          </div>

          {isTimegrapher ? (
            <div className="rounded border border-border bg-bg-elevated p-3">
              <div className="mb-2 flex items-end justify-between gap-3">
                <div className="label">Readings per position</div>
                <Field label="Lift angle °" htmlFor="t-lift" className="w-32">
                  <Input
                    id="t-lift"
                    value={liftAngle}
                    onChange={(e) => setLiftAngle(e.target.value)}
                    inputMode="decimal"
                    className="font-mono"
                    placeholder="44"
                  />
                </Field>
              </div>
              <Table>
                <THead>
                  <TR>
                    <TH className="w-16">Pos</TH>
                    <TH>Position</TH>
                    <TH className="w-32">Rate s/d</TH>
                    <TH className="w-32">Amplitude °</TH>
                    <TH className="w-32">Beat error ms</TH>
                  </TR>
                </THead>
                <TBody>
                  {POSITIONS.map((p) => (
                    <TR key={p.code}>
                      <TD mono className="font-medium">
                        {p.code}
                      </TD>
                      <TD className="text-fg-muted">{p.label}</TD>
                      {TIMEGRAPHER_METRICS.map((metric) => (
                        <TD key={metric}>
                          <Input
                            aria-label={`${p.code} ${metric}`}
                            inputMode="decimal"
                            className="font-mono"
                            value={grid[p.code]?.[metric] ?? ""}
                            onChange={(e) =>
                              setGrid((g) => ({
                                ...g,
                                [p.code]: { ...(g[p.code] ?? {}), [metric]: e.target.value },
                              }))
                            }
                          />
                        </TD>
                      ))}
                    </TR>
                  ))}
                </TBody>
              </Table>
              <p className="mt-2 text-2xs text-fg-subtle">
                Leave a cell empty to skip it. Rates are seconds per day, signed.
              </p>
            </div>
          ) : (
            <div className="rounded border border-border bg-bg-elevated p-3">
              <div className="mb-2 flex items-center justify-between">
                <div className="label">Measurements</div>
                <Button size="sm" onClick={addRow}>
                  <Plus className="h-3.5 w-3.5" /> Add measurement
                </Button>
              </div>
              {type && type.metrics.length > 0 ? (
                <p className="mb-2 text-2xs text-fg-subtle">
                  Metrics for {type.name}:{" "}
                  {type.metrics.map((m) => `${m.key}${m.unit ? ` (${m.unit})` : ""}`).join(", ")}
                  {type.allow_custom_metrics ? "; custom keys allowed." : "."}
                </p>
              ) : type?.allow_custom_metrics ? (
                <p className="mb-2 text-2xs text-fg-subtle">
                  Any metric key (lowercase, underscores), e.g. pivot_diameter_mm.
                </p>
              ) : (
                <p className="mb-2 text-2xs text-fg-subtle">
                  This test type records notes and an outcome; no numeric metrics.
                </p>
              )}
              {rows.length > 0 ? (
                <Table>
                  <THead>
                    <TR>
                      <TH>Metric</TH>
                      <TH className="w-32">Value</TH>
                      <TH className="w-24">Unit</TH>
                      <TH className="w-28">Position</TH>
                      <TH className="w-10" />
                    </TR>
                  </THead>
                  <TBody>
                    {rows.map((r) => (
                      <TR key={r.key}>
                        <TD>
                          {type && type.metrics.length > 0 && !type.allow_custom_metrics ? (
                            <Select
                              value={r.metric}
                              aria-label="Metric"
                              onChange={(e) =>
                                setRows((l) =>
                                  l.map((x) =>
                                    x.key === r.key ? { ...x, metric: e.target.value } : x,
                                  ),
                                )
                              }
                            >
                              {type.metrics.map((m) => (
                                <option key={m.key} value={m.key}>
                                  {m.label} ({m.key})
                                </option>
                              ))}
                            </Select>
                          ) : (
                            <Input
                              value={r.metric}
                              aria-label="Metric"
                              className="font-mono"
                              placeholder="metric_key"
                              onChange={(e) =>
                                setRows((l) =>
                                  l.map((x) =>
                                    x.key === r.key ? { ...x, metric: e.target.value } : x,
                                  ),
                                )
                              }
                            />
                          )}
                        </TD>
                        <TD>
                          <Input
                            value={r.value}
                            aria-label="Value"
                            inputMode="decimal"
                            className="font-mono"
                            onChange={(e) =>
                              setRows((l) =>
                                l.map((x) =>
                                  x.key === r.key ? { ...x, value: e.target.value } : x,
                                ),
                              )
                            }
                          />
                        </TD>
                        <TD>
                          <Input
                            value={r.unit}
                            aria-label="Unit"
                            placeholder={type?.metrics.find((m) => m.key === r.metric)?.unit ?? ""}
                            onChange={(e) =>
                              setRows((l) =>
                                l.map((x) =>
                                  x.key === r.key ? { ...x, unit: e.target.value } : x,
                                ),
                              )
                            }
                          />
                        </TD>
                        <TD>
                          <Input
                            value={r.position}
                            aria-label="Position"
                            placeholder={type?.uses_positions ? "DU" : ""}
                            className="font-mono uppercase"
                            onChange={(e) =>
                              setRows((l) =>
                                l.map((x) =>
                                  x.key === r.key ? { ...x, position: e.target.value } : x,
                                ),
                              )
                            }
                          />
                        </TD>
                        <TD align="right">
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label="Remove row"
                            onClick={() => setRows((l) => l.filter((x) => x.key !== r.key))}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              ) : null}
            </div>
          )}

          <Field label="Notes" htmlFor="t-notes">
            <Textarea id="t-notes" name="notes" className="min-h-[3rem]" />
          </Field>
          <FormError message={error} />
          <div className="flex gap-2">
            <Button type="submit" variant="primary" disabled={create.isPending}>
              {create.isPending ? "Saving…" : "Save test run"}
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
