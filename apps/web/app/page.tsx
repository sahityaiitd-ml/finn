import Link from "next/link";
import { Suspense } from "react";
import { TodayFeed } from "@/components/TodayFeed";
import { getDigest } from "@/lib/api";
import { fmtDayIST, fmtTimeIST } from "@/lib/format";

const WINDOWS = [
  { key: "24h", label: "Last 24 h" },
  { key: "3d", label: "3 days" },
  { key: "7d", label: "7 days" },
];

async function Content({ searchParams }: { searchParams: Promise<{ w?: string }> }) {
  const sp = await searchParams;
  const w = WINDOWS.some((x) => x.key === sp.w) ? sp.w! : "24h";
  const d = await getDigest(w);
  const now = d?.generated_at ?? new Date().toISOString();
  return (
    <>
      <header className="bg-surface px-5 pb-4 pt-6">
        <div className="mx-auto flex max-w-[1024px] flex-col gap-3">
          <div className="flex items-center text-[13px] text-muted">
            <span>{fmtDayIST(now)}</span>
            <span className="flex-1" />
            <span>Data as of {fmtTimeIST(now)} IST</span>
          </div>
          <div>
            <h1 className="text-[28px] text-ink">Today</h1>
            {d && (
              <p className="text-[14px] text-ink-2">
                {d.counts.to_review} need you · {d.counts.routine} routine archived
              </p>
            )}
          </div>
          <nav aria-label="Time window" className="flex rounded-full bg-track p-1">
            {WINDOWS.map((x) => (
              <Link
                key={x.key}
                href={`/?w=${x.key}`}
                aria-current={x.key === w ? "page" : undefined}
                className={`flex min-h-[36px] flex-1 items-center justify-center rounded-full px-3 text-[13px] ${
                  x.key === w ? "bg-surface font-medium text-sage-text shadow-sm" : "text-ink-2"
                }`}
              >
                {x.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <div className="mx-auto w-full max-w-[1024px] px-4 pb-28 pt-4">
        {d ? (
          <TodayFeed key={w} digest={d} />
        ) : (
          <p className="rounded-[16px] bg-surface p-4 text-[14px] text-ink-2 shadow-card">
            Could not reach the server. Pull to retry in a moment.
          </p>
        )}
      </div>
    </>
  );
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
