import type { ReasoningStep } from "../lib/types";

/** The agent's step-by-step trace: which agent acted, why, and what tool it called. */
export function ReasoningTrace({ steps }: { steps: ReasoningStep[] }) {
  if (steps.length === 0) return null;
  return (
    <ol className="relative space-y-3 border-l border-ink-700 pl-5">
      {steps.map((step, i) => (
        <li key={`${step.agent_name}-${i}`} className="relative">
          <span className="absolute -left-[23px] top-1.5 size-1.5 rounded-full bg-flow" />
          <div className="flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
            <span className="text-xs font-semibold text-ink-100">{step.agent_name}</span>
            <span className="mono rounded border border-ink-700 px-1.5 py-0.5 text-ink-400">
              {step.action}
            </span>
            {step.latency_ms > 0 && (
              <span className="mono text-ink-400">{step.latency_ms.toFixed(0)}ms</span>
            )}
          </div>
          <p className="mt-1 text-xs leading-relaxed text-ink-300">{step.thought}</p>
          {step.tool_called && (
            <p className="mono mt-1 text-ink-400">tool: {step.tool_called}()</p>
          )}
          {step.result_summary && (
            <p className="mt-1 text-xs text-ink-400">{step.result_summary}</p>
          )}
        </li>
      ))}
    </ol>
  );
}
