import type { TimingSummary } from "@nemeth/domain-types";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TimingTable } from "./TimingTable";

const timing: TimingSummary = {
  positions: [
    {
      position: "DU",
      label: "Dial up",
      rate_sec_day: "2.8",
      amplitude_deg: "287",
      beat_error_ms: "0.1",
    },
    {
      position: "CU",
      label: "Crown up",
      rate_sec_day: "-1.2",
      amplitude_deg: "252",
      beat_error_ms: "0.3",
    },
  ],
  mean_rate_sec_day: "0.8",
  delta_sec_day: "4.0",
  min_amplitude_deg: "252",
  max_amplitude_deg: "287",
  max_beat_error_ms: "0.3",
  lift_angle_deg: "44",
};

describe("TimingTable", () => {
  it("shows signed rates per position and the derived figures", () => {
    render(<TimingTable timing={timing} />);
    expect(screen.getByText("+2.8")).toBeInTheDocument();
    expect(screen.getByText("-1.2")).toBeInTheDocument();
    expect(screen.getByText("Dial up")).toBeInTheDocument();
    expect(screen.getByText("+0.8 s/d")).toBeInTheDocument();
    expect(screen.getByText("4 s/d")).toBeInTheDocument();
    expect(screen.getByText("252–287°")).toBeInTheDocument();
    expect(screen.getByText("44 °")).toBeInTheDocument();
  });
});
