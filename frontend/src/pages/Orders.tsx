import { useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import { money, when } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import type { Order, ReconcileResult } from "../lib/types";
import { useSession } from "../state/session";
import { PageHeader } from "../components/PageHeader";
import { Badge, Empty, ErrorNote, Json, Panel, Row, Spinner, toneForState } from "../components/ui";

export default function Orders() {
  const { userId } = useSession();
  const { data, error, loading, reload } = useAsync(() => api.listOrders(100), []);
  const [selected, setSelected] = useState<Order | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncNote, setSyncNote] = useState<{ ok: boolean; text: string } | null>(null);

  const orders = data ?? [];

  // Razorpay cannot deliver a webhook to an unreachable host, so unsettled orders
  // are re-read straight from the gateway on demand.
  async function syncAll() {
    setSyncing(true);
    setSyncNote(null);
    try {
      const res = await api.reconcilePending();
      setSyncNote({
        ok: true,
        text:
          res.updated > 0
            ? `Checked ${res.checked} unsettled order(s) against Razorpay; ${res.updated} updated.`
            : `Checked ${res.checked} unsettled order(s); Razorpay reports no completed payments on them yet.`,
      });
      reload();
    } catch (err) {
      setSyncNote({ ok: false, text: err instanceof ApiError ? err.message : String(err) });
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Orders and refunds"
        subtitle="An order is authoritative only once the gateway confirms capture. Refunds are bounded by the captured amount."
        actions={
          <>
            <button className="btn-ghost" onClick={reload}>Refresh</button>
            <button className="btn-primary" onClick={syncAll} disabled={syncing}>
              {syncing ? "Asking Razorpay…" : "Sync with Razorpay"}
            </button>
          </>
        }
      />

      {syncNote && (
        <div className="px-8 pt-6">
          <p className={`rounded-lg border px-4 py-3 text-sm leading-relaxed ${
            syncNote.ok
              ? "border-ink-700 bg-ink-850 text-ink-300"
              : "border-halt/40 bg-halt/10 text-halt"
          }`}>
            {syncNote.text}
          </p>
        </div>
      )}

      <div className="grid gap-6 p-8 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <Panel title={`Orders (${orders.length})`}>
          {loading && <div className="px-5 py-6"><Spinner /></div>}
          {error && <ErrorNote error={error} onRetry={reload} />}
          {!loading && !error && orders.length === 0 && (
            <Empty title="No orders yet" hint="Run a checkout from the cart, or ask the agent console to buy something." />
          )}

          {orders.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-ink-800 text-ink-400">
                    <th className="px-5 py-2.5 font-medium">Order</th>
                    <th className="px-3 py-2.5 font-medium">Amount</th>
                    <th className="px-3 py-2.5 font-medium">State</th>
                    <th className="px-5 py-2.5 font-medium">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-ink-800">
                  {orders.map((o) => (
                    <tr
                      key={o.order_id}
                      onClick={() => setSelected(o)}
                      className={`cursor-pointer transition-colors hover:bg-ink-850 ${
                        selected?.order_id === o.order_id ? "bg-ink-850" : ""
                      }`}
                    >
                      <td className="px-5 py-3">
                        <span className="mono text-ink-100">{o.order_id}</span>
                        {o.notes?.bundle_applied === "true" && <Badge tone="info">bundle</Badge>}
                      </td>
                      <td className="px-3 py-3 tabular-nums">{money(o.amount)}</td>
                      <td className="px-3 py-3"><Badge tone={toneForState(o.state)}>{o.state}</Badge></td>
                      <td className="px-5 py-3 text-xs text-ink-400">{when(o.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>

        <div className="space-y-4">
          {selected ? <OrderDetail order={selected} onSynced={reload} /> : (
            <Panel title="Order detail">
              <p className="px-5 py-8 text-center text-xs text-ink-400">Select an order to inspect it.</p>
            </Panel>
          )}
          <RefundForm userId={userId} onDone={reload} />
        </div>
      </div>
    </div>
  );
}

const SETTLED: string[] = ["PAYMENT_CAPTURED", "COMPLETED", "REFUNDED"];

function OrderDetail({ order, onSynced }: { order: Order; onSynced: () => void }) {
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<ReconcileResult | null>(null);
  const link = order.notes?.payment_link_url;

  // A fresh selection must not inherit the previous order's verdict.
  useEffect(() => setOutcome(null), [order.order_id]);

  async function sync() {
    setBusy(true);
    try {
      setOutcome(await api.reconcile(order.order_id));
      onSynced();
    } catch (err) {
      setOutcome({
        order_id: order.order_id,
        changed: false,
        outcome: "error",
        state: order.state,
        detail: err instanceof ApiError ? err.message : String(err),
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel title="Order detail" actions={<Badge tone={toneForState(order.state)}>{order.state}</Badge>}>
      <div className="divide-y divide-ink-800 px-5 py-2">
        <Row k="Order ID" v={<span className="mono">{order.order_id}</span>} />
        <Row k="Cart" v={<span className="mono">{order.cart_id}</span>} />
        <Row k="Receipt" v={<span className="mono">{order.receipt}</span>} />
        <Row k="Amount" v={money(order.amount)} />
        <Row k="In paise" v={<span className="mono">{order.amount_in_paise ?? "—"}</span>} />
        <Row k="Gateway status" v={order.status} />
        <Row k="Idempotency key" v={<span className="mono break-all">{order.idempotency_key ?? "—"}</span>} />
        <Row k="Created" v={when(order.created_at)} />
      </div>

      <div className="space-y-3 border-t border-ink-800 px-5 py-4">
        <div className="flex flex-wrap items-center gap-2">
          {!SETTLED.includes(order.state) && (
            <button className="btn-ghost text-xs" onClick={sync} disabled={busy}>
              {busy ? "Asking Razorpay…" : "Check payment status"}
            </button>
          )}
          {link && (
            <a className="btn-ghost text-xs" href={link} target="_blank" rel="noreferrer">
              Open payment link ↗
            </a>
          )}
        </div>

        {outcome && (
          <p className={`rounded-lg border px-3 py-2 text-xs leading-relaxed ${
            outcome.outcome === "captured"
              ? "border-signal/40 bg-signal/10 text-signal"
              : outcome.outcome === "failed" || outcome.outcome === "error"
                ? "border-halt/40 bg-halt/10 text-halt"
                : "border-ink-700 bg-ink-850 text-ink-300"
          }`}>
            {outcome.detail}
            {outcome.changed && ` Order is now ${outcome.state}.`}
          </p>
        )}
      </div>

      {Object.keys(order.notes ?? {}).length > 0 && (
        <div className="border-t border-ink-800 p-4">
          <p className="label mb-2">Notes</p>
          <Json data={order.notes} />
        </div>
      )}
    </Panel>
  );
}

function RefundForm({ userId, onDone }: { userId: string; onDone: () => void }) {
  const [paymentId, setPaymentId] = useState("");
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("Customer request");
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<{ ok: boolean; text: string } | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setOutcome(null);
    try {
      const res = await api.refund({
        payment_id: paymentId.trim(),
        amount_inr: Number(amount),
        user_id: userId,
        reason,
      });
      setOutcome({ ok: true, text: `Refund ${res.refund.refund_id} processed for ${money(res.refund.amount)}.` });
      onDone();
    } catch (err) {
      setOutcome({ ok: false, text: err instanceof ApiError ? err.message : String(err) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel title="Issue refund">
      <form className="space-y-3 px-5 py-4" onSubmit={submit}>
        <div>
          <label className="label" htmlFor="pid">Payment ID</label>
          <input id="pid" className="field mono mt-1.5" placeholder="pay_xxxxxxxx" value={paymentId} onChange={(e) => setPaymentId(e.target.value)} required />
        </div>
        <div>
          <label className="label" htmlFor="amt">Amount (INR)</label>
          <input id="amt" className="field mt-1.5" type="number" min="0.01" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} required />
        </div>
        <div>
          <label className="label" htmlFor="rsn">Reason</label>
          <input id="rsn" className="field mt-1.5" value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
        <button className="btn-primary w-full" type="submit" disabled={busy || !paymentId || !amount}>
          {busy ? "Evaluating refund policy…" : "Issue refund"}
        </button>
        {outcome && (
          <p className={`rounded-lg border px-3 py-2 text-xs leading-relaxed ${
            outcome.ok
              ? "border-signal/40 bg-signal/10 text-signal"
              : "border-halt/40 bg-halt/10 text-halt"
          }`}>
            {outcome.text}
          </p>
        )}
        <p className="text-xs leading-relaxed text-ink-400">
          Refunds are traced back to the original payment and cannot exceed the remaining captured balance.
        </p>
      </form>
    </Panel>
  );
}
