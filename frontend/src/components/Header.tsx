import React from "react";
import { ShieldCheck, PlayCircle, Bot, Sparkles, CreditCard, Lock } from "lucide-react";

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onOpenScenarios: () => void;
  spendLimit: number;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  onOpenScenarios,
  spendLimit
}) => {
  const tabs = [
    { id: "chat", label: "AI Buyer & Checkout", icon: Bot },
    { id: "merchant", label: "Merchant Growth", icon: Sparkles },
    { id: "guardrails", label: "Guardrails & Limits", icon: ShieldCheck },
    { id: "acp", label: "ACP / Machine Storefront", icon: CreditCard },
    { id: "audit", label: "Cryptographic Audit", icon: Lock },
  ];

  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Bot className="h-6 w-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg text-white tracking-tight">pay-pipeline</span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 rounded-full">
                  Razorpay Test
                </span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  LlamaIndex Workflows
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">
                Autonomous Commerce & Revenue Growth Engine
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex items-center gap-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {tab.label}
                </button>
              );
            })}
          </nav>

          {/* Action CTA: 1-Click Guided Demos */}
          <div className="flex items-center gap-3">
            <div className="hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-xs">
              <ShieldCheck className="h-3.5 w-3.5 text-indigo-400" />
              <span className="text-slate-400">Limit:</span>
              <span className="font-semibold text-emerald-400">₹{spendLimit.toLocaleString("en-IN")}</span>
            </div>

            <button
              onClick={onOpenScenarios}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 font-semibold text-xs sm:text-sm hover:from-amber-400 hover:to-orange-400 transition shadow-lg shadow-amber-500/20"
            >
              <PlayCircle className="h-4 w-4 fill-slate-950 text-amber-500" />
              <span>1-Click Live Demos</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
