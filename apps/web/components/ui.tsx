import Link from "next/link";

const stroke = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export function ArrowUpRight({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden {...stroke}>
      <path d="M5 11l6-6M6 5h5v5" />
    </svg>
  );
}
export function ArrowLeft() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden {...stroke}>
      <path d="M19 12H5M11 6l-6 6 6 6" />
    </svg>
  );
}
export function ArrowRight() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden {...stroke}>
      <path d="M3 8h10M9 4l4 4-4 4" />
    </svg>
  );
}
export function Warn() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden {...stroke}>
      <path d="M8 2l6.5 11.5h-13zM8 6.5v3M8 11.6v.1" />
    </svg>
  );
}

type Tone = "sage" | "terra" | "amber" | "neutral";
const pillTone: Record<Tone, string> = {
  sage: "bg-sage-tint text-sage-text",
  terra: "bg-terra-bg text-terra",
  amber: "bg-amber-bg text-amber",
  neutral: "bg-sand/30 text-ink-2",
};

/** Colour means severity only; type pills stay neutral. */
export function Pill({ label, tone = "neutral" }: { label: string; tone?: Tone }) {
  return (
    <span
      className={`inline-flex rounded-full px-[10px] py-[3px] text-[12px] font-medium ${pillTone[tone]}`}
    >
      {label}
    </span>
  );
}

/** Proof link: 13px / 500 / sage-text, 44px hit area, sits under the evidence it supports. */
export function SourceLink({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="inline-flex min-h-[44px] items-center gap-1 text-[13px] font-medium text-sage-text"
    >
      {label}
      <ArrowUpRight />
    </Link>
  );
}

export function LinkButton({
  href,
  label,
  arrow = true,
}: {
  href: string;
  label: string;
  arrow?: boolean;
}) {
  return (
    <Link
      href={href}
      className="inline-flex min-h-[44px] items-center gap-2 text-[14px] font-medium text-sage-text"
    >
      {label}
      {arrow && <ArrowRight />}
    </Link>
  );
}

export function Card({ children }: { children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-[14px] rounded-[16px] bg-surface p-[18px] shadow-card">
      {children}
    </section>
  );
}
