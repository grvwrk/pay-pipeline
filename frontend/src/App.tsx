import React, { useState, useEffect } from "react";
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
    merchant_whitelist: ["merch_pay_pipeline_01"]
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
