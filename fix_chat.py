import os

def write(filepath, content):
    d = os.path.dirname(filepath)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Wrote: {filepath}")

write('frontend/src/components/ChatBuyer/ChatInterface.tsx', '''import React, { useState, useRef, useEffect } from "react";
import { ChatMessage, Product, BundleOffer, RazorpayOrder } from "../../types";
import { api } from "../../services/api";
import { ProductCard } from "./ProductCard";
import { UpsellOfferCard } from "./UpsellOfferCard";
import { ApprovalModal } from "./ApprovalModal";
import { RazorpayCheckoutModal } from "./RazorpayCheckoutModal";
import { Send, Bot, User, ShieldAlert, ShieldCheck } from "lucide-react";

export const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "msg_init_1",
      sender: "agent",
      text: "Hello! I am your **AeroPay Agentic Commerce Assistant** powered by LlamaIndex Workflows.\\n\\nTell me what you're looking for (e.g. *'Find me a mechanical keyboard under ₹5000'* or *'Buy a wireless vertical mouse'*).",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

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
      
      const agentMsg: ChatMessage = {
        id: `agent_${Date.now()}`,
        sender: "agent",
        text: res.message || "Processed request successfully.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        products: res.products,
        upsell_bundle: res.upsell_bundle,
        order: res.order,
        policy_evaluation: res.policy_evaluation,
        requires_approval: res.type === "APPROVAL_REQUIRED",
        approval_token: res.approval_token,
        guardrail_denied: res.type === "GUARDRAIL_DENIED"
      };

      setMessages((prev) => [...prev, agentMsg]);

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

  const handlePaymentComplete = (paymentId: string, status: "captured" | "failed") => {
    if (status === "captured") {
      setMessages((prev) => [
        ...prev,
        {
          id: `pay_success_${Date.now()}`,
          sender: "system",
          text: `✅ **Payment Captured Successfully on Razorpay Rails!**\\n\\nPayment ID: \`${paymentId}\`\\nAuthoritative Webhook: **VERIFIED**\\nCryptographic Audit Trail: **SIGNED & HASH-CHAINED**`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        }
      ]);
    } else {
      setMessages((prev) => [
        ...prev,
        {
          id: `pay_fail_${Date.now()}`,
          sender: "system",
          text: `❌ **Payment Authorization Declined by Issuing Bank**\\n\\nState machine updated to \`PAYMENT_FAILED\`. Zero funds deducted. Audit log updated.`,
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

            <div className={`max-w-2xl ${msg.sender === "user" ? "items-end" : "items-start"}`}>
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
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
                  {msg.products.slice(0, 2).map((p, idx) => (
                    <ProductCard key={p.id} product={p} onBuy={handleBuyProduct} highlight={idx === 0} />
                  ))}
                </div>
              )}

              {msg.upsell_bundle && (
                <UpsellOfferCard bundle={msg.upsell_bundle} onAcceptBundle={handleAcceptBundle} />
              )}

              <div className="text-[10px] text-slate-500 mt-1 px-1">{msg.timestamp}</div>
            </div>

            {msg.sender === "user" && (
              <div className="h-8 w-8 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0 text-white">
                <User className="h-4 w-4" />
              </div>
            )}
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>

      <div className="p-4 bg-slate-900/80 border-t border-slate-800 backdrop-blur rounded-b-2xl">
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
            placeholder="Type intent (e.g. 'Find mechanical keyboard under ₹5000' or 'Buy keychron k2')..."
            className="flex-1 bg-slate-950 border border-slate-700/70 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-indigo-500 transition"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm flex items-center gap-2 shadow-lg shadow-indigo-600/30 transition disabled:opacity-50"
          >
            {loading ? <span className="animate-spin">🌀</span> : <Send className="h-4 w-4" />}
            <span>Send</span>
          </button>
        </form>
      </div>

      <ApprovalModal
        isOpen={approvalModalOpen}
        onClose={() => setApprovalModalOpen(false)}
        onApprove={handleApprove}
        approvalToken={pendingApprovalToken}
        amount={pendingAmount}
        reason={pendingReason}
      />

      {currentOrder && (
        <RazorpayCheckoutModal
          isOpen={checkoutModalOpen}
          onClose={() => setCheckoutModalOpen(false)}
          order={currentOrder}
          onPaymentComplete={handlePaymentComplete}
        />
      )}
    </div>
  );
};
''')

print("ChatInterface.tsx JSX error fixed!")
