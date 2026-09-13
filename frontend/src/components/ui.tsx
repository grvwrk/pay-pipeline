import type { ReactNode } from "react";
import { ApiError } from "../lib/api";

export function Panel({ title, actions, children, className = "" }: {
  title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      {(title || actions) && (
        <header className="panel-head">
          <h2 className="text-sm font-semibold text-ink-100">{title}</h2>
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}

type Tone = "neutral" | "good" | "warn" | "bad" | "info";

const TONES: Record<Tone, string> = {
  neutral: "border-ink-600 text-ink-300",
  good: "border-signal/40 bg-signal/10 text-signal",
  warn: "border-caution/40 bg-caution/10 text-caution",
  bad: "border-halt/40 bg-halt/10 text-halt",
  info: "border-flow/40 bg-flow/10 text-flow",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-medium tracking-wide ${TONES[tone]}`}>
      {children}
    </span>
  );
}

/** Maps a backend transaction state or decision code onto a visual tone. */
export function toneForState(state: string | null | undefined): Tone {
  const s = (state ?? "").toUpperCase();
  if (s.includes("CAPTURED") || s === "COMPLETED" || s === "APPROVED" || s === "SUCCESS" || s === "VERIFIED") return "good";
  if (s.includes("DENIED") || s.includes("FAILED") || s.includes("HALT")) return "bad";
  if (s.includes("PENDING") || s.includes("GATED") || s.includes("APPROVAL")) return "warn";
  if (s.includes("REFUND")) return "info";
  return "neutral";
}

export function Stat({ label, value, hint, tone = "neutral" }: {
  label: string; value: ReactNode; hint?: ReactNode; tone?: Tone;
}) {
  const valueTone =
    tone === "good" ? "text-signal" :
    tone === "bad" ? "text-halt" :
    tone === "warn" ? "text-caution" : "text-ink-100";
  return (
    <div className="panel px-5 py-4">
      <div className="label">{label}</div>
      <div className={`mt-2 text-2xl font-semibold tabular-nums ${valueTone}`}>{value}</div>
      {hint && <div className="mt-1 text-xs text-ink-400">{hint}</div>}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2.5 text-sm text-ink-400">
      <span className="size-3.5 animate-spin rounded-full border-2 border-ink-600 border-t-ink-100" />
      {label ?? "Loading…"}
    </div>
  );
}

export function Empty({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-14 text-center">
      <p className="text-sm font-medium text-ink-300">{title}</p>
      {hint && <p className="max-w-md text-xs leading-relaxed text-ink-400">{hint}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

/**
 * Several endpoints deliberately 404 when there's nothing to report yet
 * (empty audit ledger, no captured orders). Show those as guidance, not failure.
 */
export function ErrorNote({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const isApi = error instanceof ApiError;
  const benign = isApi && error.status === 404;
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div className={`m-5 rounded-lg border px-4 py-3 text-sm ${
      benign ? "border-ink-700 bg-ink-850 text-ink-300"
             : "border-halt/40 bg-halt/10 text-halt"
    }`}>
      <div className="flex items-start justify-between gap-4">
        <p className="leading-relaxed">{message}</p>
        {onRetry && (
          <button className="btn-ghost shrink-0 px-2.5 py-1 text-xs" onClick={onRetry}>Retry</button>
        )}
      </div>
    </div>
  );
}

export function Json({ data }: { data: unknown }) {
  return (
    <pre className="mono max-h-80 overflow-auto rounded-lg border border-ink-700 bg-ink-950 p-3 leading-relaxed text-ink-300">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

export function Row({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5 text-sm">
      <span className="text-ink-400">{k}</span>
      <span className="text-right text-ink-100">{v}</span>
    </div>
  );
}
