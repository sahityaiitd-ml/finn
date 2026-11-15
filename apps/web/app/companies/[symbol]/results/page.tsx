import { Suspense } from "react";
import { Hub } from "@/components/Hub";
import { ResultsCard } from "@/components/ResultsCard";
import { Card } from "@/components/ui";
import { getResults } from "@/lib/api";
import { fiscalLabel } from "@/lib/format";

async function Content({ params }: { params: Promise<{ symbol: string }> }) {
  const symbol = (await params).symbol.toUpperCase();
  const v = await getResults(symbol);
  if (!v) {
    return (
      <Hub symbol={symbol} name={symbol} active="results">
        <Card>
          <p className="text-[15px] text-ink">No results parsed for {symbol} yet.</p>
          <p className="text-[13px] text-ink-2">
            Results appear once a results filing is stored and checked.
          </p>
        </Card>
      </Hub>
    );
  }
  return (
    <Hub
      symbol={v.symbol}
      name={v.name}
      active="results"
      asOf={`Data as of ${fiscalLabel(v.period)}`}
    >
      <ResultsCard v={v} />
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
