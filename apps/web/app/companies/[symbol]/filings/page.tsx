import { Suspense } from "react";
import { Hub } from "@/components/Hub";
import { Card } from "@/components/ui";

async function Content({ params }: { params: Promise<{ symbol: string }> }) {
  const s = (await params).symbol.toUpperCase();
  return (
    <Hub symbol={s} name={s} active="filings">
      <Card>
        <p className="text-[15px] text-ink">Coming in a later milestone.</p>
      </Card>
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
