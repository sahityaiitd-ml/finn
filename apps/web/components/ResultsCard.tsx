import type { ResultRow, ResultsView } from "@/lib/api";
import { sourceHref } from "@/lib/api";
import { fiscalLabel, fmtBp, fmtNum, fmtPct } from "@/lib/format";
import { Card, Pill, SourceLink, Warn } from "./ui";

function Cell({ children, w }: { children: React.ReactNode; w: string }) {
  return <p className={`shrink-0 text-right ${w}`}>{children}</p>;
}

function Row({ r }: { r: ResultRow }) {
  const isMargin = r.key === "margin";
  const value = r.value === null ? "See PDF" : isMargin ? fmtPct(r.value, false) : fmtNum(r.value);
  const qoq = isMargin ? fmtBp(r.qoq_bp) : fmtPct(r.qoq_pct);
  const yoy = isMargin ? fmtBp(r.yoy_bp) : fmtPct(r.yoy_pct);
  return (
    <div className="flex items-start border-b border-hairline p-3 text-[14px] text-ink">
      <p className="min-w-px flex-1">{r.label}</p>
      <Cell w="w-[72px]">{value}</Cell>
      <Cell w="w-[66px]">{r.qoq_available ? qoq : "See PDF"}</Cell>
      <Cell w="w-[74px]">{r.yoy_available ? yoy : "See PDF"}</Cell>
    </div>
  );
}

export function ResultsCard({ v }: { v: ResultsView }) {
  const label = `${fiscalLabel(v.period)} results`;
  const revLine = v.rows.find((r) => r.key === "revenue")?.line ?? null;
  const href = sourceHref(v.source.sha256, v.source.page, revLine);
  const basis = v.basis ? v.basis[0].toUpperCase() + v.basis.slice(1) : null;

  return (
    <>
      <Card>
        <div className="flex items-center gap-2">
          <div className="min-w-px flex-1">
            <h2 className="text-[17px] font-medium text-ink">{label}</h2>
            <p className="text-[12px] text-muted">Source: results filing</p>
          </div>
          {basis && <Pill label={basis} />}
        </div>

        {v.status === "ok" ? (
          <div>
            <div className="flex rounded-lg bg-sunk px-3 py-[10px] text-[11px] font-medium tracking-[0.04em] text-ink-2">
              <p className="min-w-px flex-1">₹ CR</p>
              <Cell w="w-[72px]">{fiscalLabel(v.period)}</Cell>
              <Cell w="w-[66px]">QOQ</Cell>
              <Cell w="w-[74px]">YOY</Cell>
            </div>
            {v.rows.map((r) => (
              <Row key={r.key} r={r} />
            ))}
          </div>
        ) : (
          <div className="rounded-lg bg-sunk p-4">
            <p className="text-[15px] font-medium text-ink">{v.message}</p>
            <p className="mt-1 text-[13px] text-ink-2">
              {v.status === "unsupported"
                ? "Banks and NBFCs use a different results format."
                : "The figures could not be verified, so none are shown."}
            </p>
          </div>
        )}

        <div className="flex flex-col">
          <SourceLink href={href} label={`Source · results filing p.${v.source.page ?? 1}`} />
          {v.status === "ok" && (
            <p className="text-[12px] text-muted">
              {v.exceptional
                ? `Exceptional items: ${v.exceptional.value > 0 ? "gain" : "charge"} of ₹${fmtNum(Math.abs(v.exceptional.value))} Cr`
                : "Exceptional items: none"}
            </p>
          )}
        </div>
      </Card>

      {(v.notes ?? []).map((n) => (
        <div
          key={n.flag}
          className="flex items-center gap-2 rounded-[12px] bg-amber-bg px-4 py-3 text-amber"
        >
          <Warn />
          <p className="min-w-px flex-1 text-[14px]">{n.text}</p>
          {n.page && (
            <SourceLink href={sourceHref(v.source.sha256, n.page)} label={`p.${n.page}`} />
          )}
        </div>
      ))}
    </>
  );
}
