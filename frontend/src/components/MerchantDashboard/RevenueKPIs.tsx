import React from "react";
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
