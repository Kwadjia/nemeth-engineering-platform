import type { TimingSummary } from "@nemeth/domain-types";

import { Stat } from "@/components/ui/layout";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { formatNumber, formatQuantity } from "@/lib/format";

/** Per-position timegrapher readings and the derived figures a watchmaker looks at first. */
export function TimingTable({ timing }: { timing: TimingSummary }) {
  const signed = (v: string | null | undefined) => {
    if (v === null || v === undefined) return "—";
    const text = formatQuantity(v);
    return text.startsWith("-") ? text : `+${text}`;
  };
  return (
    <div className="grid gap-3" data-testid="timing-table">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        <Stat label="Mean rate" value={`${signed(timing.mean_rate_sec_day)} s/d`} />
        <Stat
          label="Delta"
          value={formatNumber(timing.delta_sec_day, "s/d")}
          hint="max − min rate"
        />
        <Stat
          label="Amplitude"
          value={
            timing.min_amplitude_deg
              ? `${formatQuantity(timing.min_amplitude_deg)}–${formatQuantity(timing.max_amplitude_deg)}°`
              : "—"
          }
          hint="min–max across positions"
        />
        <Stat label="Max beat error" value={formatNumber(timing.max_beat_error_ms, "ms")} />
        <Stat label="Lift angle" value={formatNumber(timing.lift_angle_deg, "°")} />
      </div>
      <Table>
        <THead>
          <TR>
            <TH className="w-16">Pos</TH>
            <TH>Position</TH>
            <TH className="w-28" align="right">
              Rate s/d
            </TH>
            <TH className="w-28" align="right">
              Amplitude °
            </TH>
            <TH className="w-28" align="right">
              Beat error ms
            </TH>
          </TR>
        </THead>
        <TBody>
          {timing.positions.map((p) => (
            <TR key={p.position}>
              <TD mono className="font-medium">
                {p.position}
              </TD>
              <TD className="text-fg-muted">{p.label}</TD>
              <TD align="right" mono>
                {signed(p.rate_sec_day)}
              </TD>
              <TD align="right" mono>
                {formatQuantity(p.amplitude_deg)}
              </TD>
              <TD align="right" mono>
                {formatQuantity(p.beat_error_ms)}
              </TD>
            </TR>
          ))}
        </TBody>
      </Table>
    </div>
  );
}
