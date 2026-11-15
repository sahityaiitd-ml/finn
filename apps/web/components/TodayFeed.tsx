"use client";

import Link from "next/link";
import { useState } from "react";
import { type Digest, type DigestItem, send } from "@/lib/api";
import { categoryLabel, fmtDayIST, fmtNum, fmtPct, fmtTimeIST } from "@/lib/format";
import { Check, Chevron, ExternalSourceLink, Pill } from "./ui";

function ReviewButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="min-h-[44px] rounded-full border border-border bg-surface px-5 text-[14px] font-medium text-ink"
    >
      Mark reviewed
    </button>
  );
}

function AlertCard({ it, onReview }: { it: DigestItem; onReview: (it: DigestItem) => void }) {
  const a = it.alert!;
  return (
    <article className="flex flex-col gap-[10px] rounded-[16px] bg-surface p-4 shadow-card">
      <div className="flex items-center gap-2">
        <Pill label="End-of-day alert" />
        <span className="flex-1" />
        <span className="text-[12px] text-muted">{fmtDayIST(it.published_at)}</span>
      </div>
      <h3 className="text-[18px] font-medium text-ink">{it.name}</h3>
      <div className="flex">
        <div className="flex min-w-px flex-1 flex-col gap-px pr-2">
          <span className="text-[12px] text-muted">Volume</span>
          <span className="text-[17px] font-medium text-ink">{fmtNum(a.ratio)}×</span>
          <span className="text-[12px] text-muted">
            {a.vol_mult > 0 ? `rule ${a.vol_mult}×` : "rule off"}
          </span>
        </div>
        <span className="w-px self-stretch bg-hairline" />
        <div className="flex min-w-px flex-1 flex-col gap-px pl-3 pr-2">
          <span className="text-[12px] text-muted">Price</span>
          {/* a price move is never coloured: plain ink, sign only */}
          <span className="text-[17px] font-medium text-ink">{fmtPct(a.pct)}</span>
          <span className="text-[12px] text-muted">on the day</span>
        </div>
      </div>
      <p className="flex items-center gap-2 text-[13px] font-medium text-ink">
        <span
          aria-hidden
          className="grid size-4 place-items-center rounded-full border border-ink-2 text-[10px] text-ink-2"
        >
          i
        </span>
        {a.cause_label}
      </p>
      {a.filings.slice(0, 2).map((f) => (
        <ExternalSourceLink key={f.url} href={f.url} label="Source · BSE filing" />
      ))}
      <div className="flex items-center gap-2 pt-[2px]">
        <Link
          href={`/companies/${it.symbol}/filings`}
          className="inline-flex min-h-[44px] items-center text-[14px] font-medium text-sage-text"
        >
          Dig in →
        </Link>
        <span className="flex-1" />
        <ReviewButton onClick={() => onReview(it)} />
      </div>
    </article>
  );
}

function Card({ it, onReview }: { it: DigestItem; onReview: (it: DigestItem) => void }) {
  const material = it.never_collapse && it.category !== "results";
  const digHref =
    it.category === "results"
      ? `/companies/${it.symbol}/results`
      : `/companies/${it.symbol}/filings`;
  const digLabel = it.category === "results" ? "See results first cut" : "Dig in";
  return (
    <article className="flex flex-col gap-[10px] rounded-[16px] bg-surface p-4 shadow-card">
      <div className="flex items-center gap-2">
        {material && <Pill label="Material" tone="terra" />}
        <Pill label={categoryLabel(it.category)} />
        <span className="flex-1" />
        <span className="text-[12px] text-muted">{fmtTimeIST(it.published_at)}</span>
      </div>
      <div>
        <h3 className="text-[18px] font-medium text-ink">{it.name}</h3>
        <p className="text-[13px] text-ink-2">{it.summary ?? it.headline}</p>
      </div>
      {it.source_url && <ExternalSourceLink href={it.source_url} label="Source · BSE filing" />}
      <div className="flex items-center gap-2 pt-[2px]">
        <Link
          href={digHref}
          className="inline-flex min-h-[44px] items-center text-[14px] font-medium text-sage-text"
        >
          {digLabel} →
        </Link>
        <span className="flex-1" />
        <ReviewButton onClick={() => onReview(it)} />
      </div>
    </article>
  );
}

