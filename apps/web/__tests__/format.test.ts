import { describe, expect, it } from "vitest";
import { fiscalLabel, fmtBp, fmtNum, fmtPct } from "../lib/format";

describe("format", () => {
  it("groups Indian style and uses a real minus", () => {
    expect(fmtNum(145463)).toBe("1,45,463");
    expect(fmtNum(-668)).toBe("−668");
    expect(fmtNum(12.34)).toBe("12.3");
    expect(fmtNum(null)).toBe("—");
  });
  it("signs percentages and basis points", () => {
    expect(fmtPct(4.1)).toBe("+4.1%");
    expect(fmtPct(-2.3)).toBe("−2.3%");
    expect(fmtPct(13.4, false)).toBe("13.4%");
    expect(fmtBp(-86)).toBe("−86 bp");
    expect(fmtBp(null)).toBe("—");
  });
  it("maps quarter-end months to Indian fiscal quarters", () => {
    expect(fiscalLabel("2026-09")).toBe("Q2 FY27");
    expect(fiscalLabel("2026-06")).toBe("Q1 FY27");
    expect(fiscalLabel("2026-03")).toBe("Q4 FY26");
    expect(fiscalLabel("2025-12")).toBe("Q3 FY26");
  });
});
