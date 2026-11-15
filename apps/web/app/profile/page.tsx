import { Suspense } from "react";
import { Card, RowLink, Switch } from "@/components/ui";
import { getDigest, getSettings } from "@/lib/api";

const WINDOW = { 24: "Last 24 hours", 72: "Last 3 days", 168: "Last 7 days" } as Record<
  number,
  string
>;

async function Content() {
  const [s, d] = await Promise.all([getSettings(), getDigest("24h")]);
  const rules = s
    ? `Volume ${s.vol_mult > 0 ? `${s.vol_mult}×` : "off"} · price ${s.price_pct > 0 ? `±${s.price_pct}%` : "off"}`
    : "";
  const reviewed = d ? d.counts.main - d.counts.to_review : 0;
  return (
    <>
      <header className="bg-surface px-5 pb-5 pt-6">
        <div className="mx-auto flex max-w-[640px] flex-col gap-[14px]">
          <h1 className="text-[28px] text-ink">Profile</h1>
          <div className="flex items-center gap-[14px]">
            <span className="grid size-16 place-items-center rounded-full bg-sage-tint text-[24px] font-semibold text-sage-text">
              AK
            </span>
            <div>
              <p className="text-[20px] font-medium text-ink">Alok Khandelwal</p>
              <p className="text-[13px] text-ink-2">Core team · ENAM Holdings</p>
            </div>
          </div>
        </div>
      </header>

      <div className="mx-auto flex w-full max-w-[640px] flex-col gap-3 px-4 pb-28 pt-4">
        <Card>
          <h2 className="text-[16px] font-medium text-ink">Your coverage</h2>
          <div className="flex">
            <div className="flex-1 pr-2">
              <p className="text-[12px] text-muted">Holdings</p>
              <p className="text-[17px] text-ink">{s?.holdings ?? "—"}</p>
            </div>
            <span className="w-px bg-hairline" />
            <div className="flex-1 pl-3 pr-2">
              <p className="text-[12px] text-muted">Research</p>
              <p className="text-[17px] text-ink">{s?.research ?? "—"}</p>
            </div>
            <span className="w-px bg-hairline" />
            <div className="flex-1 pl-3 pr-2">
              <p className="text-[12px] text-muted">Reviewed today</p>
              <p className="text-[17px] text-ink">{d ? `${reviewed} of ${d.counts.main}` : "—"}</p>
            </div>
          </div>
        </Card>

        <Card>
          <h2 className="border-b border-hairline pb-2 text-[16px] font-medium text-ink">
            Preferences
          </h2>
          <div>
            <RowLink
              href="/companies"
              title="Holdings & research"
              sub={`${s?.holdings ?? 18} held · ${s?.research ?? 4} research · open any ticker`}
            />
            <RowLink href="/profile/alerts" title="Alert rules" sub={rules} />
            <RowLink
              href="/profile/window"
              title="Digest window"
              sub={WINDOW[s?.window_hours ?? 24] ?? "Last 24 hours"}
            />
            <RowLink
              title="Data sources"
              sub="BSE/NSE filings via screener.in · screener.in transcripts · yfinance EOD prices"
            />
            <RowLink title="Appearance" sub="Day" />
          </div>
        </Card>

        <Card>
          <h2 className="border-b border-hairline pb-2 text-[16px] font-medium text-ink">
            Notifications
          </h2>
          <div className="flex min-h-[56px] items-center gap-3">
            <div className="min-w-px flex-1">
              <p className="text-[15px] text-ink">Evening digest</p>
              <p className="text-[13px] text-muted">
                Coming soon · for now, open Today after the close
              </p>
            </div>
            <Switch on={false} label="Evening digest" />
          </div>
        </Card>

        <p className="pt-2 text-center text-[12px] text-muted">FINN prototype · no sign-in</p>
      </div>
    </>
  );
}

export default function Page() {
  return (
    <main className="flex-1">
      <Suspense fallback={<p className="p-6 text-ink-2">Loading…</p>}>
        <Content />
      </Suspense>
    </main>
  );
}
