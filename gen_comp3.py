import os

def write(filepath, content):
    d = os.path.dirname(filepath)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Wrote: {filepath}")

# 1. MachineBuyerSandbox (ACP Inspector)
write('frontend/src/components/ACPInspector/MachineBuyerSandbox.tsx', '''import React, { useState } from "react";
import { api } from "../../services/api";
import { Terminal, Send, Play, CheckCircle2, ShieldCheck, Code2, ArrowRight } from "lucide-react";

export const MachineBuyerSandbox: React.FC = () => {
  const [activeEndpoint, setActiveEndpoint] = useState<"catalog" | "quote" | "checkout" | "mcp">("catalog");
  const [responseJson, setResponseJson] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const runDiscovery = async () => {
    setLoading(true);
    try {
      const res = await api.getACPCatalog();
      setResponseJson(res);
    } catch (e: any) {
      setResponseJson({ error: e.message });
    } finally {
      setLoading(false);
    }
  };

  const runQuote = async () => {
    setLoading(true);
    try {
      const res = await api.getACPQuote(["sku_kb_keychron_k2"], true);
      setResponseJson(res);
    } catch (e: any) {
      setResponseJson({ error: e.message });
    } finally {
      setLoading(false);
    }
  };

  const runCheckout = async () => {
    setLoading(true);
    try {
      const res = await api.executeACPCheckout("quote_auto_test", `acp_idem_${Date.now()}`);
      setResponseJson(res);
    } catch (e: any) {
      setResponseJson({ error: e.message });
    } finally {
      setLoading(false);
    }
  };

  const runMCPSchema = async () => {
    setLoading(true);
    try {
      const res = await api.getMCPToolsSchema();
      setResponseJson(res);
    } catch (e: any) {
      setResponseJson({ error: e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl mb-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-white">Agentic Commerce Protocol (ACP / MCP) Machine Inspector</h3>
            <span className="px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 text-[10px] uppercase font-bold">
              Machine-to-Machine Ready
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Test how external autonomous AI buyers (Claude, OpenAI, autonomous shopping agents) query machine-readable schemas and transact programmatically.
          </p>
        </div>
      </div>

      {/* Buttons */}
      <div className="flex flex-wrap gap-2 mb-4">
        <button
          onClick={() => { setActiveEndpoint("catalog"); runDiscovery(); }}
          className={`px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition ${
            activeEndpoint === "catalog"
              ? "bg-cyan-600 text-white shadow-lg shadow-cyan-600/30"
              : "bg-slate-950 border border-slate-800 text-slate-400 hover:text-white"
          }`}
        >
          <Code2 className="h-3.5 w-3.5" />
          GET /acp/catalog (Discovery)
        </button>

        <button
          onClick={() => { setActiveEndpoint("quote"); runQuote(); }}
          className={`px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition ${
            activeEndpoint === "quote"
              ? "bg-cyan-600 text-white shadow-lg shadow-cyan-600/30"
              : "bg-slate-950 border border-slate-800 text-slate-400 hover:text-white"
          }`}
        >
          <Code2 className="h-3.5 w-3.5" />
          POST /acp/quote (Bundle Pricing)
        </button>

        <button
          onClick={() => { setActiveEndpoint("checkout"); runCheckout(); }}
          className={`px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition ${
            activeEndpoint === "checkout"
              ? "bg-cyan-600 text-white shadow-lg shadow-cyan-600/30"
              : "bg-slate-950 border border-slate-800 text-slate-400 hover:text-white"
          }`}
        >
          <Send className="h-3.5 w-3.5" />
          POST /acp/checkout (Machine Transacting)
        </button>

        <button
          onClick={() => { setActiveEndpoint("mcp"); runMCPSchema(); }}
          className={`px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition ${
            activeEndpoint === "mcp"
              ? "bg-cyan-600 text-white shadow-lg shadow-cyan-600/30"
              : "bg-slate-950 border border-slate-800 text-slate-400 hover:text-white"
          }`}
        >
          <Terminal className="h-3.5 w-3.5" />
          GET /acp/mcp-schema (Model Context Protocol)
        </button>
      </div>

      {/* Response Terminal */}
      <div className="rounded-xl bg-slate-950 border border-slate-800 p-4 font-mono text-xs overflow-x-auto max-h-[450px]">
        <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800 text-[11px] text-slate-500">
          <span>ACP Response Payload</span>
          <span>{loading ? "Transacting..." : "Status: 200 OK"}</span>
        </div>
        {loading ? (
          <div className="text-cyan-400 py-4 animate-pulse">Running autonomous protocol interaction...</div>
        ) : responseJson ? (
          <pre className="text-cyan-300/90 whitespace-pre-wrap">{JSON.stringify(responseJson, null, 2)}</pre>
        ) : (
          <div className="text-slate-600 py-4">Click any protocol endpoint above to test external AI buyer transactions.</div>
        )}
      </div>
    </div>
  );
};
''')

