import Link from "next/link";
import { Suspense } from "react";
import { ArrowLeft } from "@/components/ui";
import { getDocPage } from "@/lib/api";

const norm = (s: string) => s.replace(/\s+/g, " ").trim().toLowerCase();

async function Content({
  params,
  searchParams,
}: {
  params: Promise<{ sha: string; page: string }>;
  searchParams: Promise<{ line?: string }>;
}) {
  const { sha, page: pageParam } = await params;
  const { line } = await searchParams;
  const page = Number(pageParam) || 1;
  const d = await getDocPage(sha, page);
  if (!d) return <p className="p-6 text-ink-2">Page not found.</p>;
  const lines = d.text.split("\n");
  const target = line ? norm(line) : "";
  const hit = target ? lines.findIndex((l) => norm(l) === target) : -1;
  return (
    <div className="mx-auto w-full max-w-[1024px] px-4 pb-28 pt-6">
      <Link href="/companies" className="-m-3 mb-2 inline-flex p-3 text-ink-2" aria-label="Back">
        <ArrowLeft />
      </Link>
      <p className="text-[12px] text-muted">
        {d.symbol} · {d.kind} · {d.period} · page {d.page} of {d.n_pages}
      </p>
      {line && hit < 0 && (
        <p className="mt-3 rounded-lg bg-sunk px-3 py-2 text-[13px] text-ink-2">
          Line not located on this page.
        </p>
      )}
      <div className="mt-3 rounded-[16px] bg-surface p-4 text-[13px] leading-6 text-ink shadow-card">
        {lines.map((l, i) => (
          <p key={i} className={i === hit ? "rounded bg-mist px-1 font-medium" : "px-1"}>
            {l || " "}
          </p>
        ))}
      </div>
    </div>
  );
}

export default function Page(props: {
  params: Promise<{ sha: string; page: string }>;
  searchParams: Promise<{ line?: string }>;
}) {
  return (
    <Suspense fallback={<p className="p-6 text-ink-2">Loading…</p>}>
      <Content params={props.params} searchParams={props.searchParams} />
    </Suspense>
  );
}
