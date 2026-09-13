const inr = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 2,
});

export const money = (n: number | null | undefined) => (typeof n === "number" ? inr.format(n) : "—");

export const pct = (n: number | null | undefined, fractionDigits = 1) =>
  typeof n === "number" ? `${n.toFixed(fractionDigits)}%` : "—";

export const ratio = (n: number | null | undefined) =>
  typeof n === "number" ? `${(n * 100).toFixed(0)}%` : "—";

export function when(iso: string | null | undefined) {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export const shortHash = (h: string | null | undefined, n = 10) =>
  h ? `${h.slice(0, n)}…${h.slice(-4)}` : "—";

/** Stable-enough client key so a double-click can't create two orders. */
export const newIdempotencyKey = () => `idem_${crypto.randomUUID().replace(/-/g, "").slice(0, 20)}`;
