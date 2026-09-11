import type { TestRunRead } from "@nemeth/domain-types";
import { useNavigate } from "react-router-dom";

import { Identifier, PlaceholderBadge } from "@/components/domain/badges";
import { OutcomeBadgeTest, TestTypeBadge } from "@/components/domain/testingBadges";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { formatDateTime, formatQuantity } from "@/lib/format";

function subjectOf(run: TestRunRead): { label: string; to?: string } {
  if (run.prototype)
    return { label: run.prototype.identifier, to: `/prototypes/${run.prototype.identifier}` };
  if (run.part_instance)
    return {
      label: run.part_instance.identifier,
      to: `/part-instances?q=${run.part_instance.identifier}`,
    };
  if (run.component && run.revision)
    return {
      label: `${run.component.identifier} Rev ${run.revision.revision_label}`,
      to: `/components/${run.component.identifier}/revisions/${run.revision.revision_label}`,
    };
  return { label: "—" };
}

function headline(run: TestRunRead): string {
  if (
    run.timing &&
    run.timing.mean_rate_sec_day !== null &&
    run.timing.mean_rate_sec_day !== undefined
  ) {
    const rate = formatQuantity(run.timing.mean_rate_sec_day);
    const amp = run.timing.min_amplitude_deg
      ? `${formatQuantity(run.timing.min_amplitude_deg)}–${formatQuantity(run.timing.max_amplitude_deg)}°`
      : "";
    return `${rate.startsWith("-") ? rate : `+${rate}`} s/d · Δ ${formatQuantity(run.timing.delta_sec_day)} · ${amp}`;
  }
  const first = run.measurements[0];
  if (first)
    return `${run.measurements.length} measurement${run.measurements.length === 1 ? "" : "s"}`;
  return run.notes ? run.notes.slice(0, 60) : "—";
}

export function TestRunsTable({
  runs,
  showSubject = true,
}: {
  runs: TestRunRead[];
  showSubject?: boolean;
}) {
  const navigate = useNavigate();
  return (
    <Table>
      <THead>
        <TR>
          <TH className="w-24">Run</TH>
          <TH className="w-36">Type</TH>
          <TH>Title</TH>
          {showSubject ? <TH className="w-40">Subject</TH> : null}
          <TH className="w-24">Experiment</TH>
          <TH>Headline</TH>
          <TH className="w-20">Outcome</TH>
          <TH className="w-40">Performed</TH>
        </TR>
      </THead>
      <TBody>
        {runs.map((run) => {
          const subject = subjectOf(run);
          return (
            <TR key={run.id} interactive onClick={() => navigate(`/testing/${run.identifier}`)}>
              <TD>
                <span className="inline-flex items-center gap-2">
                  <Identifier value={run.identifier} />
                  <PlaceholderBadge show={run.is_placeholder} />
                </span>
              </TD>
              <TD>
                <TestTypeBadge code={run.test_type.code} name={run.test_type.name} />
              </TD>
              <TD className="text-fg">{run.title ?? "—"}</TD>
              {showSubject ? (
                <TD>
                  {subject.to ? (
                    <Identifier value={subject.label} to={subject.to} />
                  ) : (
                    <span className="text-fg-subtle">—</span>
                  )}
                </TD>
              ) : null}
              <TD>
                {run.experiment ? (
                  <Identifier
                    value={run.experiment.identifier}
                    to={`/experiments/${run.experiment.identifier}`}
                  />
                ) : (
                  <span className="text-fg-subtle">—</span>
                )}
              </TD>
              <TD mono className="text-fg-muted">
                {headline(run)}
              </TD>
              <TD>
                <OutcomeBadgeTest outcome={run.outcome} />
              </TD>
              <TD className="text-fg-subtle">{formatDateTime(run.performed_at)}</TD>
            </TR>
          );
        })}
      </TBody>
    </Table>
  );
}
