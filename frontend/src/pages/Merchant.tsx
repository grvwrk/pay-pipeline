import { useState } from "react";
import { api, ApiError } from "../lib/api";
import { money, pct, ratio } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import type { Campaign } from "../lib/types";
import { PageHeader } from "../components/PageHeader";
import { Badge, Empty, ErrorNote, Panel, Spinner, Stat, toneForState } from "../components/ui";

export default function Merchant() {
  const { data, error, loading, reload } = useAsync(() => api.analytics(), []);
  const [composing, setComposing] = useState(false);

  return (
    <div>
      <PageHeader
        title="Merchant growth"
        subtitle="KPIs computed from captured orders only. Campaigns carry a bounded budget the agent cannot exceed."
        actions={
          <>
            <button className="btn-ghost" onClick={reload}>Refresh</button>
            <button className="btn-primary" onClick={() => setComposing((v) => !v)}>
              {composing ? "Close" : "New campaign"}
            </button>
          </>
        }
      />

      <div className="space-y-6 p-8">
        {composing && <CampaignForm onCreated={() => { setComposing(false); reload(); }} />}

        {loading && <Spinner label="Computing KPIs…" />}
        {error && (
          <Panel title="Analytics unavailable">
            <ErrorNote error={error} onRetry={reload} />
            <p className="px-5 pb-5 text-xs leading-relaxed text-ink-400">
              Analytics require at least one captured order and a configured baseline AOV. Run a checkout and let a
              payment webhook land, then refresh.
            </p>
          </Panel>
        )}

        {data && (
          <>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <Stat label="Total revenue" value={money(data.kpis.total_revenue_inr)} hint={`${data.kpis.total_orders_processed} captured orders`} />
              <Stat
                label="Agent AOV"
                value={money(data.kpis.average_order_value_inr)}
                hint={`vs ${money(data.kpis.baseline_aov_without_agent_inr)} baseline`}
                tone={data.kpis.aov_growth_percentage >= 0 ? "good" : "bad"}
              />
              <Stat
                label="AOV lift"
                value={pct(data.kpis.aov_growth_percentage)}
                hint="Attributable to upsell bundling"
                tone={data.kpis.aov_growth_percentage >= 0 ? "good" : "bad"}
              />
              <Stat
                label="Guardrail interceptions"
                value={data.kpis.guardrail_interceptions_count}
                hint="Denied by deterministic policy"
                tone={data.kpis.guardrail_interceptions_count > 0 ? "warn" : "neutral"}
              />
              <Stat label="Upsell conversion" value={ratio(data.kpis.upsell_conversion_rate)} hint="Orders that took a bundle" />
              <Stat label="Cart abandonment" value={ratio(data.kpis.cart_abandonment_rate)} hint="Carts never converted to orders" />
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <Panel title={`Segments (${data.segments.length})`}>
                {data.segments.length === 0 ? (
                  <Empty title="No segments configured" hint="Segments live in the merchant campaigns database." />
                ) : (
                  <ul className="divide-y divide-ink-800">
                    {data.segments.map((s) => (
                      <li key={s.id} className="px-5 py-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="text-sm font-medium">{s.name}</p>
                            <p className="mt-1 text-xs leading-relaxed text-ink-400">{s.description}</p>
                          </div>
                          <span className="mono shrink-0 text-ink-300">{s.customer_count} users</span>
                        </div>
                        <div className="mt-3 flex flex-wrap items-center gap-1.5">
                          {s.affinity_categories.map((c) => (
                            <Badge key={c}>{c.replace(/_/g, " ")}</Badge>
                          ))}
                          <Badge tone="info">AOV {money(s.average_order_value)}</Badge>
                          <Badge tone="warn">propensity {ratio(s.upsell_propensity_score)}</Badge>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </Panel>

              <Panel title={`Campaigns (${data.campaigns.length})`}>
                {data.campaigns.length === 0 ? (
                  <Empty title="No campaigns launched" hint="Create one to attach a bounded bundle offer to a segment." />
                ) : (
                  <ul className="divide-y divide-ink-800">
                    {data.campaigns.map((c) => {
                      const used = c.max_budget_inr > 0 ? Math.min(1, c.spent_budget_inr / c.max_budget_inr) : 0;
                      return (
                        <li key={c.id} className="px-5 py-4">
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <p className="text-sm font-medium">{c.title}</p>
                              <p className="mono mt-1 text-ink-400">{c.target_segment}</p>
                            </div>
                            <Badge tone={toneForState(c.status)}>{c.status}</Badge>
                          </div>
                          <p className="mt-2 text-xs leading-relaxed text-ink-400">
                            {c.bundle_offer} · {c.discount_percentage}% off · trigger: {c.trigger_condition}
                          </p>
                          <div className="mt-3">
                            <div className="h-1.5 overflow-hidden rounded-full bg-ink-800">
                              <div className="h-full rounded-full bg-flow" style={{ width: `${used * 100}%` }} />
                            </div>
                            <div className="mt-1.5 flex justify-between text-xs text-ink-400">
                              <span>{money(c.spent_budget_inr)} of {money(c.max_budget_inr)} budget</span>
                              <span>{c.conversions} conv · {money(c.revenue_generated_inr)}</span>
                            </div>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </Panel>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

const BLANK: Campaign = {
  id: "",
  title: "",
  target_segment: "",
  trigger_condition: "cart_contains_keyboard",
  bundle_offer: "",
  discount_percentage: 5,
  max_budget_inr: 10000,
  spent_budget_inr: 0,
  conversions: 0,
  revenue_generated_inr: 0,
  status: "ACTIVE",
};

function CampaignForm({ onCreated }: { onCreated: () => void }) {
  const [draft, setDraft] = useState<Campaign>({ ...BLANK, id: `camp_${crypto.randomUUID().slice(0, 8)}` });
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setProblem(null);
    try {
      await api.createCampaign(draft);
      onCreated();
    } catch (err) {
      setProblem(err instanceof ApiError ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const set = (patch: Partial<Campaign>) => setDraft((d) => ({ ...d, ...patch }));

  return (
    <Panel title="Launch campaign">
      <form className="grid gap-4 px-5 py-5 sm:grid-cols-2" onSubmit={submit}>
        <Field label="Campaign ID" value={draft.id} onChange={(v) => set({ id: v })} mono required />
        <Field label="Title" value={draft.title} onChange={(v) => set({ title: v })} required />
        <Field label="Target segment" value={draft.target_segment} onChange={(v) => set({ target_segment: v })} mono required />
        <Field label="Trigger condition" value={draft.trigger_condition} onChange={(v) => set({ trigger_condition: v })} mono />
        <Field label="Bundle offer" value={draft.bundle_offer} onChange={(v) => set({ bundle_offer: v })} className="sm:col-span-2" required />
        <Field label="Discount %" type="number" value={String(draft.discount_percentage)} onChange={(v) => set({ discount_percentage: Number(v) })} />
        <Field label="Max budget (INR)" type="number" value={String(draft.max_budget_inr)} onChange={(v) => set({ max_budget_inr: Number(v) })} />

        <div className="flex items-center gap-3 sm:col-span-2">
          <button className="btn-primary" type="submit" disabled={busy}>
            {busy ? "Launching…" : "Launch campaign"}
          </button>
          {problem && <span className="text-xs text-halt">{problem}</span>}
        </div>
      </form>
    </Panel>
  );
}

function Field({ label, value, onChange, type = "text", mono = false, required = false, className = "" }: {
  label: string; value: string; onChange: (v: string) => void;
  type?: string; mono?: boolean; required?: boolean; className?: string;
}) {
  const id = label.replace(/\W+/g, "-").toLowerCase();
  return (
    <div className={className}>
      <label className="label" htmlFor={id}>{label}</label>
      <input
        id={id}
        type={type}
        required={required}
        className={`field mt-1.5 ${mono ? "mono" : ""}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
