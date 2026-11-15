"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { type DryRun, type Override, type Settings, send } from "@/lib/api";
import { ArrowLeft, Card, Chevron, Switch } from "./ui";

const VOL = [1.5, 2, 2.5, 3, 4, 5];
const PRICE = [2, 3, 4, 5, 7, 10];
const NEVER = [
  "Results",
  "Board outcomes",
  "M&A",
  "Auditor change",
  "KMP change",
  "Credit rating",
  "Pledge",
  "Litigation",
  "Fund-raise",
];
const LABELS = ["No related filing found", "Related filing found, cause unconfirmed"];

const opts = (list: number[], cur: number) =>
  list.includes(cur) || cur === 0 ? list : [...list, cur].sort((a, b) => a - b);

function Threshold({
  label,
  sub,
  value,
  options,
  fmt,
  onChange,
  fallback,
}: {
  label: string;
  sub: string;
  value: number;
  options: number[];
  fmt: (n: number) => string;
  onChange: (n: number) => void;
  fallback: number;
}) {
  const on = value > 0;
  const shown = on ? value : fallback;
  return (
    <div className="flex items-center gap-3 border-b border-hairline py-[14px] last:border-b-0">
      <div className="min-w-px flex-1">
        <p className="text-[15px] text-ink">{label}</p>
        <p className="text-[12px] text-muted">{sub}</p>
      </div>
      <select
        aria-label={`${label} threshold`}
        value={shown}
        disabled={!on}
        onChange={(e) => onChange(Number(e.target.value))}
        className="min-h-[40px] rounded-[10px] border border-border bg-surface px-3 text-[14px] font-medium text-ink disabled:opacity-50"
      >
        {opts(options, shown).map((o) => (
          <option key={o} value={o}>
            {fmt(o)}
          </option>
        ))}
      </select>
      <Switch on={on} label={`${label} on`} onChange={(v) => onChange(v ? fallback : 0)} />
    </div>
  );
}

const describe = (o: Override, d: { vol: number; price: number }) => {
  const v = o.vol_mult ?? d.vol;
  const p = o.price_pct ?? d.price;
  const vol = v > 0 ? `Volume ${v}×` : "volume off";
  const price = p > 0 ? `price ±${p}%` : "price off";
  const s = `${vol} · ${price}`;
  return v > 0 ? s : `${price[0].toUpperCase()}${price.slice(1)} · ${vol}`;
};