const WINDOWS = [
  { key: "24h", label: "Last 24 h" },
  { key: "3d", label: "3 days" },
  { key: "7d", label: "7 days" },
];

export function TodayFeed({ digest, w, now }: { digest: Digest; w: string; now: string }) {
  const [items, setItems] = useState(digest.main);
  const [open, setOpen] = useState(false);

  const todo = items.filter((i) => !i.reviewed);
  const done = items.filter((i) => i.reviewed);
  const caughtUp = todo.length === 0;

  async function review(it: DigestItem) {
    const id = it.id;
    setItems((xs) => xs.map((x) => (x.id === id ? { ...x, reviewed: true } : x)));
    const path = it.alert ? `/alerts/${id}/reviewed` : `/filings/${id}/reviewed`;
    if (!(await send(path, "POST"))) {
      setItems((xs) => xs.map((x) => (x.id === id ? { ...x, reviewed: false } : x)));
    }
  }

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
            <p className="text-[14px] text-ink-2">
              {todo.length} need you · {digest.routine.length} routine archived
            </p>
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
      <div className="mx-auto flex w-full max-w-[1024px] flex-col gap-3 px-4 pb-28 pt-4">
        {items.length > 0 && (
          <div className="flex flex-col gap-[6px] px-1" aria-label="Review progress">
            <p className="text-[12px] font-medium text-ink-2">
              {done.length} of {items.length} reviewed
            </p>
            <div className="h-[6px] w-full rounded-full bg-track">
              <div
                className="h-[6px] rounded-full bg-sage"
                style={{ width: `${(done.length / items.length) * 100}%` }}
              />
            </div>
          </div>
        )}

        {caughtUp && (
          <div className="flex items-center gap-3 rounded-[16px] bg-mist px-4 py-3 text-sage-text">
            <span className="grid size-6 place-items-center rounded-md bg-sage text-surface">
              <Check size={16} />
            </span>
            <div>
              <p className="text-[16px] font-semibold">All caught up</p>
              <p className="text-[12px]">
                {items.length === 0
                  ? "No new filings in this window"
                  : `${done.length} of ${items.length} reviewed`}
              </p>
            </div>
          </div>
        )}

        {todo.map((it) =>
          it.alert ? (
            <AlertCard key={it.id} it={it} onReview={review} />
          ) : (
            <Card key={it.id} it={it} onReview={review} />
          ),
        )}

        {done.length > 0 && (
          <section className="rounded-[16px] bg-surface p-4 shadow-card">
            <h2 className="mb-2 text-[16px] font-medium text-ink">Reviewed</h2>
            {done.map((it) => (
              <div key={it.id} className="flex min-h-[44px] items-center gap-3 py-1">
                <span className="text-sage-text">
                  <Check />
                </span>
                <div className="min-w-px flex-1">
                  <p className="text-[15px] text-ink">{it.name}</p>
                  <p className="text-[12px] text-muted">
                    {it.alert ? "End-of-day alert" : (it.summary ?? it.headline)}
                  </p>
                </div>
                <span className="text-[12px] text-muted">{fmtTimeIST(it.published_at)}</span>
              </div>
            ))}
          </section>
        )}

        {digest.routine.length > 0 && (
          <section className="rounded-[16px] bg-surface p-4 shadow-card">
            <button
              type="button"
              aria-expanded={open}
              onClick={() => setOpen((o) => !o)}
              className="flex min-h-[32px] w-full items-center gap-2 text-left text-[15px] text-ink"
            >
              <span className="flex-1">{digest.routine.length} routine filings archived</span>
              <Chevron open={open} />
            </button>
            {!open && (
              <p className="text-[12px] text-muted">
                {Array.from(new Set(digest.routine.map((r) => categoryLabel(r.category))))
                  .slice(0, 4)
                  .join(" · ")}
              </p>
            )}
            {open && (
              <ul className="mt-2 flex flex-col">
                {digest.routine.map((r) => (
                  <li key={r.id} className="flex items-start gap-3 border-t border-hairline py-2">
                    <div className="min-w-px flex-1">
                      <p className="text-[14px] text-ink">
                        {r.name} · {r.headline}
                      </p>
                      {r.source_url && (
                        <ExternalSourceLink href={r.source_url} label="Source · BSE filing" />
                      )}
                    </div>
                    <span className="text-[12px] text-muted">{fmtTimeIST(r.published_at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}
      </div>
    </>
  );
}
