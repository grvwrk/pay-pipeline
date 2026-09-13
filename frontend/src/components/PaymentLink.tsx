import { useState } from "react";
import { money } from "../lib/format";

/**
 * A Razorpay hosted-checkout short_url returned alongside a created order.
 * It is the only way the buyer actually moves money, so it gets a real
 * call-to-action rather than being buried in the raw payload.
 */
export function PaymentLink({ url, amount, compact = false, onOpened }: {
  url: string;
  amount?: number;
  compact?: boolean;
  /** Fired when the buyer opens the hosted checkout, so the caller can start watching for the outcome. */
  onOpened?: () => void;
}) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard blocked; the link is still visible and selectable below */
    }
  }

  return (
    <div className={`rounded-lg border border-signal/40 bg-signal/5 ${compact ? "p-3" : "px-4 py-3.5"}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="label text-signal">Razorpay payment link</p>
          {typeof amount === "number" && (
            <p className="mt-1 text-sm text-ink-300">
              Pay <span className="font-semibold text-ink-100">{money(amount)}</span> on Razorpay hosted checkout.
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <a className="btn-primary text-xs" href={url} target="_blank" rel="noreferrer" onClick={onOpened}>
            Pay now ↗
          </a>
          <button className="btn-ghost text-xs" onClick={copy} type="button">
            {copied ? "Copied ✓" : "Copy link"}
          </button>
        </div>
      </div>

      <a
        className="mono mt-2.5 block break-all text-flow hover:underline"
        href={url}
        target="_blank"
        rel="noreferrer"
      >
        {url}
      </a>

      <p className="mt-2 text-xs leading-relaxed text-ink-400">
        Completing this link does not mark the order paid on its own — capture is recorded only when the signed
        webhook arrives.
      </p>
    </div>
  );
}
