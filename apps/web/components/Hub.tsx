import Link from "next/link";
import { ArrowLeft } from "./ui";

const tabs = ["promises", "results", "filings"] as const;

export function Hub({
  symbol,
  name,
  active,
  asOf,
  children,
}: {
  symbol: string;
  name: string;
  active: (typeof tabs)[number];
  asOf?: string;
  children: React.ReactNode;
}) {
  return (
    <>
      <header className="border-b border-hairline bg-surface px-5 pt-6">
        <div className="mx-auto flex max-w-[1024px] flex-col gap-[10px]">
          <div className="flex items-center gap-[10px]">
            <Link href="/companies" aria-label="Back to Companies" className="-m-3 p-3 text-ink-2">
              <ArrowLeft />
            </Link>
            <span className="text-[14px] text-ink-2">Companies</span>
            <span className="flex-1" />
            {asOf && <span className="text-[12px] text-muted">{asOf}</span>}
          </div>
          <h1 className="text-[26px] text-ink">{name}</h1>
          <p className="text-[13px] text-ink-2">{symbol}</p>
          <nav aria-label="Company sections" className="flex gap-6 pt-1">
            {tabs.map((t) => (
              <Link
                key={t}
                href={`/companies/${symbol}/${t}`}
                aria-current={t === active ? "page" : undefined}
                className={`flex min-h-[44px] items-center text-[15px] capitalize ${
                  t === active ? "border-b-2 border-sage font-medium text-sage-text" : "text-ink-2"
                }`}
              >
                {t}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <div className="mx-auto flex w-full max-w-[1024px] flex-col gap-3 px-4 pb-28 pt-4">
        {children}
      </div>
    </>
  );
}
