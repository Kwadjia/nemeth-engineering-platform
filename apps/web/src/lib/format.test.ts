import { describe, expect, it } from "vitest";

import { formatQuantity, pluralize, revisionLabel, titleCase } from "./format";

describe("formatQuantity", () => {
  it("trims trailing zeros from decimal strings without rounding", () => {
    expect(formatQuantity("2.0000")).toBe("2");
    expect(formatQuantity("0.0150")).toBe("0.015");
    expect(formatQuantity("12")).toBe("12");
    expect(formatQuantity(3)).toBe("3");
  });

  it("returns an em dash for missing values and passes through non-numeric text", () => {
    expect(formatQuantity(null)).toBe("—");
    expect(formatQuantity("")).toBe("—");
    expect(formatQuantity("±0.01")).toBe("±0.01");
  });
});

describe("labels", () => {
  it("builds revision labels and title-cases enums", () => {
    expect(revisionLabel("N1-MVT-002", "C")).toBe("N1-MVT-002 Rev C");
    expect(titleCase("PROTOTYPE")).toBe("Prototype");
    expect(titleCase("WIRE_EDM")).toBe("Wire Edm");
    expect(pluralize(1, "line")).toBe("1 line");
    expect(pluralize(3, "line")).toBe("3 lines");
  });
});
