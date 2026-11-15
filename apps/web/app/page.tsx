import { Suspense } from "react";
import { getHealth } from "@/lib/api";

async function ApiStatus() {
  const health = await getHealth();
  return (
    <>
      <p className="mt-1 text-lg font-medium" data-testid="api-status">
        {health ? "Connected" : "Not reachable"}
      </p>
      <p className="mt-1 text-sm text-ink-2">
        Database: {health?.db_configured ? "configured" : "not configured"}
      </p>
    </>
  );
}

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-[1024px] flex-1 px-4 py-10">
      <h1 className="text-2xl font-semibold">FINN</h1>
      <p className="mt-1 text-ink-2">Evidence, not verdicts.</p>
      <section className="mt-6 rounded-[16px] bg-surface p-5 shadow-card">
        <p className="text-sm text-muted">API status</p>
        <Suspense fallback={<p className="mt-1 text-lg font-medium">Checking…</p>}>
          <ApiStatus />
        </Suspense>
      </section>
    </main>
  );
}