# 2. HashChainVerifier (Audit Inspector)
write('frontend/src/components/AuditInspector/HashChainVerifier.tsx', '''import React, { useState } from "react";
import { AuditChainVerificationResult } from "../../types";
import { api } from "../../services/api";
import { ShieldCheck, ShieldAlert, CheckCircle2, RefreshCw, AlertTriangle, Lock } from "lucide-react";

interface HashChainVerifierProps {
  onRefetchRecords: () => void;
}

export const HashChainVerifier: React.FC<HashChainVerifierProps> = ({ onRefetchRecords }) => {
  const [verification, setVerification] = useState<AuditChainVerificationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [tamperMsg, setTamperMsg] = useState("");

  const handleVerify = async () => {
    setLoading(true);
    try {
      const res = await api.verifyAuditChain();
      setVerification(res);
      setTamperMsg("");
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTamperAttack = async () => {
    try {
      // Simulate malicious database tampering on record #1
      const res = await api.simulateTampering(1, 99999.0);
      setTamperMsg(res.message);
      onRefetchRecords();
      handleVerify(); // Immediately re-verify to demonstrate instant detection
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl mb-6">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-white">Cryptographic SHA-256 Hash Chain & HMAC Verifier</h3>
            <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[10px] uppercase font-bold">
              Zero-Trust Audit
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Every intent, decision, policy evaluation, and Razorpay payment event is cryptographically linked with SHA-256 and signed with HMAC.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleVerify}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-600/20 transition disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Verify Chain Integrity</span>
          </button>

          <button
            onClick={handleTamperAttack}
            className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl bg-red-950/40 hover:bg-red-900/50 border border-red-500/30 text-red-400 text-xs font-semibold transition"
          >
            <AlertTriangle className="h-3.5 w-3.5" />
            <span>Simulate DB Tampering</span>
          </button>
        </div>
      </div>

      {tamperMsg && (
        <div className="p-3 mb-4 rounded-xl bg-red-950/60 border border-red-500/40 text-red-200 text-xs flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-red-400 flex-shrink-0" />
          <span>{tamperMsg}</span>
        </div>
      )}

      {/* Verification Result Banner */}
      {verification && (
        <div
          className={`p-4 rounded-xl border flex items-center justify-between ${
            verification.is_valid
              ? "bg-emerald-950/40 border-emerald-500/50 text-emerald-200"
              : "bg-red-950/60 border-red-500/60 text-red-200"
          }`}
        >
          <div className="flex items-center gap-3">
            <div
              className={`h-10 w-10 rounded-xl flex items-center justify-center ${
                verification.is_valid ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"
              }`}
            >
              {verification.is_valid ? <CheckCircle2 className="h-5 w-5" /> : <ShieldAlert className="h-5 w-5" />}
            </div>
            <div>
              <div className="font-bold text-sm">
                {verification.is_valid ? "Cryptographic Chain Verified: ZERO TAMPERING DETECTED" : "SECURITY ALERT: TAMPERING DETECTED"}
              </div>
              <div className="text-xs opacity-80">
                {verification.is_valid
                  ? `All ${verification.total_records} audit records intact from Genesis block to latest block.`
                  : verification.error_detail}
              </div>
            </div>
          </div>

          <div className="hidden sm:block text-right font-mono text-[11px] opacity-70">
            <div>Genesis: {verification.genesis_hash.substring(0, 16)}...</div>
            <div>Latest: {verification.latest_hash.substring(0, 16)}...</div>
          </div>
        </div>
      )}
    </div>
  );
};
''')

