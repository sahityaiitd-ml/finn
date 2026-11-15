import { Suspense } from "react";
import { Hub } from "@/components/Hub";
import { LedgerBuilder } from "@/components/LedgerBuilder";
import { PromisesView } from "@/components/PromisesView";
import { getPromises } from "@/lib/api";
import { fiscalLabel } from "@/lib/format";

async function Content({ params }: { params: Promise<{ symbol: string }> }) {
  const symbol = (await params).symbol.toUpperCase();
  const d = await getPromises(symbol);
  const name = d?.name ?? symbol;
  return (
    <Hub
      symbol={symbol}
      name={name}
      active="promises"
      asOf={d?.reported_through ? `Results through ${fiscalLabel(d.reported_through)}` : undefined}
    >
      {d && d.rows.length > 0 ? (
        <PromisesView data={d} />
      ) : (
        <LedgerBuilder symbol={symbol} calls={d?.calls ?? []} />
      )}
    </Hub>
  );
}

export default function Page({ params }: { params: Promise<{ symbol: string }> }) {
  return (
    <Suspense fallback={<p className="p-6 text-ink-2">Loading…</p>}>
      <Content params={params} />
    </Suspense>
  );
}
