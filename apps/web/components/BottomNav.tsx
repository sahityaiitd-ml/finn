"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const stroke = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

const items = [
  { href: "/", label: "Today", match: (p: string) => p === "/" },
  {
    href: "/companies",
    label: "Companies",
    match: (p: string) => p.startsWith("/companies") || p.startsWith("/source"),
  },
  { href: "/profile", label: "Profile", match: (p: string) => p.startsWith("/profile") },
];

function Icon({ label }: { label: string }) {
  if (label === "Today")
    return (
      <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden {...stroke}>
        <path d="M3 13l3-8h12l3 8v6H3zM3 13h5l1 3h6l1-3h5" />
      </svg>
    );
  if (label === "Companies")
    return (
      <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden {...stroke}>
        <path d="M6 3h9l4 4v14H6zM14 3v5h5M9 12h7M9 16h7" />
      </svg>
    );
  return (
    <span className="grid size-[22px] place-items-center rounded-full bg-sage-tint text-[9px] font-semibold text-sage-text">
      AK
    </span>
  );
}

export function BottomNav() {
  const path = usePathname();
  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-10 border-t border-hairline bg-surface"
    >
      <div className="mx-auto flex h-[72px] max-w-[1024px] items-center justify-between px-[44px] pb-2">
        {items.map((it) => {
          const active = it.match(path);
          return (
            <Link
              key={it.label}
              href={it.href}
              aria-current={active ? "page" : undefined}
              className={`flex min-h-[44px] flex-col items-center gap-1 text-[12px] ${active ? "font-semibold text-sage-text" : "font-medium text-muted"}`}
            >
              <Icon label={it.label} />
              {it.label}
              <span className={`size-1 rounded-full ${active ? "bg-sage" : "bg-transparent"}`} />
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
