import Link from "next/link";
import { Suspense } from "react";
import { WindowPicker } from "@/components/WindowPicker";
import { ArrowLeft } from "@/components/ui";
import { getSettings } from "@/lib/api";

async function Content() {
  const s = await getSettings();
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
          <h1 className="text-[28px] text-ink">Digest window</h1>
          <p className="text-[13px] text-ink-2">How far back Today looks by default.</p>
        </div>
      </header>
      <div className="mx-auto w-full max-w-[640px] px-4 pb-28 pt-4">
        <WindowPicker initial={s?.window_hours ?? 24} />
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
