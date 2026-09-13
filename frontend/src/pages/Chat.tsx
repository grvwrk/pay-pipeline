import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { money, newIdempotencyKey } from "../lib/format";
import type { ChatResponse } from "../lib/types";
import { useSession } from "../state/session";
import { PageHeader } from "../components/PageHeader";
import { PaymentLink } from "../components/PaymentLink";
import { PolicyPanel } from "../components/PolicyPanel";
import { ReasoningTrace } from "../components/ReasoningTrace";
import { Badge, Json, Panel, Row, Spinner, toneForState } from "../components/ui";

interface Turn {
  id: string;
  role: "user" | "agent";
  text: string;
  response?: ChatResponse;
  failed?: boolean;
}

const SUGGESTIONS = [
  "Find me a good mechanical keyboard under ₹5000",
  "Buy the Keychron K2 with the wrist rest bundle",
  "I want to purchase a ₹7999 keyboard",
  "What is the status of my last order?",
];

export default function Chat() {
  const { userId, setApprovalToken } = useSession();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [forceFail, setForceFail] = useState(false);
  const [selected, setSelected] = useState<ChatResponse | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, busy]);

  async function send(
    message: string,
    opts: { approvalToken?: string; sku?: string; includeBundle?: boolean } = {},
  ) {
    const text = message.trim();
    if (!text || busy) return;

    setTurns((t) => [...t, { id: crypto.randomUUID(), role: "user", text }]);
    setInput("");
    setBusy(true);

    try {
      const res = await api.chat({
        user_message: text,
        user_id: userId,
        approval_token: opts.approvalToken ?? null,
        idempotency_key: newIdempotencyKey(),
        sku: opts.sku ?? null,
        force_fail_payment: forceFail,
        include_bundle: opts.includeBundle ?? false,
      });
      setTurns((t) => [...t, { id: crypto.randomUUID(), role: "agent", text: res.message, response: res }]);
      setSelected(res);
      if (res.type === "APPROVAL_REQUIRED" && res.approval_token) setApprovalToken(res.approval_token);
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : String(err);
      setTurns((t) => [...t, { id: crypto.randomUUID(), role: "agent", text: detail, failed: true }]);
    } finally {
      setBusy(false);
    }
  }

  // The policy engine gates high-value carts. Registering the token unlocks the
  // gated money tool, then we re-issue the purchase carrying that token.
  async function approveAndRetry(token: string) {
    await api.approve(token).catch(() => null);
    await send("Approved - proceed with the purchase.", { approvalToken: token });
  }

  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title="Agent console"
        subtitle="The orchestrator is untrusted: it reads the catalog and builds carts freely, but every money-moving step is decided by the policy engine."
        actions={
          <>
            <label className="flex cursor-pointer items-center gap-2 text-xs text-ink-300">
              <input
                type="checkbox"
                className="accent-halt"
                checked={forceFail}
                onChange={(e) => setForceFail(e.target.checked)}
              />
              Force payment failure
            </label>
            <button
              className="btn-ghost"
              onClick={() => {
                setTurns([]);
                setSelected(null);
              }}
              disabled={turns.length === 0}
            >
              Clear
            </button>
          </>
        }
      />

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-6 overflow-hidden p-8 xl:grid-cols-[minmax(0,1fr)_26rem]">
        {/* Conversation */}
        <div className="flex min-h-0 flex-col gap-4">
          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
            {turns.length === 0 && (
              <div className="panel px-6 py-8">
                <p className="text-sm text-ink-300">Ask the agent to find or buy something.</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button key={s} className="btn-ghost text-xs" onClick={() => send(s)}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {turns.map((turn) =>
              turn.role === "user" ? (
                <div key={turn.id} className="flex justify-end">
                  <p className="max-w-[80%] rounded-xl rounded-br-sm bg-ink-800 px-4 py-2.5 text-sm leading-relaxed">
                    {turn.text}
                  </p>
                </div>
              ) : (
                <div key={turn.id} className="flex justify-start">
                  <div
                    className={`max-w-[85%] space-y-3 rounded-xl rounded-bl-sm border px-4 py-3 ${
                      turn.failed
                        ? "border-halt/40 bg-halt/5"
                        : "border-ink-700 bg-ink-900"
                    }`}
                  >
                    {turn.response && (
                      <Badge tone={toneForState(turn.response.type)}>{turn.response.type.replace(/_/g, " ")}</Badge>
                    )}
                    <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink-100">{turn.text}</p>

                    <ResponseExtras
                      response={turn.response}
                      onApprove={approveAndRetry}
                      onBuy={(sku, opts) =>
                        send(opts?.label ?? `Buy ${sku}`, { sku, includeBundle: opts?.bundle })
                      }
                    />

                    {turn.response && (
                      <button
                        className="text-xs text-flow hover:underline"
                        onClick={() => setSelected(turn.response!)}
                      >
                        Inspect decision →
                      </button>
                    )}
                  </div>
                </div>
              ),
            )}

            {busy && (
              <div className="px-1">
                <Spinner label="Agents reasoning…" />
              </div>
            )}
            <div ref={endRef} />
          </div>

          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
          >
            <input
              className="field"
              placeholder="Ask for a product, or tell the agent to buy one…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={busy}
            />
            <button className="btn-primary px-5" type="submit" disabled={busy || !input.trim()}>
              Send
            </button>
          </form>
        </div>

        {/* Inspector */}
        <div className="min-h-0 overflow-y-auto">
          <Inspector response={selected} />
        </div>
      </div>
    </div>
  );
}