export function AlertRules({ initial }: { initial: Settings }) {
  const [s, setS] = useState(initial);
  const [dry, setDry] = useState<DryRun | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [adding, setAdding] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      setDry(
        await send<DryRun>(
          `/settings/dry-run?vol_mult=${s.vol_mult}&price_pct=${s.price_pct}`,
          "GET",
        ),
      );
    }, 350);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [s.vol_mult, s.price_pct, s.overrides]);

  async function setDefault(patch: Partial<Pick<Settings, "vol_mult" | "price_pct">>) {
    setS((x) => ({ ...x, ...patch }));
    const next = await send<Settings>("/settings", "PUT", patch);
    if (next) setS(next);
  }
  async function saveOverride(sym: string, vol: number | null, price: number | null) {
    const next = await send<Settings>(`/settings/overrides/${sym}`, "PUT", {
      vol_mult: vol,
      price_pct: price,
    });
    if (next) setS(next);
  }
  async function removeOverride(sym: string) {
    const next = await send<Settings>(`/settings/overrides/${sym}`, "DELETE");
    if (next) {
      setS(next);
      setOpen(null);
    }
  }

  const taken = new Set(s.overrides.map((o) => o.symbol));
  const addable = s.holdings_list.filter((h) => !taken.has(h.symbol));
  const d = { vol: s.vol_mult, price: s.price_pct };

  return (
    <>
      <header className="bg-surface px-5 pb-4 pt-6">
        <div className="mx-auto flex max-w-[640px] flex-col gap-[14px]">
          <div className="flex items-center gap-[10px]">
            <Link href="/profile" aria-label="Back to Profile" className="-m-3 p-3 text-ink-2">
              <ArrowLeft />
            </Link>
            <span className="text-[14px] text-ink-2">Profile</span>
          </div>
          <h1 className="text-[28px] text-ink">Alert rules</h1>
          <p className="text-[13px] text-ink-2">Checked once a day, after the market close.</p>
        </div>
      </header>

      <div className="mx-auto flex w-full max-w-[640px] flex-col gap-3 px-4 pb-28 pt-4">
        <Card>
          <div className="flex items-center gap-2 border-b border-hairline pb-2">
            <h2 className="text-[16px] font-medium text-ink">Portfolio default</h2>
            <span className="flex-1" />
            <span className="text-[13px] text-muted">{s.holdings} stocks</span>
          </div>
          <div>
            <Threshold
              label="Volume spike"
              sub="Above × the 20-day average"
              value={s.vol_mult}
              options={VOL}
              fmt={(n) => `${n.toFixed(1)}×`}
              onChange={(n) => setDefault({ vol_mult: n })}
              fallback={2}
            />
            <Threshold
              label="Price move"
              sub="Beyond ± % in one day"
              value={s.price_pct}
              options={PRICE}
              fmt={(n) => `${n.toFixed(1)}%`}
              onChange={(n) => setDefault({ price_pct: n })}
              fallback={5}
            />
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-2 border-b border-hairline pb-2">
            <h2 className="text-[16px] font-medium text-ink">Overrides</h2>
            <span className="flex-1" />
            <span className="text-[13px] text-muted">{s.overrides.length}</span>
          </div>
          {s.overrides.map((o) => (
            <div key={o.symbol} className="border-b border-hairline last:border-b-0">
              <button
                type="button"
                aria-expanded={open === o.symbol}
                onClick={() => setOpen(open === o.symbol ? null : o.symbol)}
                className="flex min-h-[56px] w-full items-center gap-3 text-left"
              >
                <span className="min-w-px flex-1">
                  <span className="block text-[15px] text-ink">{o.name}</span>
                  <span className="block text-[12px] text-muted">{describe(o, d)}</span>
                </span>
                <Chevron open={open === o.symbol} />
              </button>
              {open === o.symbol && (
                <div className="pb-2">
                  <Threshold
                    label="Volume spike"
                    sub="Above × the 20-day average"
                    value={o.vol_mult ?? s.vol_mult}
                    options={VOL}
                    fmt={(n) => `${n.toFixed(1)}×`}
                    onChange={(n) => saveOverride(o.symbol, n, o.price_pct ?? s.price_pct)}
                    fallback={s.vol_mult || 2}
                  />
                  <Threshold
                    label="Price move"
                    sub="Beyond ± % in one day"
                    value={o.price_pct ?? s.price_pct}
                    options={PRICE}
                    fmt={(n) => `${n.toFixed(1)}%`}
                    onChange={(n) => saveOverride(o.symbol, o.vol_mult ?? s.vol_mult, n)}
                    fallback={s.price_pct || 5}
                  />
                  <button
                    type="button"
                    onClick={() => removeOverride(o.symbol)}
                    className="min-h-[44px] text-[14px] font-medium text-sage-text"
                  >
                    Remove override
                  </button>
                </div>
              )}
            </div>
          ))}
          <div className="flex items-center gap-2 pt-3">
            <select
              aria-label="Stock to override"
              value={adding}
              onChange={(e) => setAdding(e.target.value)}
              className="min-h-[44px] min-w-px flex-1 rounded-full border border-border bg-surface px-4 text-[14px] text-ink"
            >
              <option value="">Choose a stock…</option>
              {addable.map((h) => (
                <option key={h.symbol} value={h.symbol}>
                  {h.name}
                </option>
              ))}
            </select>
            <button
              type="button"
              disabled={!adding}
              onClick={async () => {
                await saveOverride(adding, s.vol_mult, s.price_pct);
                setOpen(adding);
                setAdding("");
              }}
              className="min-h-[44px] rounded-full border border-border bg-surface px-5 text-[14px] font-medium text-ink disabled:opacity-50"
            >
              Add override
            </button>
          </div>
        </Card>

        <div className="flex items-start gap-3 rounded-[16px] bg-sage-tint px-4 py-[14px] text-sage-text">
          <span
            aria-hidden
            className="mt-[2px] grid size-5 place-items-center rounded-full border border-sage-text text-[12px]"
          >
            i
          </span>
          <div>
            <p className="text-[14px] font-semibold">Dry run</p>
            <p className="text-[13px]">
              {dry
                ? `Last ${dry.sessions} sessions at these settings: ${dry.alerts} alerts would have fired, ${dry.with_filing} with a related filing.`
                : "Checking the last month of prices…"}
            </p>
          </div>
        </div>

        <Card>
          <h2 className="text-[16px] font-medium text-ink">How FINN labels a cause</h2>
          <p className="text-[13px] text-ink-2">
            FINN never guesses why a stock moved. Each alert carries one of two labels:
          </p>
          {LABELS.map((l) => (
            <p key={l} className="flex items-center gap-[10px] text-[14px] text-ink">
              <span className="text-sage-text">✓</span>
              {l}
            </p>
          ))}
          <p className="text-[12px] text-muted">
            A filing counts as related only if it is material, for this stock, and filed between the
            previous close and this one.
          </p>
        </Card>

        <Card>
          <h2 className="text-[16px] font-medium text-ink">Never collapsed</h2>
          <p className="text-[13px] text-ink-2">These filing types always appear in the digest.</p>
          {NEVER.map((n) => (
            <p key={n} className="flex items-center gap-[10px] text-[14px] text-ink">
              <span className="text-sage-text">✓</span>
              {n}
            </p>
          ))}
        </Card>
      </div>
    </>
  );
}
