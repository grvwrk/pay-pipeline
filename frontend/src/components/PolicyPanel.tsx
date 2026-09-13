import { money } from "../lib/format";
import type { PolicyEvaluation } from "../lib/types";
import { Badge, toneForState } from "./ui";

/**
 * Renders a deterministic policy evaluation: the decision, the amount it was
 * bounded against, and every rule the engine actually ran.
 */
export function PolicyPanel({ evaluation }: { evaluation: PolicyEvaluation }) {
  return (
    <div className="rounded-lg border border-ink-700 bg-ink-850">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ink-700 px-4 py-3">
        <div className="flex items-center gap-2.5">
          <span className="label">Policy engine</span>
          <Badge tone={toneForState(evaluation.decision_code)}>{evaluation.decision_code}</Badge>
        </div>
        <span className="mono text-ink-400">
          {money(evaluation.bounded_amount)} / {money(evaluation.max_allowed_amount)} ceiling
        </span>
      </div>

      <p className="px-4 py-3 text-sm leading-relaxed text-ink-300">{evaluation.reason}</p>

      {evaluation.rule_evaluations.length > 0 && (
        <ul className="divide-y divide-ink-700 border-t border-ink-700">
          {evaluation.rule_evaluations.map((rule) => (
            <li key={rule.rule_name} className="flex items-start gap-3 px-4 py-2.5">
              <span className={`mt-0.5 select-none text-xs ${rule.passed ? "text-signal" : "text-halt"}`}>
                {rule.passed ? "PASS" : "FAIL"}
              </span>
              <div className="min-w-0 flex-1">
                <p className="mono text-ink-100">{rule.rule_name}</p>
                <p className="mt-0.5 text-xs leading-relaxed text-ink-400">{rule.description}</p>
              </div>
              {rule.threshold_value != null && (
                <span className="mono shrink-0 text-ink-400">
                  {String(rule.actual_value)} ≤ {String(rule.threshold_value)}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
