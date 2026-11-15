export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Health = { status: string; service: string; db_configured: boolean };

export async function getHealth(): Promise<Health | null> {
  try {
    const r = await fetch(`${API_URL}/health`, { cache: "no-store" });
    return r.ok ? ((await r.json()) as Health) : null;
  } catch {
    return null;
  }
}
