const MINUS = "−";

export function fmtNum(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  const digits = Math.abs(v) >= 100 ? 0 : 1;
  const s = new Intl.NumberFormat("en-IN", { maximumFractionDigits: digits }).format(Math.abs(v));
  return v < 0 ? MINUS + s : s;
}

export function fmtPct(v: number | null | undefined, withSign = true): string {
  if (v === null || v === undefined) return "—";
  const s = Math.abs(v).toFixed(1) + "%";
  if (v < 0) return MINUS + s;
  return withSign && v > 0 ? "+" + s : s;
}

export function fmtBp(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  const s = Math.abs(v).toString() + " bp";
  return v < 0 ? MINUS + s : v > 0 ? "+" + s : s;
}

/** '2026-09' (quarter-end month) -> 'Q2 FY27'. Indian fiscal year ends in March. */
export function fiscalLabel(period: string): string {
  const [y, m] = period.split("-").map(Number);
  const fyEnd = m >= 4 ? y + 1 : y;
  const q = m >= 4 ? Math.floor((m - 4) / 3) + 1 : 4;
  return `Q${q} FY${String(fyEnd).slice(-2)}`;
}

const IST = "Asia/Kolkata";

export function fmtTimeIST(iso: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: IST,
  }).format(new Date(iso));
}

export function fmtDayIST(iso: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    timeZone: IST,
  })
    .format(new Date(iso))
    .replace(",", ",");
}

const LABELS: Record<string, string> = {
  results: "Results",
  "M&A": "M&A",
  fund_raise: "Fund raise",
  management_change: "Management change",
  litigation: "Litigation",
  insider_trading: "Insider trading",
  earnings_call: "Earnings call",
  investor_meetings: "Investor meetings",
  credit_rating: "Credit rating",
  dividend: "Dividend",
  bonus_split: "Bonus / split",
  capex: "Capex",
  press_release: "Press release",
  postal_ballot: "Postal ballot",
  agm_egm: "AGM / EGM",
  pledging: "Pledging",
  unclassified: "Routine",
};

export function categoryLabel(c: string | null): string {
  return c ? (LABELS[c] ?? c) : "Filing";
}
