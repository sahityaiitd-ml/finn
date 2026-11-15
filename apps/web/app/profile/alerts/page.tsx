import { Suspense } from "react";
import { AlertRules } from "@/components/AlertRules";
import { getSettings } from "@/lib/api";

async function Content() {
  const s = await getSettings();
  if (!s) return <p className="p-6 text-ink-2">Could not reach the server.</p>;
  return <AlertRules initial={s} />;
}

export default function Page() {
  return (
    <main className="flex-1">
      <Suspense fallback={<p className="p-6 text-ink-2">Loading…</p>}>
        <Content />
      </Suspense>
    </main>
  );
}
