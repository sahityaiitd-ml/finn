"use client";

import Link from "next/link";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { API_URL, type DocPage } from "@/lib/api";
import { fiscalLabel } from "@/lib/format";
import { ArrowRight, Check } from "./ui";

export type SourceRef = {
  sha: string;
  page: number;
  line?: string | null;
  quote?: string | null;
  /** What FINN read from this page, shown in the callout ("Other income ₹114 Cr"). */
  read?: string | null;
};

const Ctx = createContext<{ open: (r: SourceRef) => void } | null>(null);
export const useSourceSheet = () => useContext(Ctx);

const norm = (s: string) => s.replace(/\s+/g, " ").trim().toLowerCase();
const KIND: Record<string, string> = { results: "Results filing", transcript: "Call transcript" };

export function SourceSheetProvider({ children }: { children: React.ReactNode }) {
  const [ref, setRef] = useState<SourceRef | null>(null);
  const open = useCallback((r: SourceRef) => setRef(r), []);
  return (
    <Ctx.Provider value={{ open }}>
      {children}
      {ref && <Sheet initial={ref} onClose={() => setRef(null)} />}
    </Ctx.Provider>
  );
}

function Sheet({ initial, onClose }: { initial: SourceRef; onClose: () => void }) {
  const [page, setPage] = useState(initial.page);
  const [loaded, setLoaded] = useState<{ key: string; doc: DocPage | null } | null>(null);
  const [copied, setCopied] = useState(false);
  const closeRef = useRef<HTMLButtonElement>(null);
  const hitRef = useRef<HTMLElement>(null);
  const original = page === initial.page; // only the cited page carries a highlight

  const key = `${page}|${original ? (initial.quote ?? "") : ""}`;
  const loading = loaded?.key !== key;
  const doc = loaded?.key === key ? loaded.doc : null;

  useEffect(() => {
    let stop = false;
    const q = original && initial.quote ? `?q=${encodeURIComponent(initial.quote)}` : "";
    fetch(`${API_URL}/docs/${initial.sha}/page/${page}${q}`)
      .then((r) => (r.ok ? (r.json() as Promise<DocPage>) : null))
      .catch(() => null)
      .then((d) => {
        if (!stop) setLoaded({ key, doc: d });
      });
    return () => {
      stop = true;
    };
  }, [initial.sha, initial.quote, page, original, key]);

  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      prev?.focus?.();
    };
  }, [onClose]);

  useEffect(() => {
    hitRef.current?.scrollIntoView({ block: "center" });
  }, [doc]);

  // locate the cited text on the page
  const lines = doc ? doc.text.split("\n") : [];
  const target = original && initial.line ? norm(initial.line) : "";
  const lineHit = target ? lines.findIndex((l) => norm(l) === target) : -1;
  const span = original && initial.quote ? doc?.highlight : null;
  const asked = original && Boolean(initial.line || initial.quote);
  const located = lineHit >= 0 || Boolean(span);
  const ocr = doc?.method && doc.method !== "pdfplumber";

  const title = doc
    ? `${doc.symbol} · ${KIND[doc.kind] ?? doc.kind} · ${fiscalLabel(doc.period)}`
    : "Source";
  const citation = doc ? `${title} · p.${doc.page} of ${doc.n_pages}` : "";

  async function copy() {
    try {
      await navigator.clipboard.writeText(citation);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard not available: nothing to do */
    }
  }

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-[rgba(34,38,42,0.32)]" onClick={onClose} aria-hidden />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Source"
        className="absolute inset-x-0 bottom-0 mx-auto flex h-[75dvh] max-w-[640px] flex-col gap-[14px] rounded-t-[24px] bg-surface px-5 pb-6 pt-[10px]"
      >
        <span className="mx-auto h-1 w-10 shrink-0 rounded-sm bg-border" aria-hidden />
        <div className="flex shrink-0 items-center gap-[10px]">
          <div className="min-w-px flex-1">
            <h2 className="text-[20px] text-ink">Source</h2>
            <p className="truncate text-[12px] text-muted">{title}</p>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close source"
            className="grid size-11 shrink-0 place-items-center rounded-full bg-sunk text-ink"
          >
            ✕
          </button>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <span className="rounded-full bg-sand/30 px-[10px] py-[3px] text-[12px] font-medium text-ink-2">
            {doc ? `Page ${doc.page} of ${doc.n_pages}` : "Loading…"}
          </span>
          {ocr && (
            <span className="rounded-full bg-amber-bg px-[10px] py-[3px] text-[12px] font-medium text-amber">
              OCR · verify
            </span>
          )}
          <span className="flex-1" />
          {doc?.pdf_url && (
            <a
              href={doc.pdf_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex min-h-[44px] items-center gap-2 text-[14px] font-medium text-sage-text"
            >
              Open PDF <ArrowRight />
            </a>
          )}
        </div>

        {doc && asked && !located && (
          <p className="shrink-0 rounded-xl bg-amber-bg px-[14px] py-3 text-[13px] text-amber">
            Line not located on p.{doc.page}. The full page is shown; check the figure yourself.
          </p>
        )}

        <div className="min-h-0 flex-1 overflow-y-auto rounded-xl bg-sunk px-[10px] py-3 text-[13px] leading-6 text-ink">
          {loading && (
            <div className="flex flex-col gap-2" aria-label="Loading page">
              {[272, 192, 240].map((w) => (
                <span
                  key={w}
                  className="h-2 rounded bg-track"
                  style={{ width: w, maxWidth: "100%" }}
                />
              ))}
            </div>
          )}
          {!loading && !doc && <p className="text-ink-2">This page could not be loaded.</p>}
          {!loading && doc && span && (
            <p className="whitespace-pre-wrap px-2">
              {doc.text.slice(0, span.start)}
              <mark
                ref={hitRef}
                className="rounded border-[1.5px] border-sage bg-sage-tint px-1 font-medium text-ink"
              >
                {doc.text.slice(span.start, span.end)}
              </mark>
              {doc.text.slice(span.end)}
            </p>
          )}
          {!loading &&
            doc &&
            !span &&
            lines.map((l, i) => (
              <p
                key={i}
                ref={i === lineHit ? (hitRef as React.RefObject<HTMLParagraphElement>) : undefined}
                className={
                  i === lineHit
                    ? "rounded-lg border-[1.5px] border-sage bg-sage-tint px-2 py-1 font-medium"
                    : "px-2"
                }
              >
                {l || " "}
              </p>
            ))}
        </div>

        {doc && initial.read && original && (
          <div
            className={`flex shrink-0 items-center gap-[10px] rounded-xl px-[14px] py-3 ${located ? "bg-sage-tint text-sage-text" : "bg-sunk text-ink-2"}`}
          >
            <span aria-hidden className="shrink-0">
              {located ? <Check size={20} /> : "ⓘ"}
            </span>
            <div className="min-w-px">
              <p className="text-[14px] font-medium">FINN read: {initial.read}</p>
              <p className="text-[12px]">
                {located
                  ? span
                    ? `Quote found on the page (${Math.round(span.score)}% match)`
                    : "Matches the page exactly"
                  : "Could not match to a line on this page"}
              </p>
            </div>
          </div>
        )}

        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            disabled={!doc || page <= 1}
            onClick={() => setPage(page - 1)}
            className="min-h-[44px] rounded-full border border-border bg-surface px-5 text-[14px] font-medium text-ink disabled:opacity-40"
          >
            ‹ p.{page - 1}
          </button>
          <span className="flex-1" />
          <button
            type="button"
            onClick={copy}
            disabled={!doc}
            className="min-h-[44px] rounded-full border border-border bg-surface px-5 text-[14px] font-medium text-ink disabled:opacity-40"
          >
            {copied ? "Copied" : "Copy citation"}
          </button>
          <span className="flex-1" />
          <button
            type="button"
            disabled={!doc || page >= doc.n_pages}
            onClick={() => setPage(page + 1)}
            className="min-h-[44px] rounded-full border border-border bg-surface px-5 text-[14px] font-medium text-ink disabled:opacity-40"
          >
            p.{page + 1} ›
          </button>
        </div>
        <Link href={`/source/${initial.sha}/${page}`} className="sr-only">
          Open this page as a full page
        </Link>
      </div>
    </div>
  );
}
