import React, { useState } from "react";
import { api } from "../services/api";
import { PlayCircle, ShieldAlert, Sparkles, CheckCircle2, AlertTriangle, ArrowRight, Bot, X, CreditCard } from "lucide-react";

interface ScenariosModalProps {
  isOpen: boolean;
  onClose: () => void;
  onScenarioExecuted: () => void;
}

export const ScenariosModal: React.FC<ScenariosModalProps> = ({
  isOpen,
  onClose,
  onScenarioExecuted
}) => {
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const scenarios = [
    {
      id: "discovery_and_reasoning",
      title: "1. Discovery & Reasoning",
      subtitle: "Natural Language Search under ₹5,000",
      description: "Catalog Agent interprets natural language intent, searches structured SKUs, and reasons over tactile mechanical keyboard specs.",
      tag: "Intelligence",
      color: "from-blue-500 to-indigo-500"
    },
    {
      id: "upsell_basket_growth",
      title: "2. Revenue Growth & Upsell",
      subtitle: "Dynamic Wrist Rest Bundle (₹4,998)",
      description: "Upsell Agent pairs Keychron K2 with Solid Walnut Wrist Rest (₹499) + 5% bundle discount, increasing Merchant AOV while staying within ₹5,000 spend limit.",
      tag: "Revenue Growth",
      color: "from-purple-500 to-indigo-500"
    },
    {
      id: "graceful_failure_spend_limit",
      title: "3. Bounded Guardrail Graceful Failure",
      subtitle: "Deterministic Denial of ₹7,999 Order",
      description: "User attempts to buy ₹7,999 aluminium keyboard with ₹5,000 limit. Guardrail Engine intercepts and blocks execution deterministically.",
      tag: "Safety & Boundaries",
      color: "from-red-500 to-rose-500"
    },
    {
      id: "gated_approval_flow",
      title: "4. Gated Human Approval Flow",
      subtitle: "Orders > ₹3,000 require 2FA token",
      description: "Order transitions to PENDING_APPROVAL requiring explicit human confirmation before money moves.",
      tag: "Human-in-the-Loop",
      color: "from-amber-500 to-orange-500"
    },
    {
      id: "graceful_failure_payment_decline",
      title: "5. Bank Decline & Webhook Recovery",
      subtitle: "Authoritative Payment Failure State",
      description: "Razorpay bank decline handled gracefully. State machine marks PAYMENT_FAILED without hallucinatory success.",
      tag: "Payment Rails",
      color: "from-orange-500 to-red-500"
    },
    {
      id: "acp_machine_buyer_transaction",
      title: "6. Agentic Commerce Protocol (ACP)",
      subtitle: "External AI Buyer Transacting Machine-to-Machine",
      description: "External AI Buyer directly discovers catalog, quotes bundle, and checks out ScreenBar LED over ACP machine endpoints.",
      tag: "M2M Commerce",
      color: "from-cyan-500 to-teal-500"
    }
  ];

  const handleRun = async (scenarioId: string) => {
    setSelectedScenario(scenarioId);
    setLoading(true);
    try {
      const res = await api.runScenario(scenarioId);
      setResult(res);
      onScenarioExecuted();
    } catch (e: any) {
      setResult({ error: e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 max-w-4xl w-full rounded-2xl p-6 shadow-2xl relative max-h-[90vh] flex flex-col">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 flex items-center justify-center text-slate-950 shadow-lg shadow-amber-500/20">
            <PlayCircle className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">1-Click Evaluation Scenarios</h3>
            <p className="text-xs text-slate-400">
              Interactive end-to-end scenarios demonstrating agentic intelligence, revenue growth, deterministic safety, and graceful failure recovery.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 overflow-y-auto pr-1 mb-4 flex-1">
          {scenarios.map((sc) => (
            <div
              key={sc.id}
              onClick={() => handleRun(sc.id)}
              className={`p-4 rounded-xl border cursor-pointer transition flex flex-col justify-between ${
                selectedScenario === sc.id
                  ? "bg-indigo-950/50 border-indigo-500 shadow-lg shadow-indigo-500/15"
                  : "bg-slate-950/80 border-slate-800 hover:border-slate-700"
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-white">{sc.title}</span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                    {sc.tag}
                  </span>
                </div>
                <div className="text-xs font-semibold text-indigo-300 mb-1">{sc.subtitle}</div>
                <p className="text-[11px] text-slate-400 leading-relaxed">{sc.description}</p>
              </div>

              <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-indigo-400 font-semibold">
                <span>Click to Execute Live</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </div>
            </div>
          ))}
        </div>

        {/* Execution Output */}
        {selectedScenario && (
          <div className="bg-slate-950 rounded-xl border border-slate-800 p-4 font-mono text-xs max-h-48 overflow-y-auto">
            <div className="flex justify-between items-center pb-2 mb-2 border-b border-slate-800 text-slate-400">
              <span>Scenario Execution Result</span>
              <span>{loading ? "Running workflow..." : "Completed"}</span>
            </div>
            {loading ? (
              <div className="text-amber-400 py-2 animate-pulse">Orchestrating LlamaIndex Workflow & Razorpay test rails...</div>
            ) : (
              <pre className="text-emerald-400 whitespace-pre-wrap">{JSON.stringify(result, null, 2)}</pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
