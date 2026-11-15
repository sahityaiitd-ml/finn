"use client";

import { useState } from "react";
import { type Settings, send } from "@/lib/api";
import { Card } from "./ui";

const OPTIONS = [
  { hours: 24, label: "Last 24 hours", sub: "Default. What happened since yesterday." },
  { hours: 72, label: "Last 3 days", sub: "Useful after a weekend." },
  { hours: 168, label: "Last 7 days", sub: "A weekly catch-up." },
];

export function WindowPicker({ initial }: { initial: number }) {
  const [hours, setHours] = useState(initial);
  const [saved, setSaved] = useState(false);
  async function pick(h: number) {
    setHours(h);
    setSaved(false);
    setSaved(!!(await send<Settings>("/settings", "PUT", { window_hours: h })));
  }
  return (
    <Card>
      <div role="radiogroup" aria-label="Digest window">
        {OPTIONS.map((o) => (
          <button
            key={o.hours}
            type="button"
            role="radio"
            aria-checked={hours === o.hours}
            onClick={() => pick(o.hours)}
            className="flex min-h-[56px] w-full items-center gap-3 border-b border-hairline text-left last:border-b-0"
          >
            <span
              className={`grid size-5 place-items-center rounded-full border ${hours === o.hours ? "border-sage-600" : "border-border"}`}
            >
              {hours === o.hours && <span className="size-[10px] rounded-full bg-sage-600" />}
            </span>
            <span className="min-w-px flex-1">
              <span className="block text-[15px] text-ink">{o.label}</span>
              <span className="block text-[12px] text-muted">{o.sub}</span>
            </span>
          </button>
        ))}
      </div>
      {saved && <p className="text-[12px] text-sage-text">Saved. Today opens on this window.</p>}
    </Card>
  );
}
