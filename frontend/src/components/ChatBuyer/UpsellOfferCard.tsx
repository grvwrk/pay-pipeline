import React from "react";
import { BundleOffer } from "../../types";
import { Sparkles, Plus, Check, ArrowRight } from "lucide-react";

interface UpsellOfferCardProps {
  bundle: BundleOffer;
  onAcceptBundle: (bundle: BundleOffer) => void;
}

export const UpsellOfferCard: React.FC<UpsellOfferCardProps> = ({ bundle, onAcceptBundle }) => {
  return (
    <div className="mt-3 p-4 rounded-xl bg-gradient-to-br from-indigo-950/80 via-slate-900/90 to-purple-950/60 border-2 border-indigo-500/50 shadow-xl shadow-indigo-500/10 relative overflow-hidden">
      {/* Badge */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 font-bold text-[11px] tracking-wide uppercase shadow">
          <Sparkles className="h-3 w-3" />
          AI Revenue Growth Opportunity
        </div>
        <span className="text-xs font-bold text-emerald-400 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">
          Save ₹{bundle.savings_amount.toLocaleString("en-IN")} (5% OFF)
        </span>
      </div>

      <h4 className="font-bold text-sm text-white mb-1">
        {bundle.title}
      </h4>

      <p className="text-xs text-indigo-200/90 mb-3">
        {bundle.rationale}
      </p>

      {/* Pricing Comparison */}
      <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800 mb-3 flex items-center justify-between">
        <div>
          <div className="text-[11px] text-slate-400">Standard Separate Total</div>
          <div className="text-xs font-medium text-slate-400 line-through">
            ₹{bundle.original_combined_price.toLocaleString("en-IN")}
          </div>
        </div>

        <ArrowRight className="h-4 w-4 text-indigo-400" />

        <div>
          <div className="text-[11px] text-indigo-300 font-medium">Bundled Autonomous Price</div>
          <div className="text-sm font-bold text-emerald-400">
            ₹{bundle.discounted_bundle_price.toLocaleString("en-IN")}
          </div>
        </div>
      </div>

      {/* Accept CTA */}
      <button
        onClick={() => onAcceptBundle(bundle)}
        className="w-full py-2 px-4 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/25 transition"
      >
        <Plus className="h-4 w-4" />
        Accept Bundle & Add {bundle.complementary_product_name}
      </button>
    </div>
  );
};