function ResponseExtras({
  response,
  onApprove,
  onBuy,
}: {
  response?: ChatResponse;
  onApprove: (token: string) => void;
  onBuy: (sku: string, opts?: { bundle?: boolean; label?: string }) => void;
}) {
  if (!response) return null;

  const orderAmount =
    typeof (response.order as Record<string, unknown> | undefined)?.amount === "number"
      ? ((response.order as Record<string, unknown>).amount as number)
      : response.cart?.total_amount;

  // On a purchase, `products` carries the alternatives that were not chosen.
  const alreadyOrdered = response.type === "ORDER_CREATED";
  const alternatives = (response.products ?? []).filter((p) => p.id !== response.top_choice?.id);

  return (
    <>
      {response.payment_link && <PaymentLink url={response.payment_link} amount={orderAmount} compact />}

      {/*
        An order exists but the gateway refused to mint a link. Rendering nothing here
        leaves a created order with no way to pay and no clue why, so surface the
        gateway's own reason instead.
      */}
      {!response.payment_link && alreadyOrdered && (
        <div className="rounded-lg border border-caution/40 bg-caution/5 px-3 py-2.5">
          <p className="label text-caution">Payment link unavailable</p>
          <p className="mt-1 text-xs leading-relaxed text-ink-300">
            {response.payment_link_error ??
              "The payment gateway did not return a link for this order."}
          </p>
          <p className="mt-1.5 text-xs leading-relaxed text-ink-400">
            The order itself was created and is unpaid. Settle it from the{" "}
            <Link className="text-flow hover:underline" to="/orders">orders page</Link> once a
            link can be issued.
          </p>
        </div>
      )}

      {response.type === "APPROVAL_REQUIRED" && response.approval_token && (
        <div className="rounded-lg border border-caution/40 bg-caution/5 p-3">
          <p className="mono break-all text-ink-300">{response.approval_token}</p>
          <button className="btn-primary mt-2.5 text-xs" onClick={() => onApprove(response.approval_token!)}>
            Approve as human and continue
          </button>
        </div>
      )}

      {response.top_choice && (
        <div className="flex items-center justify-between gap-3 rounded-lg border border-ink-700 bg-ink-850 px-3 py-2.5">
          <div className="min-w-0">
            <p className="label">{alreadyOrdered ? "Ordered" : "Top recommendation"}</p>
            <p className="mt-1 truncate text-sm font-medium">{response.top_choice.name}</p>
            <p className="mono text-ink-400">{response.top_choice.id}</p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <span className="text-sm tabular-nums">{money(response.top_choice.price)}</span>
            {/* Buying it again from the confirmation of that very purchase reads as a mistake. */}
            {!alreadyOrdered && (
              <button className="btn-ghost text-xs" onClick={() => onBuy(response.top_choice!.id)}>
                Buy
              </button>
            )}
          </div>
        </div>
      )}

      {alternatives.length > 0 && (
        <div className="rounded-lg border border-ink-700 bg-ink-850 px-3 py-2.5">
          <p className="label">Also in stock</p>
          <ul className="mt-2 space-y-1.5">
            {alternatives.slice(0, 3).map((p) => (
              <li key={p.id} className="flex items-center justify-between gap-3">
                <span className="min-w-0 truncate text-xs text-ink-300">{p.name}</span>
                <span className="flex shrink-0 items-center gap-2">
                  <span className="text-xs tabular-nums">{money(p.price)}</span>
                  <button className="text-xs text-flow hover:underline" onClick={() => onBuy(p.id)}>
                    Buy
                  </button>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {response.upsell_bundle && (
        <div className="rounded-lg border border-flow/30 bg-flow/5 px-3 py-2.5">
          <p className="text-xs font-medium text-flow">
            Frequently bought together: {response.upsell_bundle.complementary_product_name}
          </p>
          <p className="mt-1 text-xs text-ink-300">
            {response.upsell_bundle.primary_product_name} + {response.upsell_bundle.complementary_product_name} for{" "}
            {money(response.upsell_bundle.discounted_bundle_price)} — saves{" "}
            {money(response.upsell_bundle.savings_amount)}
          </p>
          {/*
            Buying the companion on its own charges full price and never applies the
            bundle discount advertised right above it. The offer is on the pair, so the
            button re-issues the *primary* purchase with the bundle attached.
          */}
          <button
            className="mt-2 text-xs text-flow hover:underline"
            onClick={() =>
              onBuy(response.upsell_bundle!.primary_product_id, {
                bundle: true,
                label: `Buy ${response.upsell_bundle!.primary_product_name} together with ${response.upsell_bundle!.complementary_product_name} as a bundle.`,
              })
            }
          >
            Add both for {money(response.upsell_bundle.discounted_bundle_price)} →
          </button>
        </div>
      )}
    </>
  );
}

function Inspector({ response }: { response: ChatResponse | null }) {
  if (!response) {
    return (
      <Panel title="Decision inspector">
        <p className="px-5 py-8 text-center text-xs leading-relaxed text-ink-400">
          Send a message to see the agent trace and the deterministic policy evaluation behind each decision.
        </p>
      </Panel>
    );
  }

  const order = response.order as Record<string, unknown> | undefined;

  return (
    <div className="space-y-4">
      {response.reasoning_steps && response.reasoning_steps.length > 0 && (
        <Panel title="Agent trace">
          <div className="px-5 py-4">
            <ReasoningTrace steps={response.reasoning_steps} />
          </div>
        </Panel>
      )}

      {response.policy_evaluation && <PolicyPanel evaluation={response.policy_evaluation} />}

      {order && (
        <Panel title="Order">
          <div className="divide-y divide-ink-800 px-5 py-2">
            <Row k="Order ID" v={<span className="mono">{String(order.order_id)}</span>} />
            <Row k="Amount" v={money(Number(order.amount))} />
            <Row k="State" v={<Badge tone={toneForState(String(order.state))}>{String(order.state)}</Badge>} />
          </div>

          <div className="border-t border-ink-800 p-4">
            {response.payment_link ? (
              <PaymentLink url={response.payment_link} amount={Number(order.amount)} compact />
            ) : (
              <p className="text-xs leading-relaxed text-ink-400">
                {/*
                  This used to blame simulator mode and missing credentials unconditionally,
                  which is wrong whenever the gateway refused for some other reason -- a
                  quota, a bad key, an outage. Report what actually came back.
                */}
                {response.payment_link_error ??
                  "No payment link was issued for this order. Razorpay only returns one when provider_mode is razorpay and both API credentials are configured; in simulator mode, pay via the cart page instead."}
              </p>
            )}
          </div>
        </Panel>
      )}

      {response.cart && (
        <Panel title="Cart">
          <div className="divide-y divide-ink-800 px-5 py-2">
            <Row k="Subtotal" v={money(response.cart.subtotal_amount)} />
            <Row k="Discount" v={`- ${money(response.cart.discount_amount)}`} />
            <Row k="Total" v={<strong>{money(response.cart.total_amount)}</strong>} />
          </div>
        </Panel>
      )}

      <Panel title="Raw response">
        <div className="p-4">
          <Json data={response} />
        </div>
      </Panel>
    </div>
  );
}
