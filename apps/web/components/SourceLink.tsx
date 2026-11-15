"use client";

import Link from "next/link";
import { ArrowUpRight } from "./ui";
import { useSourceSheet } from "./SourceSheet";

const SOURCE = /^\/source\/([0-9a-f]+)\/(\d+)(?:\?(.*))?$/;

/** Proof link: 13px / 500 / sage-text, 44px hit area. Opens the bottom sheet at the cited page.
 *  Without JavaScript (or outside the provider) it is a normal link to the full source page. */
export function SourceLink({
  href,
  label,
  read,
}: {
  href: string;
  label: string;
  read?: string | null;
}) {
  const sheet = useSourceSheet();
  const m = SOURCE.exec(href);
  return (
    <Link
      href={href}
      onClick={(e) => {
        if (!sheet || !m) return;
        e.preventDefault();
        const q = new URLSearchParams(m[3] ?? "");
        sheet.open({
          sha: m[1],
          page: Number(m[2]),
          line: q.get("line"),
          quote: q.get("q"),
          read,
        });
      }}
      className="inline-flex min-h-[44px] items-center gap-1 text-[13px] font-medium text-sage-text"
    >
      {label}
      <ArrowUpRight />
    </Link>
  );
}
