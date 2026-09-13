import { useState } from "react";
import { api, ApiError } from "../lib/api";
import type { ReasoningStep } from "../lib/types";
import { PageHeader } from "../components/PageHeader";
import { ReasoningTrace } from "../components/ReasoningTrace";
import { Badge, Json, Panel, Spinner } from "../components/ui";

/** Mirrors the scenario IDs handled by POST /api/v1/scenarios/run/{scenario_id}. */
const SCENARIOS = [
  {
    id: "discovery_and_reasoning",
    name: "Discovery and reasoning",
    blurb: "Natural-language catalog search under a ₹5,000 budget; the catalog agent reasons over specs.",
    expect: "CATALOG_DISCOVERY",
    tone: "info" as const,
  },
  {
    id: "upsell_basket_growth",
    name: "Upsell basket growth",
    blurb: "Pairs a keyboard with a complementary wrist rest and applies the bundle discount, lifting AOV under the ceiling.",
    expect: "ORDER_CREATED",
    tone: "good" as const,
  },
  {
    id: "graceful_failure_spend_limit",
    name: "Spend-limit denial",
    blurb: "Attempts a ₹7,999 purchase against the ₹5,000 per-transaction ceiling.",
    expect: "DENIED_SPEND_LIMIT",
    tone: "bad" as const,
  },
  {
    id: "gated_approval_flow",
    name: "Gated human approval",
    blurb: "A ₹4,499 purchase crosses the ₹3,000 gate, so checkout stops at PENDING_APPROVAL with a token.",
    expect: "GATED_APPROVAL_REQUIRED",
    tone: "warn" as const,
  },
  {
    id: "duplicate_request_idempotency",
    name: "Idempotency replay",
    blurb: "Fires the same checkout twice with one idempotency key to prove double-spend protection.",
    expect: "DENIED_IDEMPOTENCY_COLLISION",
    tone: "warn" as const,
  },
  {
    id: "valid_refund_flow",
    name: "Bounded refund",
    blurb: "Captures a test payment, then refunds part of it within the captured balance.",
    expect: "REFUND_PROCESSED",
    tone: "info" as const,
  },
];

export default function Scenarios() {
  const [running, setRunning] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, unknown>>({});
  const [failures, setFailures] = useState<Record<string, string>>({});

  async function run(id: string) {
    setRunning(id);
    setFailures((f) => ({ ...f, [id]: "" }));
    try {
      const res = await api.runScenario(id);
      setResults((r) => ({ ...r, [id]: res }));
    } catch (err) {
      setFailures((f) => ({ ...f, [id]: err instanceof ApiError ? err.message : String(err) }));
    } finally {
      setRunning(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="Demo scenarios"
        subtitle="Preset end-to-end runs that exercise each edge of the policy engine: growth, denial, gating, replay and refund."
      />

      <div className="grid gap-5 p-8 lg:grid-cols-2">
        {SCENARIOS.map((s) => {
          const result = results[s.id] as Record<string, unknown> | undefined;
          const failure = failures[s.id];
          const trace = extractTrace(result);

          return (
            <Panel
              key={s.id}
              title={s.name}
              actions={<Badge tone={s.tone}>{s.expect}</Badge>}
            >
              <div className="space-y-4 px-5 py-4">
                <p className="text-xs leading-relaxed text-ink-400">{s.blurb}</p>

                <div className="flex items-center gap-3">
                  <button className="btn-primary text-xs" onClick={() => run(s.id)} disabled={running !== null}>
                    {running === s.id ? "Running…" : result ? "Run again" : "Run scenario"}
                  </button>
                  {running === s.id && <Spinner label="Executing workflow…" />}
                </div>

                {failure && (
                  <p className="rounded-lg border border-halt/40 bg-halt/10 px-3 py-2 text-xs text-halt">
                    {failure}
                  </p>
                )}

                {result && (
                  <>
                    {typeof result.description === "string" && (
                      <p className="rounded-lg border border-ink-700 bg-ink-850 px-3 py-2.5 text-xs leading-relaxed text-ink-300">
                        {result.description}
                      </p>
                    )}

                    {trace.length > 0 && (
                      <details className="group">
                        <summary className="cursor-pointer text-xs text-flow hover:underline">
                          Agent trace ({trace.length} steps)
                        </summary>
                        <div className="mt-3"><ReasoningTrace steps={trace} /></div>
                      </details>
                    )}

                    <details>
                      <summary className="cursor-pointer text-xs text-flow hover:underline">
                        Raw result
                      </summary>
                      <div className="mt-3"><Json data={result} /></div>
                    </details>
                  </>
                )}
              </div>
            </Panel>
          );
        })}
      </div>
    </div>
  );
}

/** Scenario payloads vary: some nest the workflow result, some return it flat. */
function extractTrace(result: Record<string, unknown> | undefined): ReasoningStep[] {
  if (!result) return [];
  const nested = result.workflow_result as Record<string, unknown> | undefined;
  const steps = (nested?.reasoning_steps ?? result.reasoning_steps) as ReasoningStep[] | undefined;
  return Array.isArray(steps) ? steps : [];
}
