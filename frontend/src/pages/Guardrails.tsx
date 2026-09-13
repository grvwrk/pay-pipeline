import { useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import { money } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import type { GuardrailConfig } from "../lib/types";
import { PageHeader } from "../components/PageHeader";
import { Badge, ErrorNote, Panel, Spinner, Stat } from "../components/ui";

export default function Guardrails() {
  const { data, error, loading, reload } = useAsync(() => api.getGuardrails(), []);
  const [draft, setDraft] = useState<GuardrailConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [outcome, setOutcome] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    if (data) setDraft(structuredClone(data));
  }, [data]);

  const dirty = draft !== null && data !== null && JSON.stringify(draft) !== JSON.stringify(data);

  async function save() {
    if (!draft) return;
    setSaving(true);
    setOutcome(null);
    try {
      await api.updateGuardrails(draft);
      setOutcome({ ok: true, text: "Policy ceilings updated. New checkouts are evaluated against these values." });
      reload();
    } catch (err) {
      setOutcome({ ok: false, text: err instanceof ApiError ? err.message : String(err) });
    } finally {
      setSaving(false);
    }
  }

  function patch(update: Partial<GuardrailConfig>) {
    setDraft((d) => (d ? { ...d, ...update } : d));
  }

  return (
    <div>
      <PageHeader
        title="Guardrails"
        subtitle="The trusted layer. Plain rule-based code, independent of any model — this is what actually decides whether money moves."
        actions={
          <>
            {dirty && <Badge tone="warn">unsaved</Badge>}
            <button className="btn-ghost" onClick={() => data && setDraft(structuredClone(data))} disabled={!dirty}>
              Reset
            </button>
            <button className="btn-primary" onClick={save} disabled={!dirty || saving}>
              {saving ? "Saving…" : "Save policy"}
            </button>
          </>
        }
      />

      {loading && <div className="p-8"><Spinner label="Loading policy…" /></div>}
      {error && <ErrorNote error={error} onRetry={reload} />}

      {draft && (
        <div className="space-y-6 p-8">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Stat label="Per-transaction ceiling" value={money(draft.max_transaction_amount_inr)} hint="Hard deny above this" tone="bad" />
            <Stat label="Approval threshold" value={money(draft.approval_threshold_inr)} hint="Gate to human above this" tone="warn" />
            <Stat label="Cumulative spend cap" value={money(draft.max_cumulative_spend_inr)} hint="Across the session" />
            <Stat label="Max item quantity" value={draft.max_item_quantity} hint="Per line item" />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Panel title="Limits">
              <div className="space-y-4 px-5 py-5">
                <NumberField
                  label="Max transaction amount (INR)"
                  help="Any cart above this is denied outright with DENIED_SPEND_LIMIT."
                  value={draft.max_transaction_amount_inr}
                  onChange={(v) => patch({ max_transaction_amount_inr: v })}
                />
                <NumberField
                  label="Approval threshold (INR)"
                  help="Carts above this stop at PENDING_APPROVAL and issue a token."
                  value={draft.approval_threshold_inr}
                  onChange={(v) => patch({ approval_threshold_inr: v })}
                />
                <NumberField
                  label="Max cumulative spend (INR)"
                  help="Running total the agent may commit before being cut off."
                  value={draft.max_cumulative_spend_inr}
                  onChange={(v) => patch({ max_cumulative_spend_inr: v })}
                />
                <NumberField
                  label="Max item quantity"
                  help="Upper bound on units per line, blocking runaway quantities."
                  value={draft.max_item_quantity}
                  step={1}
                  onChange={(v) => patch({ max_item_quantity: Math.round(v) })}
                />
                <div>
                  <label className="label" htmlFor="cur">Allowed currency</label>
                  <input
                    id="cur"
                    className="field mono mt-1.5"
                    value={draft.allowed_currency}
                    onChange={(e) => patch({ allowed_currency: e.target.value.toUpperCase() })}
                  />
                </div>
              </div>
            </Panel>

            <div className="space-y-6">
              <ListField
                title="Allowed categories"
                help="A cart containing any category outside this list is denied as unauthorized."
                values={draft.allowed_categories}
                onChange={(allowed_categories) => patch({ allowed_categories })}
                placeholder="mechanical_keyboards"
              />
              <ListField
                title="Merchant whitelist"
                help="Only these merchant IDs can be transacted with."
                values={draft.merchant_whitelist}
                onChange={(merchant_whitelist) => patch({ merchant_whitelist })}
                placeholder="merch_pay_pipeline_01"
              />
            </div>
          </div>

          {outcome && (
            <p className={`rounded-lg border px-4 py-3 text-sm ${
              outcome.ok
                ? "border-signal/40 bg-signal/10 text-signal"
                : "border-halt/40 bg-halt/10 text-halt"
            }`}>
              {outcome.text}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function NumberField({ label, help, value, onChange, step = 100 }: {
  label: string; help: string; value: number; onChange: (v: number) => void; step?: number;
}) {
  const id = label.replace(/\W+/g, "-").toLowerCase();
  return (
    <div>
      <label className="label" htmlFor={id}>{label}</label>
      <input
        id={id}
        className="field mt-1.5 tabular-nums"
        type="number"
        min={0}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <p className="mt-1.5 text-xs leading-relaxed text-ink-400">{help}</p>
    </div>
  );
}

function ListField({ title, help, values, onChange, placeholder }: {
  title: string; help: string; values: string[]; onChange: (next: string[]) => void; placeholder: string;
}) {
  const [entry, setEntry] = useState("");

  function add(e: React.FormEvent) {
    e.preventDefault();
    const v = entry.trim();
    if (!v || values.includes(v)) return;
    onChange([...values, v]);
    setEntry("");
  }

  return (
    <Panel title={title}>
      <div className="px-5 py-5">
        <p className="text-xs leading-relaxed text-ink-400">{help}</p>
        <ul className="mt-3 flex flex-wrap gap-2">
          {values.map((v) => (
            <li key={v}>
              <button
                className="mono group inline-flex items-center gap-1.5 rounded-md border border-ink-700 px-2 py-1 text-ink-300 hover:border-halt/50 hover:text-halt"
                onClick={() => onChange(values.filter((x) => x !== v))}
                title={`Remove ${v}`}
              >
                {v}
                <span className="text-ink-400 group-hover:text-halt">×</span>
              </button>
            </li>
          ))}
          {values.length === 0 && <li className="text-xs text-ink-400">Empty — nothing is permitted.</li>}
        </ul>
        <form className="mt-3 flex gap-2" onSubmit={add}>
          <input className="field mono" placeholder={placeholder} value={entry} onChange={(e) => setEntry(e.target.value)} />
          <button className="btn-ghost" type="submit" disabled={!entry.trim()}>Add</button>
        </form>
      </div>
    </Panel>
  );
}
