import React, { useState } from "react";
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
