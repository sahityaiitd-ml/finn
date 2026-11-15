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

export { SourceLink } from "./SourceLink";

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

export function ExternalSourceLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex min-h-[44px] items-center gap-1 text-[13px] font-medium text-sage-text"
    >
      {label}
      <ArrowUpRight />
    </a>
  );
}

export function Check({ size = 18 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      aria-hidden
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="10" cy="10" r="8" />
      <path d="M6.5 10.2l2.4 2.4 4.6-5" />
    </svg>
  );
}

export function Chevron({ open }: { open?: boolean }) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 20 20"
      aria-hidden
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={open ? "rotate-90" : ""}
    >
      <path d="M8 5l5 5-5 5" />
    </svg>
  );
}

export function Switch({
  on,
  onChange,
  label,
}: {
  on: boolean;
  onChange?: (v: boolean) => void;
  label: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      disabled={!onChange}
      onClick={onChange ? () => onChange(!on) : undefined}
      className={`relative h-7 w-[46px] shrink-0 rounded-full transition-colors ${on ? "bg-sage-600" : "bg-track"} ${onChange ? "" : "opacity-60"}`}
    >
      <span
        className={`absolute top-[3px] size-[22px] rounded-full bg-surface shadow-sm transition-all ${on ? "left-[21px]" : "left-[3px]"}`}
      />
    </button>
  );
}

export function RowLink({ href, title, sub }: { href?: string; title: string; sub: string }) {
  const body = (
    <>
      <div className="min-w-px flex-1">
        <p className="text-[15px] text-ink">{title}</p>
        <p className="text-[12px] text-muted">{sub}</p>
      </div>
      {href && <Chevron />}
    </>
  );
  const cls = "flex min-h-[56px] items-center gap-3 border-b border-hairline last:border-b-0";
  return href ? (
    <Link href={href} className={cls}>
      {body}
    </Link>
  ) : (
    <div className={cls}>{body}</div>
  );
}
