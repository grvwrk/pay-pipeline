import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { money, newIdempotencyKey } from "../lib/format";
import type { GuardedOrderResult, ReconcileResult } from "../lib/types";
import { useSession } from "../state/session";
import { PageHeader } from "../components/PageHeader";
import { PaymentLink } from "../components/PaymentLink";
import { PolicyPanel } from "../components/PolicyPanel";
import { Badge, Empty, Panel, Row, Spinner, toneForState } from "../components/ui";

export default function CartPage() {
  const { userId, cart, cartLoading, removeFromCart, clearCart, approvalToken, setApprovalToken } = useSession();

  // Reusing one idempotency key across retries is the point: a second submit of
  // the same intent must collide, not create a second order.
  const [idempotencyKey, setIdempotencyKey] = useState(newIdempotencyKey);
  const [result, setResult] = useState<GuardedOrderResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [payBusy, setPayBusy] = useState(false);
  const [payResult, setPayResult] = useState<Record<string, unknown> | null>(null);
  const [reconcile, setReconcile] = useState<ReconcileResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [watching, setWatching] = useState(false);

  const orderId = result?.order?.order_id;

  const checkPayment = useCallback(async () => {
    if (!orderId) return null;
    setChecking(true);
    try {
      const res = await api.reconcile(orderId);
      setReconcile(res);
      return res;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
      return null;
    } finally {
      setChecking(false);
    }
  }, [orderId]);

  // Razorpay settles out of band and, on an unreachable host, without a webhook.
  // Once the buyer opens the hosted checkout, poll the gateway until it has a verdict.
  useEffect(() => {
    if (!watching || !orderId) return;
    let cancelled = false;
    let attempts = 0;

    const timer = setInterval(async () => {
      attempts += 1;
      const res = await checkPayment();
      const settled = res?.outcome === "captured" || res?.outcome === "failed" || res?.outcome === "already_settled";
      if (cancelled || settled || attempts >= 20) {
        clearInterval(timer);
        if (!cancelled) setWatching(false);
      }
    }, 6000);

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [watching, orderId, checkPayment]);

  async function checkout(token?: string | null) {
    if (!cart) return;
    setBusy(true);
    setError(null);
    setPayResult(null);
    setReconcile(null);
    setWatching(false);
    try {
      const res = await api.checkout({
        cart_id: cart.cart_id,
        user_id: userId,
        idempotency_key: idempotencyKey,
        approval_token: token ?? null,
      });
      setResult(res);
      if (res.requires_approval && res.approval_token) setApprovalToken(res.approval_token);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function approveAndCheckout() {
    const token = result?.approval_token ?? approvalToken;
    if (!token) return;
    setBusy(true);
    try {
      await api.approve(token);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
      setBusy(false);
      return;
    }
    setBusy(false);
    await checkout(token);
  }

  async function pay(simulateFailure: boolean) {
    const order = result?.order;
    if (!order) return;
    setPayBusy(true);
    setError(null);
    try {
      const res = await api.initiatePayment({
        order_id: order.order_id,
        amount_inr: order.amount,
        method: "upi",
        simulate_failure: simulateFailure,
        user_id: userId,
      });
      setPayResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setPayBusy(false);
    }
  }

  function startOver() {
    clearCart();
    setResult(null);
    setPayResult(null);
    setReconcile(null);
    setWatching(false);
    setError(null);
    setIdempotencyKey(newIdempotencyKey());
  }

  if (!cart || cart.items.length === 0) {
    return (
      <div>
        <PageHeader title="Cart and checkout" subtitle="Carts are priced server-side, then pushed through the deterministic policy engine." />
        <div className="p-8">
          <Panel>
            <Empty
              title="Your cart is empty"
              hint="Add something from the catalog, or let the agent build a cart for you in the console."
              action={<Link className="btn-primary" to="/catalog">Browse catalog</Link>}
            />
          </Panel>
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Cart and checkout"
        subtitle="Carts are priced server-side, then pushed through the deterministic policy engine."
        actions={<button className="btn-ghost" onClick={startOver}>Start over</button>}
      />

      <div className="grid gap-6 p-8 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <div className="space-y-6">
          <Panel title="Items" actions={<span className="mono text-ink-400">{cart.cart_id}</span>}>
            <ul className="divide-y divide-ink-800">
              {cart.items.map((item) => (
                <li key={item.product_id} className="flex items-center gap-4 px-5 py-3.5">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{item.name}</p>
                    <p className="mono mt-0.5 text-ink-400">
                      {item.product_id} · {item.category.replace(/_/g, " ")}
                    </p>
                  </div>
                  <span className="mono shrink-0 text-ink-300">
                    {item.quantity} × {money(item.price)}
                  </span>
                  <span className="w-24 shrink-0 text-right text-sm tabular-nums">{money(item.subtotal)}</span>
                  <button
                    className="shrink-0 text-xs text-ink-400 hover:text-halt"
                    onClick={() => removeFromCart(item.product_id)}
                    disabled={cartLoading}
                    aria-label={`Remove ${item.name}`}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>

            {cart.applied_bundle && (
              <div className="border-t border-ink-800 bg-flow/5 px-5 py-3">
                <p className="text-xs font-medium text-flow">{cart.applied_bundle.title}</p>
                <p className="mt-1 text-xs leading-relaxed text-ink-300">
                  {cart.applied_bundle.rationale || cart.applied_bundle.description} — saves{" "}
                  {money(cart.applied_bundle.savings_amount)} ({cart.applied_bundle.discount_percentage}%)
                </p>
              </div>
            )}
          </Panel>

          {result?.policy_evaluation && <PolicyPanel evaluation={result.policy_evaluation} />}

          {result && !result.success && !result.requires_approval && (
            <div className="rounded-lg border border-halt/40 bg-halt/10 px-4 py-3 text-sm text-halt">
              <Badge tone="bad">{result.decision_code ?? "DENIED"}</Badge>
              <p className="mt-2 leading-relaxed">{result.reason}</p>
            </div>
          )}

          {result?.requires_approval && (
            <div className="rounded-lg border border-caution/40 bg-caution/10 px-4 py-3">
              <Badge tone="warn">GATED APPROVAL REQUIRED</Badge>
              <p className="mt-2 text-sm leading-relaxed text-ink-100">{result.reason}</p>
              <p className="mono mt-2 break-all text-ink-300">{result.approval_token}</p>
              <button className="btn-primary mt-3 text-xs" onClick={approveAndCheckout} disabled={busy}>
                Approve as human and retry checkout
              </button>
            </div>
          )}

          {result?.success && result.order && (
            <Panel
              title="Order created"
              actions={<Badge tone={toneForState(result.order.state)}>{result.order.state}</Badge>}
            >
              <div className="divide-y divide-ink-800 px-5 py-2">
                <Row k="Order ID" v={<span className="mono">{result.order.order_id}</span>} />
                <Row k="Receipt" v={<span className="mono">{result.order.receipt}</span>} />
                <Row k="Amount" v={money(result.order.amount)} />
                <Row k="Gateway status" v={result.order.status} />
              </div>

              {!result.payment_link && result.payment_link_error && (
                <div className="border-t border-ink-800 p-4">
                  <p className="rounded-lg border border-caution/40 bg-caution/5 px-3 py-2.5 text-xs leading-relaxed text-ink-300">
                    <span className="label text-caution">Payment link unavailable</span>
                    <br />
                    {result.payment_link_error}
                  </p>
                </div>
              )}

              {result.payment_link && (
                <div className="space-y-3 border-t border-ink-800 p-4">
                  <PaymentLink
                    url={result.payment_link}
                    amount={result.order.amount}
                    onOpened={() => setWatching(true)}
                  />
                  <div className="flex flex-wrap items-center gap-3">
                    <button className="btn-ghost text-xs" onClick={checkPayment} disabled={checking}>
                      {checking ? "Asking Razorpay…" : "Check payment status"}
                    </button>
                    {watching && !checking && (
                      <span className="text-xs text-ink-400">Watching for the outcome…</span>
                    )}
                  </div>
                  {reconcile && (
                    <p className={`rounded-lg border px-3 py-2 text-xs leading-relaxed ${
                      reconcile.outcome === "captured"
                        ? "border-signal/40 bg-signal/10 text-signal"
                        : reconcile.outcome === "failed" || reconcile.outcome === "error"
                          ? "border-halt/40 bg-halt/10 text-halt"
                          : "border-ink-700 bg-ink-850 text-ink-300"
                    }`}>
                      {reconcile.outcome === "captured" && "Payment captured. "}
                      {reconcile.outcome === "failed" && "Payment failed. "}
                      {reconcile.detail} Order is {reconcile.state}.
                    </p>
                  )}
                </div>
              )}

              <div className="flex flex-wrap items-center gap-2 border-t border-ink-800 px-5 py-4">
                <button className="btn-ghost" onClick={() => pay(false)} disabled={payBusy}>
                  Initiate test payment
                </button>
                <button className="btn-danger" onClick={() => pay(true)} disabled={payBusy}>
                  Simulate failure
                </button>
                {payBusy && <Spinner label="Contacting payment rail…" />}
              </div>

              {payResult && (
                <div className="border-t border-ink-800 px-5 py-4">
                  <p className="text-sm leading-relaxed text-ink-300">
                    {payResult.verification_pending
                      ? "Payment initiated. The order stays unpaid until a signed webhook confirms capture — that is the system refusing to mark its own money movement as done."
                      : String(payResult.error ?? "Payment attempt finished.")}
                  </p>
                  <p className="mt-2 text-xs text-ink-400">
                    Track the resulting state on the{" "}
                    <Link className="text-flow hover:underline" to="/orders">orders page</Link>.
                  </p>
                </div>
              )}
            </Panel>
          )}

          {error && (
            <div className="rounded-lg border border-halt/40 bg-halt/10 px-4 py-3 text-sm text-halt">
              {error}
            </div>
          )}
        </div>

        <div className="space-y-4">
          <Panel title="Summary">
            <div className="divide-y divide-ink-800 px-5 py-2">
              <Row k="Subtotal" v={money(cart.subtotal_amount)} />
              <Row k="Bundle discount" v={`- ${money(cart.discount_amount)}`} />
              <Row k="Shipping" v={money(cart.shipping_fee)} />
              <Row k="Total" v={<span className="text-base font-semibold">{money(cart.total_amount)}</span>} />
            </div>
            <div className="border-t border-ink-800 px-5 py-4">
              <label className="label" htmlFor="idem">Idempotency key</label>
              <input
                id="idem"
                className="field mono mt-1.5"
                value={idempotencyKey}
                onChange={(e) => setIdempotencyKey(e.target.value)}
                spellCheck={false}
              />
              <p className="mt-2 text-xs leading-relaxed text-ink-400">
                Check out twice with the same key to see double-spend protection reject the replay.
              </p>
              <button
                className="btn-primary mt-3 w-full"
                onClick={() => checkout(approvalToken)}
                disabled={busy || cartLoading}
              >
                {busy ? "Evaluating policy…" : "Run checkout"}
              </button>
            </div>
          </Panel>

          <Panel title="What happens next">
            <ol className="space-y-2.5 px-5 py-4 text-xs leading-relaxed text-ink-400">
              <li>1. Guardrails evaluate spend ceiling, category, quantity, currency and idempotency.</li>
              <li>2. Over the approval threshold, checkout stops and issues a human-approval token.</li>
              <li>3. On approval an order is created in ORDER_CREATED — never paid.</li>
              <li>4. Only a signature-verified webhook moves it to PAYMENT_CAPTURED.</li>
            </ol>
          </Panel>
        </div>
      </div>
    </div>
  );
}
