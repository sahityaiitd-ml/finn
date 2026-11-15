"use client";

import { useState } from "react";
import { type LedgerRow, type Promises, sourceHref } from "@/lib/api";
import { fiscalLabel } from "@/lib/format";
import { Card, Pill, SourceLink } from "./ui";

type Status = LedgerRow["status"];
const TONE: Record<Status, "sage" | "terra" | "amber" | "neutral"> = {
  Delivered: "sage",
  Missed: "terra",
  Partly: "amber",
  Vague: "neutral",
  "Not yet due": "neutral",
  "No comparable actual": "neutral",
};
const BAR: Record<Status, string> = {
  Delivered: "bg-sage",
  Missed: "bg-terra",
  Partly: "bg-amber",
  Vague: "bg-sand",
  "Not yet due": "bg-mist",
  "No comparable actual": "bg-border",
};
const ORDER: Status[] = [
  "Delivered",
  "Missed",
  "Partly",
  "Vague",
  "Not yet due",
  "No comparable actual",
];
const SHORT: Record<Status, string> = {
  Delivered: "Delivered",
  Missed: "Missed",
  Partly: "Partly",
  Vague: "Vague",
  "Not yet due": "Due later",
  "No comparable actual": "No match",
};
const LEGEND: Record<Status, string> = {
  Delivered: "delivered",
  Missed: "missed",
  Partly: "partly",
  Vague: "vague",
  "Not yet due": "not yet due",
  "No comparable actual": "no comparable figure",
};

function Quote({ text }: { text: string }) {
  return (
    <div className="flex overflow-hidden rounded-lg bg-mist">
      <span className="w-[3px] self-stretch bg-sage" />
      <p className="px-3 py-[10px] text-[14px] text-ink">“{text}”</p>
    </div>
  );
}

function Reported({ r }: { r: LedgerRow }) {
  if (r.status === "Vague")
    return (
      <p className="text-[15px] font-medium text-ink-2">Not scored: no number or date given</p>
    );
  if (r.status === "Not yet due")
    return <p className="text-[15px] font-medium text-ink-2">Due {r.period ?? "later"}</p>;
  if (r.status === "No comparable actual")
    return (
      <p className="text-[15px] font-medium text-ink-2">
        No comparable figure in the results{r.reason ? `: ${r.reason}` : ""}
      </p>
    );
  return (
    <>
      <p className="text-[15px] font-medium text-ink">
        {r.metric_label} {r.reported}
      </p>
      {r.source && (
        <SourceLink
          href={sourceHref(r.source.sha256, r.source.page, r.source.line)}
          label={`Source · results filing · p.${r.source.page}`}
        />
      )}
    </>
  );
}

function Row({ r }: { r: LedgerRow }) {
  return (
    <article className="flex flex-col gap-[6px] rounded-[16px] bg-surface p-4 shadow-card">
      <div className="flex items-center gap-2">
        <span className="text-[12px] font-medium text-muted">Said</span>
        <span className="flex-1" />
        <Pill
          label={r.status === "No comparable actual" ? "No comparable figure" : r.status}
          tone={TONE[r.status]}
        />
      </div>
      <Quote text={r.quote} />
      {r.target && (
        <p className="text-[13px] text-ink-2">
          {r.metric_label} · target {r.target}
          {r.period ? ` · ${r.period}` : ""}
        </p>
      )}
      <SourceLink
        href={sourceHref(r.sha256, r.page, null, r.quote)}
        label={`Source · ${r.call} · p.${r.page}`}
      />
      <p className="text-[12px] font-medium text-muted">Reported</p>
      <Reported r={r} />
    </article>
  );
}

export function PromisesView({ data }: { data: Promises }) {
  const [filter, setFilter] = useState<Status | "All">("All");
  const rows = data.rows;
  const shown = filter === "All" ? rows : rows.filter((r) => r.status === filter);
  const present = ORDER.filter((s) => (data.counts[s] ?? 0) > 0);

  return (
    <>
      <Card>
        <div className="flex items-center gap-2">
          <h2 className="text-[16px] font-medium text-ink">
            Last {data.calls.length || 4} quarters
          </h2>
          <span className="flex-1" />
          <span className="text-[13px] text-muted">{rows.length} tracked</span>
        </div>
        <div className="flex h-2 gap-[3px]" role="img" aria-label="Status breakdown">
          {present.map((s) => (
            <span
              key={s}
              className={`h-2 rounded-full ${BAR[s]}`}
              style={{ flexGrow: data.counts[s] }}
            />
          ))}
        </div>
        <div className="flex flex-wrap gap-x-[14px] gap-y-[6px]">
          {present.map((s) => (
            <span key={s} className="flex items-center gap-[6px] text-[12px] text-ink-2">
              <span className={`size-2 rounded-full ${BAR[s]}`} />
              {data.counts[s]} {LEGEND[s]}
            </span>
          ))}
        </div>
        {data.reported_through && (
          <p className="text-[12px] text-muted">
            Compared with results reported through {fiscalLabel(data.reported_through)}.
          </p>
        )}
      </Card>

      <div className="-mx-4 overflow-x-auto px-4">
        <div
          className="inline-flex rounded-full bg-track p-1"
          role="tablist"
          aria-label="Filter promises"
        >
          {(["All", ...present] as const).map((s) => {
            const n = s === "All" ? rows.length : data.counts[s];
            const active = filter === s;
            return (
              <button
                key={s}
                role="tab"
                aria-selected={active}
                onClick={() => setFilter(s)}
                className={`min-h-[36px] whitespace-nowrap rounded-full px-[14px] text-[13px] ${
                  active ? "bg-surface font-medium text-sage-text shadow-sm" : "text-ink-2"
                }`}
              >
                {s === "All" ? "All" : SHORT[s]} {n}
              </button>
            );
          })}
        </div>
      </div>

      {shown.map((r) => (
        <Row key={r.id} r={r} />
      ))}
    </>
  );
}
