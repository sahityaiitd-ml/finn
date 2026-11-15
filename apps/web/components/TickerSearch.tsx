"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function TickerSearch() {
  const router = useRouter();
  const [v, setV] = useState("");
  const sym = v
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9&-]/g, "");
  return (
    <form
      className="flex gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (sym) router.push(`/companies/${sym}/promises`);
      }}
    >
      <input
        value={v}
        onChange={(e) => setV(e.target.value)}
        placeholder="Any NSE ticker, e.g. TITAN"
        aria-label="NSE ticker"
        autoCapitalize="characters"
        className="min-h-[44px] min-w-px flex-1 rounded-full border border-border bg-surface px-4 text-[14px] text-ink placeholder:text-muted"
      />
      <button
        type="submit"
        className="min-h-[44px] rounded-full bg-sage-600 px-5 text-[14px] font-medium text-surface"
      >
        Open
      </button>
    </form>
  );
}
