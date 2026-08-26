import React, { useState } from "react";
import { GuardrailConfig } from "../../types";
import { ShieldCheck, Lock, Sliders, AlertCircle, Save } from "lucide-react";

interface PolicyControlsProps {
  config: GuardrailConfig;
  onSaveConfig: (newConfig: GuardrailConfig) => void;
}

export const PolicyControls: React.FC<PolicyControlsProps> = ({ config, onSaveConfig }) => {
  const [maxTxn, setMaxTxn] = useState(config.max_transaction_amount_inr);
  const [cumulative, setCumulative] = useState(config.max_cumulative_spend_inr);
  const [approvalThreshold, setApprovalThreshold] = useState(config.approval_threshold_inr);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    onSaveConfig({
      ...config,
      max_transaction_amount_inr: maxTxn,
      max_cumulative_spend_inr: cumulative,
      approval_threshold_inr: approvalThreshold
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl mb-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-white">Deterministic Guardrails & Spending Boundaries</h3>
            <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[10px] uppercase font-bold">
              Active Enforcement
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Strict, model-independent financial bounds. The LLM cannot override or negotiate these rules.
          </p>
        </div>

        <button
          onClick={handleSave}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-600/20 transition"
        >
          <Save className="h-4 w-4" />
          {saved ? "Saved & Applied!" : "Save Policy"}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Max Single Txn Limit */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs font-semibold text-slate-400">Max Single Txn Limit</span>
            <span className="text-sm font-bold text-emerald-400">₹{maxTxn.toLocaleString("en-IN")}</span>
          </div>
          <input
            type="range"
            min="1000"
            max="15000"
            step="500"
            value={maxTxn}
            onChange={(e) => setMaxTxn(Number(e.target.value))}
            className="w-full accent-emerald-500 cursor-pointer"
          />
          <p className="text-[11px] text-slate-500 mt-2">
            Hard upper limit per order. Orders exceeding this are immediately denied with <code className="text-red-400">DENIED_SPEND_LIMIT</code>.
          </p>
        </div>

        {/* Gated Approval Threshold */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs font-semibold text-slate-400">Gated Approval Threshold</span>
            <span className="text-sm font-bold text-amber-400">₹{approvalThreshold.toLocaleString("en-IN")}</span>
          </div>
          <input
            type="range"
            min="1000"
            max="8000"
            step="500"
            value={approvalThreshold}
            onChange={(e) => setApprovalThreshold(Number(e.target.value))}
            className="w-full accent-amber-500 cursor-pointer"
          />
          <p className="text-[11px] text-slate-500 mt-2">
            Orders above this threshold transition to <code className="text-amber-400">PENDING_APPROVAL</code> requiring 2FA human token.
          </p>
        </div>

        {/* Cumulative Session Spend */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs font-semibold text-slate-400">Cumulative Session Cap</span>
            <span className="text-sm font-bold text-indigo-400">₹{cumulative.toLocaleString("en-IN")}</span>
          </div>
          <input
            type="range"
            min="5000"
            max="30000"
            step="1000"
            value={cumulative}
            onChange={(e) => setCumulative(Number(e.target.value))}
            className="w-full accent-indigo-500 cursor-pointer"
          />
          <p className="text-[11px] text-slate-500 mt-2">
            Max total money an agent can spend across multiple sessions. Prevents runaway repetitive drain attacks.
          </p>
        </div>
      </div>
    </div>
  );
};
