import React, { useState, useRef, useEffect } from "react";
import { ChatMessage, Product, BundleOffer, RazorpayOrder, AgentReasoningStep } from "../../types";
import { api } from "../../services/api";
import { ProductCard } from "./ProductCard";
import { UpsellOfferCard } from "./UpsellOfferCard";
import { ApprovalModal } from "./ApprovalModal";
import { RazorpayCheckoutModal } from "./RazorpayCheckoutModal";
import { Send, Bot, User, ShieldAlert, ShieldCheck, Sparkles, ChevronDown, ChevronUp, Cpu, Wrench } from "lucide-react";

export const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "msg_init_1",
      sender: "agent",
      text: "Hello! I am your **AeroPay Agentic Commerce Assistant** powered by a Multi-Agent LlamaIndex Orchestrator.\n\nTell me what you're looking for (e.g. *'best available peanut butter with highest protein % under 700rs'* or *'Buy Keychron K2 mechanical keyboard'*).",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [openTraceIds, setOpenTraceIds] = useState<Record<string, boolean>>({});

  const [approvalModalOpen, setApprovalModalOpen] = useState(false);
  const [pendingApprovalToken, setPendingApprovalToken] = useState("");
  const [pendingAmount, setPendingAmount] = useState(0);
  const [pendingReason, setPendingReason] = useState("");

  const [checkoutModalOpen, setCheckoutModalOpen] = useState(false);
  const [currentOrder, setCurrentOrder] = useState<RazorpayOrder | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const toggleTrace = (msgId: string) => {
    setOpenTraceIds((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  const handleSend = async (customText?: string, approvalToken?: string, sku?: string) => {
    const textToSend = customText || input;
    if (!textToSend.trim() && !approvalToken) return;

    if (!approvalToken) {
      const userMsg: ChatMessage = {
        id: `user_${Date.now()}`,
        sender: "user",
        text: textToSend,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
    }

    setLoading(true);

    try {
      const res = await api.sendChatMessage(textToSend, approvalToken, undefined, sku);

      const agentMsgId = `agent_${Date.now()}`;
      const agentMsg: ChatMessage = {
        id: agentMsgId,
        sender: "agent",
        text: res.message || "Processed request successfully.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        products: res.products,
        upsell_bundle: res.upsell_bundle,
        order: res.order,
        policy_evaluation: res.policy_evaluation,
        requires_approval: res.type === "APPROVAL_REQUIRED",
        approval_token: res.approval_token,
        guardrail_denied: res.type === "GUARDRAIL_DENIED",
        reasoning_steps: res.reasoning_steps
      };

      setMessages((prev) => [...prev, agentMsg]);

      // Auto-open reasoning trace for transparency
      if (res.reasoning_steps && res.reasoning_steps.length > 0) {
        setOpenTraceIds((prev) => ({ ...prev, [agentMsgId]: true }));
      }

      if (res.type === "APPROVAL_REQUIRED") {
        setPendingApprovalToken(res.approval_token || "");
        setPendingAmount(res.cart?.total_amount || 0);
        setPendingReason(res.message);
        setApprovalModalOpen(true);
      }

      if (res.type === "ORDER_CREATED" && res.order) {
        setCurrentOrder(res.order);
        setCheckoutModalOpen(true);
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err_${Date.now()}`,
          sender: "system",
          text: `⚠️ Error executing request: ${err.message}`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleBuyProduct = (product: Product) => {
    handleSend(`Buy ${product.name} for ₹${product.price}`, undefined, product.id);
  };

  const handleAcceptBundle = (bundle: BundleOffer) => {
    handleSend(`Add ${bundle.complementary_product_name} and accept the 5% bundle discount`, undefined, bundle.primary_product_id);
  };

  const handleApprove = (token: string) => {
    setApprovalModalOpen(false);
    handleSend("Approve and proceed with purchase", token);
  };

  const handlePaymentComplete = (paymentId: string, status: "pending" | "captured" | "failed") => {
    if (status === "pending") {
      setMessages((prev) => [
        ...prev,
        {
          id: `pay_pending_${Date.now()}`,
          sender: "system",
          text: `Payment initiated; awaiting Razorpay webhook verification.\n\nPayment ID: \`${paymentId}\`\nThe order will only be marked complete after an authenticated payment.captured webhook is received.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        }
      ]);
      return;
    }
    if (status === "captured") {
      setMessages((prev) => [
        ...prev,
        {
          id: `pay_success_${Date.now()}`,
          sender: "system",
          text: `✅ **Payment Captured Successfully on Razorpay Rails!**\n\nPayment ID: \`${paymentId}\`\nAuthoritative Webhook: **VERIFIED**\nCryptographic Audit Trail: **SIGNED & HASH-CHAINED**`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        }
      ]);
    } else {
      setMessages((prev) => [
        ...prev,
        {
          id: `pay_fail_${Date.now()}`,
          sender: "system",
          text: `❌ **Payment Authorization Declined by Issuing Bank**\n\nState machine updated to \`PAYMENT_FAILED\`. Zero funds deducted. Audit log updated.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        }
      ]);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] max-w-5xl mx-auto">
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.sender !== "user" && (
              <div className="h-8 w-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center flex-shrink-0 text-indigo-400">
                <Bot className="h-4 w-4" />
              </div>
            )}

            <div className={`max-w-2xl w-full ${msg.sender === "user" ? "items-end" : "items-start"}`}>
              {/* Agent Reasoning & Tool Trace Accordion */}
              {msg.reasoning_steps && msg.reasoning_steps.length > 0 && (
                <div className="mb-2 bg-slate-900/90 border border-indigo-500/30 rounded-xl overflow-hidden shadow-lg backdrop-blur-sm">
                  <button
                    onClick={() => toggleTrace(msg.id)}
                    className="w-full px-3.5 py-2 flex items-center justify-between text-xs font-medium text-indigo-300 hover:bg-indigo-950/40 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-3.5 w-3.5 text-indigo-400 animate-pulse" />
                      <span>Multi-Agent Reasoning & Tool Execution ({msg.reasoning_steps.length} steps)</span>
                    </div>
                    {openTraceIds[msg.id] ? (
                      <ChevronUp className="h-3.5 w-3.5 text-indigo-400" />
                    ) : (
                      <ChevronDown className="h-3.5 w-3.5 text-indigo-400" />
                    )}
                  </button>

                  {openTraceIds[msg.id] && (
                    <div className="px-3.5 py-2.5 space-y-2.5 bg-slate-950/60 border-t border-indigo-500/20 text-xs font-mono">
                      {msg.reasoning_steps.map((step, idx) => (
                        <div key={idx} className="border-l-2 border-indigo-500/50 pl-2.5 space-y-1">
                          <div className="flex items-center gap-1.5 text-indigo-300 font-semibold">
                            <Cpu className="h-3 w-3 text-indigo-400" />
                            <span>[{step.agent_name}]</span>
                            {step.action && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-900/50 text-indigo-200 uppercase">
                                {step.action}
                              </span>
                            )}
                          </div>
                          <p className="text-slate-300 font-sans text-xs">{step.thought}</p>
                          {step.tool_called && (
                            <div className="flex items-center gap-1 text-[11px] text-amber-300/90">
                              <Wrench className="h-3 w-3" />
                              <span>Tool Invoked: <code className="bg-slate-900 px-1 py-0.5 rounded text-amber-200">{step.tool_called}</code></span>
                            </div>
                          )}
                          {step.result_summary && (
                            <p className="text-emerald-400 text-[11px]">↳ {step.result_summary}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div
                className={`p-4 rounded-2xl text-sm leading-relaxed ${
                  msg.sender === "user"
                    ? "bg-indigo-600 text-white rounded-br-none"
                    : msg.guardrail_denied
                    ? "bg-red-950/60 border border-red-500/40 text-red-200 rounded-bl-none"
                    : msg.requires_approval
                    ? "bg-amber-950/60 border border-amber-500/40 text-amber-200 rounded-bl-none"
                    : "bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none"
                }`}
              >
                <div className="whitespace-pre-line">
                  {msg.text}
                </div>

                {msg.guardrail_denied && (
                  <div className="mt-2.5 pt-2 border-t border-red-500/30 flex items-center gap-1.5 text-xs text-red-400 font-semibold">
                    <ShieldAlert className="h-4 w-4" />
                    Deterministic Guardrail: Money tool execution intercepted
                  </div>
                )}

                {msg.requires_approval && (
                  <div className="mt-2.5 pt-2 border-t border-amber-500/30 flex items-center gap-1.5 text-xs text-amber-400 font-semibold">
                    <ShieldCheck className="h-4 w-4" />
                    Human-in-the-Loop Gating: Order &gt; ₹3,000 threshold
                  </div>
                )}
              </div>

              {msg.products && msg.products.length > 0 && (
                <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {msg.products.map((product) => (
                    <ProductCard
                      key={product.id}
                      product={product}
                      onBuy={handleBuyProduct}
                    />
                  ))}
                </div>
              )}

              {msg.upsell_bundle && (
                <div className="mt-3">
                  <UpsellOfferCard
                    bundle={msg.upsell_bundle}
                    onAcceptBundle={handleAcceptBundle}
                  />
                </div>
              )}
            </div>

            {msg.sender === "user" && (
              <div className="h-8 w-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center flex-shrink-0 text-slate-400">
                <User className="h-4 w-4" />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex gap-3 justify-start">
            <div className="h-8 w-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center flex-shrink-0 text-indigo-400">
              <Bot className="h-4 w-4 animate-spin" />
            </div>
            <div className="bg-slate-900 border border-slate-800 px-4 py-3 rounded-2xl rounded-bl-none text-xs text-slate-400 flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5 text-indigo-400 animate-pulse" />
              <span>Multi-Agent Orchestrator Reasoning...</span>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      <div className="p-4 bg-slate-900/80 border-t border-slate-800 backdrop-blur-md">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Express buying intent (e.g. 'Find me peanut butter with highest protein % under 700rs', 'Buy Keychron K2')..."
            className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-2.5 rounded-xl font-medium text-sm flex items-center gap-2 transition-colors shadow-lg shadow-indigo-600/20"
          >
            <Send className="h-4 w-4" />
            <span>Send</span>
          </button>
        </form>
      </div>

      <ApprovalModal
        isOpen={approvalModalOpen}
        approvalToken={pendingApprovalToken}
        amount={pendingAmount}
        reason={pendingReason}
        onApprove={handleApprove}
        onClose={() => setApprovalModalOpen(false)}
      />

      <RazorpayCheckoutModal
        isOpen={checkoutModalOpen}
        order={currentOrder}
        onClose={() => setCheckoutModalOpen(false)}
        onPaymentComplete={handlePaymentComplete}
      />
    </div>
  );
};
