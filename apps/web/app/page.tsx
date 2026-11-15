import { Suspense } from "react";
import { TodayFeed } from "@/components/TodayFeed";
import { getDigest } from "@/lib/api";

const KEYS = ["24h", "3d", "7d"];

async function Content({ searchParams }: { searchParams: Promise<{ w?: string }> }) {
  const sp = await searchParams;
  const w = KEYS.includes(sp.w ?? "") ? sp.w! : "24h";
  const d = await getDigest(w);
  const now = d?.generated_at ?? new Date().toISOString();
  if (!d) {
    return (
      <p className="m-4 rounded-[16px] bg-surface p-4 text-[14px] text-ink-2 shadow-card">
        Could not reach the server. Try again in a moment.
      </p>
    );
  }
  return <TodayFeed key={w} digest={d} w={w} now={now} />;
}

export default function Home({ searchParams }: { searchParams: Promise<{ w?: string }> }) {
  return (
    <main className="flex-1">
      <Suspense fallback={<p className="p-6 text-ink-2">Loading…</p>}>
        <Content searchParams={searchParams} />
      </Suspense>
    </main>
  );
}
