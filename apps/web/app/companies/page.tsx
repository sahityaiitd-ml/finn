import Link from "next/link";
import { TickerSearch } from "@/components/TickerSearch";
import { Card } from "@/components/ui";

const DEMO = ["TCS", "DABUR", "TATASTEEL", "DIXON", "RELIANCE", "MARUTI"];

export default function Companies() {
  return (
    <main className="mx-auto flex w-full max-w-[1024px] flex-1 flex-col gap-4 px-4 pb-28 pt-8">
      <h1 className="text-[26px] text-ink">Companies</h1>
      <TickerSearch />
      <Card>
        <p className="text-[12px] font-medium text-muted">Demo names</p>
        {DEMO.map((s) => (
          <Link
            key={s}
            href={`/companies/${s}/promises`}
            className="flex min-h-[44px] items-center text-[15px] text-sage-text"
          >
            {s}
          </Link>
        ))}
      </Card>
    </main>
  );
}
