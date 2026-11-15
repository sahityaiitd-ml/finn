import Link from "next/link";
import { Card } from "@/components/ui";

const DEMO = ["TCS", "RELIANCE", "TATASTEEL", "DABUR", "MARUTI"];

export default function Companies() {
  return (
    <main className="mx-auto w-full max-w-[1024px] flex-1 px-4 pb-28 pt-8">
      <h1 className="text-[26px] text-ink">Companies</h1>
      <p className="mb-4 mt-1 text-[13px] text-ink-2">
        Search arrives in a later milestone. Demo names:
      </p>
      <Card>
        {DEMO.map((s) => (
          <Link
            key={s}
            href={`/companies/${s}/results`}
            className="flex min-h-[44px] items-center text-[15px] text-sage-text"
          >
            {s}
          </Link>
        ))}
      </Card>
    </main>
  );
}