# 3. AuditLogTable
write('frontend/src/components/AuditInspector/AuditLogTable.tsx', '''import React from "react";
import { AuditRecord } from "../../types";
import { ShieldCheck, ShieldAlert, CheckCircle2, Lock, ArrowRight, User, Bot, Server } from "lucide-react";

interface AuditLogTableProps {
  records: AuditRecord[];
}

export const AuditLogTable: React.FC<AuditLogTableProps> = ({ records }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-bold text-white flex items-center gap-2">
          <Lock className="h-4 w-4 text-indigo-400" />
          Immutable Audit Trail ({records.length} Signed Blocks)
        </h4>
        <span className="text-xs text-slate-500">Live Streaming</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950/80 text-slate-400 font-semibold border-b border-slate-800">
            <tr>
              <th className="py-3 px-3">#</th>
              <th className="py-3 px-3">Actor / Role</th>
              <th className="py-3 px-3">Action</th>
              <th className="py-3 px-3">Guardrail Status</th>
              <th className="py-3 px-3">Hash Link (prev → curr)</th>
              <th className="py-3 px-3">HMAC Signature</th>
              <th className="py-3 px-3">Timestamp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {records.map((rec) => (
              <tr key={rec.event_id} className="hover:bg-slate-800/30 transition">
                <td className="py-3 px-3 text-slate-500 font-bold">{rec.index}</td>
                <td className="py-3 px-3 font-sans">
                  <span className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 text-[10px] font-semibold">
                    {rec.actor_role}
                  </span>
                </td>
                <td className="py-3 px-3 font-sans font-medium text-white">
                  {rec.action}
                </td>
                <td className="py-3 px-3 font-sans">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      rec.result_status === "SUCCESS"
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                        : "bg-red-500/10 text-red-400 border border-red-500/30"
                    }`}
                  >
                    {rec.guardrail_decision || rec.result_status}
                  </span>
                </td>
                <td className="py-3 px-3 text-[10px] text-slate-400">
                  <span className="text-slate-500">{rec.prev_hash.substring(0, 8)}</span>
                  <span className="text-indigo-400 mx-1">→</span>
                  <span className="text-indigo-300 font-bold">{rec.record_hash.substring(0, 8)}</span>
                </td>
                <td className="py-3 px-3 text-[10px] text-slate-500 font-mono">
                  {rec.signature.substring(0, 12)}...
                </td>
                <td className="py-3 px-3 text-[11px] text-slate-500 font-sans">
                  {new Date(rec.timestamp).toLocaleTimeString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
''')

# 4. ScenariosModal (1-Click Guided Demos)
write('frontend/src/components/ScenariosModal.tsx', '''import React, { useState } from "react";
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
''')

