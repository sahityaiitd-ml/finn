"use client";

import Link from "next/link";
import { useState } from "react";
import { API_URL, type Digest, type DigestItem } from "@/lib/api";
import { categoryLabel, fmtTimeIST } from "@/lib/format";
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

function Card({ it, onReview }: { it: DigestItem; onReview: (id: string) => void }) {
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
        <ReviewButton onClick={() => onReview(it.id)} />
      </div>
    </article>
  );
}

export function TodayFeed({ digest }: { digest: Digest }) {
  const [items, setItems] = useState(digest.main);
  const [open, setOpen] = useState(false);

  const todo = items.filter((i) => !i.reviewed);
  const done = items.filter((i) => i.reviewed);
  const caughtUp = todo.length === 0;

  async function review(id: string) {
    setItems((xs) => xs.map((x) => (x.id === id ? { ...x, reviewed: true } : x)));
    try {
      const r = await fetch(`${API_URL}/filings/${id}/reviewed`, { method: "POST" });
      if (!r.ok) throw new Error();
    } catch {
      setItems((xs) => xs.map((x) => (x.id === id ? { ...x, reviewed: false } : x)));
    }
  }

  return (
    <div className="flex flex-col gap-3">
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

      {todo.map((it) => (
        <Card key={it.id} it={it} onReview={review} />
      ))}

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
                <p className="text-[12px] text-muted">{it.summary ?? it.headline}</p>
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
  );
}
