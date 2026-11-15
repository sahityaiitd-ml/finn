export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Health = { status: string; service: string; db_configured: boolean };

export type ResultRow = {
  key: string;
  label: string;
  value: number | null;
  qoq_pct: number | null;
  yoy_pct: number | null;
  qoq_bp?: number | null;
  yoy_bp?: number | null;
  qoq_available: boolean;
  yoy_available: boolean;
  derived: boolean;
  page: number | null;
  line: string | null;
  unit?: string;
};

export type ResultsView = {
  symbol: string;
  name: string;
  period: string;
  status: "ok" | "see_pdf" | "unsupported";
  basis: string | null;
  message?: string;
  reason: string;
  flags: string[];
  notes?: { flag: string; text: string; page: number | null }[];
  source: { sha256: string; page: number | null };
  unit: string;
  rows: ResultRow[];
  exceptional: { value: number; page: number | null } | null;
};

export type DocPage = {
  sha256: string;
  page: number;
  n_pages: number;
  symbol: string;
  kind: string;
  period: string;
  text: string;
  highlight?: { start: number; end: number; score: number } | null;
};

export type DigestItem = {
  id: string;
  symbol: string;
  name: string;
  category: string | null;
  headline: string;
  summary: string | null;
  published_at: string;
  source_url: string | null;
  never_collapse: boolean;
  materiality: number;
  reviewed: boolean;
  alert?: AlertInfo;
};

export type AlertInfo = {
  triggered: string[];
  ratio: number;
  vol_mult: number;
  pct: number;
  price_pct: number;
  cause_label: string;
  filings: { headline: string; url: string }[];
};

export type Digest = {
  portfolio_id: string;
  window: string;
  generated_at: string;
  main: DigestItem[];
  routine: DigestItem[];
  counts: { main: number; routine: number; to_review: number };
  caught_up: boolean;
};

export type LedgerRow = {
  id: string;
  quote: string;
  page: number;
  sha256: string;
  call_period: string;
  call: string;
  metric_label: string;
  status: "Delivered" | "Missed" | "Partly" | "Vague" | "Not yet due" | "No comparable actual";
  target: string;
  period: string | null;
  reported: string | null;
  reason: string | null;
  source: { sha256: string; page: number; line: string } | null;
};

export type Promises = {
  symbol: string;
  name: string;
  calls: { period: string; pages: number }[];
  rows: LedgerRow[];
  counts: Record<string, number>;
  reported_through: string | null;
};

export type JobProgress = {
  period: string;
  label: string;
  pages: number;
  status: string;
  promises: number;
};
export type Job = {
  id: string;
  status: "queued" | "running" | "done" | "failed";
  result: {
    state?: string;
    progress?: JobProgress[];
    links?: { label: string; url: string }[];
    reason?: string;
    errors?: { call: string; error: string }[];
  } | null;
  error: string | null;
};

export type Override = {
  symbol: string;
  name: string;
  vol_mult: number | null;
  price_pct: number | null;
};
export type Settings = {
  portfolio_id: string;
  window_hours: number;
  vol_mult: number;
  price_pct: number;
  overrides: Override[];
  holdings: number;
  research: number;
  holdings_list: { symbol: string; name: string }[];
};
export type DryRun = { alerts: number; with_filing: number; sessions: number };

/** Browser-side call with JSON body. Returns null on any failure. */
export async function send<T>(path: string, method: string, body?: unknown): Promise<T | null> {
  try {
    const r = await fetch(`${API_URL}${path}`, {
      method,
      headers: body ? { "content-type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    return r.ok ? ((await r.json()) as T) : null;
  } catch {
    return null;
  }
}

async function get<T>(path: string): Promise<T | null> {
  try {
    const r = await fetch(`${API_URL}${path}`, { cache: "no-store" });
    return r.ok ? ((await r.json()) as T) : null;
  } catch {
    return null;
  }
}

export const getDigest = (window: string) => get<Digest>(`/digest?window=${window}`);
export const getPromises = (symbol: string) => get<Promises>(`/promises/${symbol}`);
export const getSettings = () => get<Settings>("/settings");
export const getHealth = () => get<Health>("/health");
export const getResults = (symbol: string) => get<ResultsView>(`/results/${symbol}/latest`);
export const getDocPage = (sha: string, n: number, q?: string) =>
  get<DocPage>(`/docs/${sha}/page/${n}${q ? `?q=${encodeURIComponent(q)}` : ""}`);

export function sourceHref(
  sha: string,
  page: number | null,
  line?: string | null,
  quote?: string | null,
): string {
  const qs = new URLSearchParams();
  if (line) qs.set("line", line);
  if (quote) qs.set("q", quote);
  const q = qs.toString();
  return `/source/${sha}/${page ?? 1}${q ? `?${q}` : ""}`;
}
