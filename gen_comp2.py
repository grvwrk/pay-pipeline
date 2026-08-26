import os

def write(filepath, content):
    d = os.path.dirname(filepath)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Wrote: {filepath}")

# 1. RevenueKPIs
write('frontend/src/components/MerchantDashboard/RevenueKPIs.tsx', '''import React from "react";
import { MerchantKPIs } from "../../types";
import { TrendingUp, ShoppingBag, ShieldCheck, Percent, ArrowUpRight } from "lucide-react";

interface RevenueKPIsProps {
  kpis: MerchantKPIs;
}

export const RevenueKPIs: React.FC<RevenueKPIsProps> = ({ kpis }) => {
  const cards = [
    {
      title: "Average Order Value (AOV)",
      value: `₹${kpis.average_order_value_inr.toLocaleString("en-IN")}`,
      change: `+${kpis.aov_growth_percentage}% vs baseline`,
      sub: `Baseline without AI agent: ₹${kpis.baseline_aov_without_agent_inr.toLocaleString("en-IN")}`,
      icon: TrendingUp,
      color: "text-emerald-400",
      bg: "bg-emerald-500/10 border-emerald-500/30"
    },
    {
      title: "Upsell Conversion Rate",
      value: `${(kpis.upsell_conversion_rate * 100).toFixed(0)}%`,
      change: "+18.4% this month",
      sub: "Buyers adding complementary dynamic bundles",
      icon: Percent,
      color: "text-indigo-400",
      bg: "bg-indigo-500/10 border-indigo-500/30"
    },
    {
      title: "Cart Abandonment Rate",
      value: `${(kpis.cart_abandonment_rate * 100).toFixed(0)}%`,
      change: "-50% drop via Agentic Flow",
      sub: "Industry average without agent: 68%",
      icon: ShoppingBag,
      color: "text-cyan-400",
      bg: "bg-cyan-500/10 border-cyan-500/30"
    },
    {
      title: "Guardrail Interceptions",
      value: `${kpis.guardrail_interceptions_count}`,
      change: "100% policy compliance",
      sub: "Oversized & unsafe money actions intercepted",
      icon: ShieldCheck,
      color: "text-amber-400",
      bg: "bg-amber-500/10 border-amber-500/30"
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className="p-5 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col justify-between shadow-lg"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  {card.title}
                </span>
                <div className={`h-8 w-8 rounded-lg flex items-center justify-center border ${card.bg} ${card.color}`}>
                  <Icon className="h-4 w-4" />
                </div>
              </div>

              <div className="text-2xl font-bold text-white mb-1">
                {card.value}
              </div>

              <div className="flex items-center gap-1 text-xs font-semibold text-emerald-400 mb-2">
                <ArrowUpRight className="h-3.5 w-3.5" />
                <span>{card.change}</span>
              </div>
            </div>

            <div className="text-[11px] text-slate-500 pt-2 border-t border-slate-800/80">
              {card.sub}
            </div>
          </div>
        );
      })}
    </div>
  );
};
''')

# 2. CampaignOrchestrator
write('frontend/src/components/MerchantDashboard/CampaignOrchestrator.tsx', '''import React, { useState } from "react";
import { Campaign, CustomerSegment } from "../../types";
import { Sparkles, Plus, Target, CheckCircle2, Play, Users } from "lucide-react";

interface CampaignOrchestratorProps {
  campaigns: Campaign[];
  segments: CustomerSegment[];
  onCreateCampaign: (campaign: Partial<Campaign>) => void;
}

export const CampaignOrchestrator: React.FC<CampaignOrchestratorProps> = ({
  campaigns,
  segments,
  onCreateCampaign
}) => {
  const [showModal, setShowModal] = useState(false);
  const [title, setTitle] = useState("");
  const [targetSegment, setTargetSegment] = useState(segments[0]?.id || "");
  const [bundleOffer, setBundleOffer] = useState("");
  const [discount, setDiscount] = useState(5.0);
  const [budget, setBudget] = useState(25000);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onCreateCampaign({
      title,
      target_segment: targetSegment,
      trigger_condition: "Autonomous intent match on catalog query",
      bundle_offer: bundleOffer,
      discount_percentage: discount,
      max_budget_inr: budget,
      status: "ACTIVE"
    });
    setShowModal(false);
    setTitle("");
    setBundleOffer("");
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl mb-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-white">Automated Campaign Orchestrator</h3>
            <span className="px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30 text-[10px] uppercase font-bold">
              AI Powered
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Bounded autonomous campaigns targeting high-affinity customer segments to maximize Merchant Revenue.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-lg shadow-purple-600/20 transition"
        >
          <Plus className="h-4 w-4" />
          Create Bounded Campaign
        </button>
      </div>

      {/* Campaigns Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {campaigns.map((camp) => (
          <div
            key={camp.id}
            className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 transition"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-white line-clamp-1">{camp.title}</span>
              <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold">
                {camp.status}
              </span>
            </div>

            <p className="text-xs text-indigo-300/80 mb-3 line-clamp-2">
              {camp.bundle_offer}
            </p>

            <div className="grid grid-cols-3 gap-2 bg-slate-900/90 p-2.5 rounded-lg border border-slate-800/80 text-[11px] mb-2">
              <div>
                <span className="text-slate-500 block">Conversions</span>
                <span className="font-bold text-white">{camp.conversions}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Discount</span>
                <span className="font-bold text-amber-400">{camp.discount_percentage}%</span>
              </div>
              <div>
                <span className="text-slate-500 block">Rev Generated</span>
                <span className="font-bold text-emerald-400">₹{camp.revenue_generated_inr.toLocaleString("en-IN")}</span>
              </div>
            </div>

            <div className="flex items-center justify-between text-[10px] text-slate-500">
              <span>Budget: ₹{camp.spent_budget_inr.toLocaleString("en-IN")} / ₹{camp.max_budget_inr.toLocaleString("en-IN")}</span>
              <span className="text-purple-400 font-semibold">{camp.target_segment.replace("seg_", "").replace("_", " ")}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 max-w-md w-full rounded-2xl p-6 shadow-2xl">
            <h4 className="text-base font-bold text-white mb-4">Create Bounded AI Campaign</h4>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="text-xs text-slate-400 font-semibold mb-1 block">Campaign Title</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Ergonomic Master: Mouse + Wrist Rest Combo"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 font-semibold mb-1 block">Target Segment</label>
                <select
                  value={targetSegment}
                  onChange={(e) => setTargetSegment(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
                >
                  {segments.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} (Propensity: {(s.upsell_propensity_score * 100).toFixed(0)}%)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs text-slate-400 font-semibold mb-1 block">Bundle Offer & Incentive</label>
                <input
                  type="text"
                  required
                  value={bundleOffer}
                  onChange={(e) => setBundleOffer(e.target.value)}
                  placeholder="e.g. Save ₹250 when pairing Vertical Mouse with Leather Desk Mat"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 font-semibold mb-1 block">Discount Rate (%)</label>
                  <input
                    type="number"
                    min="1"
                    max="20"
                    value={discount}
                    onChange={(e) => setDiscount(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 font-semibold mb-1 block">Max Budget (₹)</label>
                  <input
                    type="number"
                    min="5000"
                    max="100000"
                    step="5000"
                    value={budget}
                    onChange={(e) => setBudget(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
                  />
                </div>
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow"
                >
                  Activate Campaign
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
''')

# 3. PolicyControls & GuardrailSimulator
write('frontend/src/components/GuardrailsCenter/PolicyControls.tsx', '''import React, { useState } from "react";
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
''')

print("Part 2 frontend components written successfully!")