# 5. Main App Container
write('frontend/src/App.tsx', '''import React, { useState, useEffect } from "react";
import { Header } from "./components/Header";
import { ChatInterface } from "./components/ChatBuyer/ChatInterface";
import { RevenueKPIs } from "./components/MerchantDashboard/RevenueKPIs";
import { CampaignOrchestrator } from "./components/MerchantDashboard/CampaignOrchestrator";
import { PolicyControls } from "./components/GuardrailsCenter/PolicyControls";
import { MachineBuyerSandbox } from "./components/ACPInspector/MachineBuyerSandbox";
import { HashChainVerifier } from "./components/AuditInspector/HashChainVerifier";
import { AuditLogTable } from "./components/AuditInspector/AuditLogTable";
import { ScenariosModal } from "./components/ScenariosModal";
import { api } from "./services/api";
import { GuardrailConfig, MerchantKPIs, CustomerSegment, Campaign, AuditRecord } from "./types";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState("chat");
  const [scenariosModalOpen, setScenariosModalOpen] = useState(false);

  // App Data
  const [config, setConfig] = useState<GuardrailConfig>({
    max_transaction_amount_inr: 5000.0,
    max_cumulative_spend_inr: 15000.0,
    approval_threshold_inr: 3000.0,
    max_item_quantity: 5,
    allowed_currency: "INR",
    allowed_categories: ["mechanical_keyboards", "computer_peripherals", "workspace_accessories", "developer_gear", "ergonomics", "audio_equipment"],
    merchant_whitelist: ["merch_aeropay_electronics_01"]
  });

  const [merchantData, setMerchantData] = useState<{
    kpis: MerchantKPIs;
    segments: CustomerSegment[];
    campaigns: Campaign[];
  }>({
    kpis: {
      total_revenue_inr: 1284500.0,
      average_order_value_inr: 4498.0,
      baseline_aov_without_agent_inr: 3200.0,
      aov_growth_percentage: 40.6,
      upsell_conversion_rate: 0.42,
      cart_abandonment_rate: 0.18,
      guardrail_interceptions_count: 28,
      total_orders_processed: 286
    },
    segments: [],
    campaigns: []
  });

  const [auditRecords, setAuditRecords] = useState<AuditRecord[]>([]);

  const loadData = async () => {
    try {
      const [cfg, merch, audits] = await Promise.all([
        api.getGuardrailConfig(),
        api.getMerchantAnalytics(),
        api.getAuditRecords()
      ]);
      setConfig(cfg);
      setMerchantData(merch);
      setAuditRecords(audits);
    } catch (err) {
      console.error("Failed loading data:", err);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(async () => {
      try {
        const audits = await api.getAuditRecords();
        setAuditRecords(audits);
      } catch (e) {}
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleSaveConfig = async (newConfig: GuardrailConfig) => {
    try {
      const updated = await api.updateGuardrailConfig(newConfig);
      setConfig(updated);
    } catch (err) {
      alert("Failed updating guardrails");
    }
  };

  const handleCreateCampaign = async (campaign: Partial<Campaign>) => {
    try {
      await api.createCampaign(campaign);
      const merch = await api.getMerchantAnalytics();
      setMerchantData(merch);
    } catch (err) {
      alert("Failed creating campaign");
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenScenarios={() => setScenariosModalOpen(true)}
        spendLimit={config.max_transaction_amount_inr}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === "chat" && <ChatInterface />}

        {activeTab === "merchant" && (
          <div>
            <RevenueKPIs kpis={merchantData.kpis} />
            <CampaignOrchestrator
              campaigns={merchantData.campaigns}
              segments={merchantData.segments}
              onCreateCampaign={handleCreateCampaign}
            />
          </div>
        )}

        {activeTab === "guardrails" && (
          <div>
            <PolicyControls config={config} onSaveConfig={handleSaveConfig} />
          </div>
        )}

        {activeTab === "acp" && (
          <div>
            <MachineBuyerSandbox />
          </div>
        )}

        {activeTab === "audit" && (
          <div>
            <HashChainVerifier onRefetchRecords={loadData} />
            <AuditLogTable records={auditRecords} />
          </div>
        )}
      </main>

      <ScenariosModal
        isOpen={scenariosModalOpen}
        onClose={() => setScenariosModalOpen(false)}
        onScenarioExecuted={loadData}
      />
    </div>
  );
};

export default App;
''')

print("Part 3 frontend components written successfully!")
