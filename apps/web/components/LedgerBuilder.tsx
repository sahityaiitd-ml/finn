"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { API_URL, type Job, type JobProgress } from "@/lib/api";
import { Card, Check, Pill } from "./ui";

const POLL_MS = 2500;
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

function StatusIcon({ s }: { s: string }) {
  if (s === "done")
    return (
      <span className="text-sage-text">
        <Check />
      </span>
    );
  if (s === "error") return <span className="text-terra">✕</span>;
  if (s === "reading")
    return (
      <span className="inline-block size-[18px] animate-spin rounded-full border-2 border-sage border-t-transparent" />
    );
  return <span className="inline-block size-[18px] rounded-full border border-border" />;
}

const TAG: Record<string, { label: string; tone: "sage" | "terra" | "neutral" }> = {
  done: { label: "Done", tone: "sage" },
  reading: { label: "Reading", tone: "neutral" },
  queued: { label: "Queued", tone: "neutral" },
  error: { label: "Retry later", tone: "terra" },
};

export function LedgerBuilder({
  symbol,
  calls,
}: {
  symbol: string;
  calls: { period: string; pages: number }[];
}) {
  const router = useRouter();
  const [job, setJob] = useState<Job | null>(null);
  const [failed, setFailed] = useState<string | null>(null);

  useEffect(() => {
    let stop = false;
    async function loop() {
      try {
        const r = await fetch(`${API_URL}/promises/${symbol}`, { method: "POST" });
        if (!r.ok) throw new Error("start failed");
        const { job_id } = (await r.json()) as { job_id: string };
        while (!stop) {
          const j = (await (await fetch(`${API_URL}/jobs/${job_id}`)).json()) as Job;
          setJob(j);
          if (j.status === "done" || j.status === "failed") {
            if (j.status === "done" && j.result?.state === "done") router.refresh();
            else if (j.status === "failed") setFailed(j.error ?? "The ledger could not be built.");
            return;
          }
          await new Promise((res) => setTimeout(res, POLL_MS));
        }
      } catch {
        if (!stop) setFailed("Could not reach the server.");
      }
    }
    loop();
    return () => {
      stop = true;
    };
  }, [symbol, router]);

  const state = job?.result?.state;
  const progress: JobProgress[] =
    job?.result?.progress ??
    calls.map((c) => ({
      period: c.period,
      label: c.period,
      pages: c.pages,
      status: "queued",
      promises: 0,
    }));
  const doneCount = progress.filter((p) => p.status === "done").length;

  if (state === "unavailable") {
    return (
      <Card>
        <p className="text-[16px] font-medium text-ink">Transcripts not available</p>
        <p className="text-[13px] text-ink-2">
          {cap(job?.result?.reason ?? "The source blocks automated downloads")}. Nothing is guessed.
          You can open them yourself:
        </p>
        {(job?.result?.links ?? []).map((l) => (
          <a
            key={l.url}
            href={l.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex min-h-[44px] items-center text-[13px] font-medium text-sage-text"
          >
            Transcript · {l.label} ↗
          </a>
        ))}
      </Card>
    );
  }
  if (failed || state === "partial") {
    return (
      <Card>
        <p className="text-[16px] font-medium text-ink">Some calls could not be read</p>
        <p className="text-[13px] text-ink-2">
          {failed ?? "The model service is rate-limited right now."} Nothing is shown as “no
          guidance” when a call could not be read. Try again in a minute.
        </p>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <div className="flex items-center gap-2">
          <h2 className="text-[17px] font-medium text-ink">Building the ledger</h2>
          <span className="flex-1" />
          <span className="text-[13px] text-muted">
            {doneCount} of {progress.length}
          </span>
        </div>
        <div className="h-[6px] w-full rounded-full bg-track">
          <div
            className="h-[6px] rounded-full bg-sage transition-all"
            style={{ width: `${progress.length ? (doneCount / progress.length) * 100 : 0}%` }}
          />
        </div>
        <p className="text-[12px] text-muted">
          Reading each call and checking every quote against its page.
        </p>
      </Card>
      <section className="rounded-[16px] bg-surface p-4 shadow-card">
        {progress.map((p) => {
          const t = TAG[p.status] ?? TAG.queued;
          return (
            <div
              key={p.period}
              className="flex items-center gap-3 border-b border-hairline py-3 last:border-b-0"
            >
              <StatusIcon s={p.status} />
              <div className="min-w-px flex-1">
                <p className="text-[15px] text-ink">{p.label}</p>
                <p className="text-[12px] text-muted">
                  {p.pages} pages{p.status === "done" ? ` · ${p.promises} promises` : ""}
                </p>
              </div>
              <Pill label={t.label} tone={t.tone} />
            </div>
          );
        })}
      </section>
    </>
  );
}
