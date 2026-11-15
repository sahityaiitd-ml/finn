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

async function get<T>(path: string): Promise<T | null> {
  try {
    const r = await fetch(`${API_URL}${path}`, { cache: "no-store" });
    return r.ok ? ((await r.json()) as T) : null;
  } catch {
    return null;
  }
}

export const getDigest = (window: string) => get<Digest>(`/digest?window=${window}`);
export const getHealth = () => get<Health>("/health");
export const getResults = (symbol: string) => get<ResultsView>(`/results/${symbol}/latest`);
export const getDocPage = (sha: string, n: number) => get<DocPage>(`/docs/${sha}/page/${n}`);

export function sourceHref(sha: string, page: number | null, line?: string | null): string {
  const q = line ? `?line=${encodeURIComponent(line)}` : "";
  return `/source/${sha}/${page ?? 1}${q}`;
}
