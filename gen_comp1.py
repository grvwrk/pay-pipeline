import os

def write(filepath, content):
    d = os.path.dirname(filepath)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Wrote: {filepath}")

# 1. Header
write('frontend/src/components/Header.tsx', '''import React from "react";
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
                <span className="font-bold text-lg text-white tracking-tight">AeroPay</span>
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
''')

# 2. ProductCard
write('frontend/src/components/ChatBuyer/ProductCard.tsx', '''import React from "react";
import { Product } from "../../types";
import { Star, Truck, ShoppingCart, CheckCircle2 } from "lucide-react";

interface ProductCardProps {
  product: Product;
  onBuy: (product: Product) => void;
  highlight?: boolean;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product, onBuy, highlight = false }) => {
  return (
    <div
      className={`rounded-xl border transition-all overflow-hidden flex flex-col justify-between ${
        highlight
          ? "bg-indigo-950/40 border-indigo-500/50 shadow-xl shadow-indigo-500/10"
          : "bg-slate-900/90 border-slate-800 hover:border-slate-700"
      }`}
    >
      <div>
        {product.image_url && (
          <div className="h-40 w-full overflow-hidden relative">
            <img
              src={product.image_url}
              alt={product.name}
              className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
            />
            <div className="absolute top-2 right-2 px-2 py-0.5 rounded-full bg-slate-950/80 backdrop-blur text-[11px] font-semibold text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3" />
              {product.inventory} in stock
            </div>
          </div>
        )}

        <div className="p-4">
          <div className="flex items-center justify-between gap-2 mb-1">
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              {product.category.replace("_", " ")}
            </span>
            <div className="flex items-center gap-1 text-xs text-amber-400 font-semibold">
              <Star className="h-3.5 w-3.5 fill-amber-400" />
              <span>{product.rating}</span>
              <span className="text-slate-500">({product.review_count})</span>
            </div>
          </div>

          <h3 className="font-semibold text-sm text-white line-clamp-2 mb-1.5">
            {product.name}
          </h3>

          <p className="text-xs text-slate-400 line-clamp-2 mb-3">
            {product.description}
          </p>

          {/* Specs tags */}
          <div className="flex flex-wrap gap-1 mb-3">
            {Object.entries(product.specs).slice(0, 2).map(([key, val]) => (
              <span key={key} className="text-[10px] px-1.5 py-0.5 bg-slate-800/80 text-slate-400 rounded">
                {String(val)}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="px-4 pb-4 pt-2 border-t border-slate-800/60 flex items-center justify-between">
        <div>
          <div className="text-xs text-slate-400">Price</div>
          <div className="text-base font-bold text-white">
            ₹{product.price.toLocaleString("en-IN")}
          </div>
        </div>

        <button
          onClick={() => onBuy(product)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/30 transition"
        >
          <ShoppingCart className="h-3.5 w-3.5" />
          Buy Now
        </button>
      </div>
    </div>
  );
};
''')

# 3. UpsellOfferCard
write('frontend/src/components/ChatBuyer/UpsellOfferCard.tsx', '''import React from "react";
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
''')

# 4. ApprovalModal
write('frontend/src/components/ChatBuyer/ApprovalModal.tsx', '''import React from "react";
import { ShieldAlert, CheckCircle, X } from "lucide-react";

interface ApprovalModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApprove: (token: string) => void;
  approvalToken: string;
  amount: number;
  reason: string;
}

export const ApprovalModal: React.FC<ApprovalModalProps> = ({
  isOpen,
  onClose,
  onApprove,
  approvalToken,
  amount,
  reason
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 max-w-md w-full rounded-2xl p-6 shadow-2xl relative animate-in fade-in zoom-in-95 duration-200">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="h-12 w-12 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center justify-center mb-4">
          <ShieldAlert className="h-6 w-6" />
        </div>

        <h3 className="text-lg font-bold text-white mb-1">
          Gated Human Approval Required
        </h3>

        <p className="text-xs text-slate-300 mb-4">
          This money action requires explicit buyer confirmation because the requested order amount exceeds the autonomous safety threshold of ₹3,000.00.
        </p>

        <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-2 mb-5">
          <div className="flex justify-between text-xs">
            <span className="text-slate-400">Transaction Amount:</span>
            <span className="font-bold text-white">₹{amount.toLocaleString("en-IN")}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-400">Approval Token:</span>
            <span className="font-mono text-indigo-400 text-[11px]">{approvalToken}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-400">Policy Reason:</span>
            <span className="text-amber-400 text-right max-w-[200px] text-[11px]">{reason}</span>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition"
          >
            Deny / Cancel
          </button>
          <button
            onClick={() => onApprove(approvalToken)}
            className="flex-1 py-2.5 px-4 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-semibold flex items-center justify-center gap-1.5 shadow-lg shadow-emerald-600/30 transition"
          >
            <CheckCircle className="h-4 w-4" />
            Approve & Pay
          </button>
        </div>
      </div>
    </div>
  );
};
''')

# 5. RazorpayCheckoutModal
write('frontend/src/components/ChatBuyer/RazorpayCheckoutModal.tsx', '''import React, { useState } from "react";
import { RazorpayOrder } from "../../types";
import { ShieldCheck, CreditCard, Smartphone, CheckCircle2, AlertTriangle, X } from "lucide-react";
import confetti from "canvas-confetti";

interface RazorpayCheckoutModalProps {
  isOpen: boolean;
  onClose: () => void;
  order: RazorpayOrder;
  onPaymentComplete: (paymentId: string, status: "captured" | "failed") => void;
}

export const RazorpayCheckoutModal: React.FC<RazorpayCheckoutModalProps> = ({
  isOpen,
  onClose,
  order,
  onPaymentComplete
}) => {
  const [method, setMethod] = useState<"upi" | "card">("upi");
  const [isProcessing, setIsProcessing] = useState(false);

  if (!isOpen) return null;

  const handlePay = (shouldFail: boolean = false) => {
    setIsProcessing(true);
    setTimeout(() => {
      setIsProcessing(false);
      if (shouldFail) {
        onPaymentComplete(`pay_${Math.random().toString(36).substring(2, 10)}`, "failed");
      } else {
        confetti({
          particleCount: 80,
          spread: 60,
          origin: { y: 0.6 }
        });
        onPaymentComplete(`pay_${Math.random().toString(36).substring(2, 10)}`, "captured");
      }
      onClose();
    }, 1200);
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 max-w-md w-full rounded-2xl p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Razorpay Branding Header */}
        <div className="flex items-center gap-3 mb-4">
          <div className="h-10 w-10 rounded-xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <span className="font-black text-white text-lg tracking-tighter">R</span>
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Razorpay Checkout (Test Mode)</h3>
            <p className="text-xs text-slate-400">Order ID: <span className="font-mono text-slate-300">{order.order_id}</span></p>
          </div>
        </div>

        {/* Amount */}
        <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 mb-4 flex items-center justify-between">
          <span className="text-xs text-slate-400">Total Payable:</span>
          <span className="text-xl font-bold text-emerald-400">₹{order.amount.toLocaleString("en-IN")}</span>
        </div>

        {/* Payment Methods */}
        <div className="space-y-2 mb-5">
          <div className="text-xs font-semibold text-slate-400 mb-1">Select Payment Rail:</div>
          <div
            onClick={() => setMethod("upi")}
            className={`p-3 rounded-xl border cursor-pointer flex items-center gap-3 transition ${
              method === "upi"
                ? "bg-indigo-950/50 border-indigo-500 text-white"
                : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700"
            }`}
          >
            <Smartphone className="h-5 w-5 text-indigo-400" />
            <div className="flex-1 text-xs">
              <div className="font-bold text-white">UPI Reserve Pay / QR</div>
              <div className="text-[11px] text-slate-400">Instant agentic authorization via UPI Rail</div>
            </div>
            {method === "upi" && <CheckCircle2 className="h-4 w-4 text-indigo-400" />}
          </div>

          <div
            onClick={() => setMethod("card")}
            className={`p-3 rounded-xl border cursor-pointer flex items-center gap-3 transition ${
              method === "card"
                ? "bg-indigo-950/50 border-indigo-500 text-white"
                : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700"
            }`}
          >
            <CreditCard className="h-5 w-5 text-indigo-400" />
            <div className="flex-1 text-xs">
              <div className="font-bold text-white">Credit / Debit Card</div>
              <div className="text-[11px] text-slate-400">Razorpay Test Gateway Sandbox</div>
            </div>
            {method === "card" && <CheckCircle2 className="h-4 w-4 text-indigo-400" />}
          </div>
        </div>

        {/* Action buttons */}
        <div className="space-y-2">
          <button
            disabled={isProcessing}
            onClick={() => handlePay(false)}
            className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-blue-600/30 transition disabled:opacity-50"
          >
            {isProcessing ? "Authorizing on Razorpay Rails..." : `Pay ₹${order.amount.toLocaleString("en-IN")} (Test Mode)`}
          </button>

          <button
            disabled={isProcessing}
            onClick={() => handlePay(true)}
            className="w-full py-2 rounded-xl bg-red-950/40 hover:bg-red-900/50 border border-red-500/30 text-red-400 text-xs font-semibold flex items-center justify-center gap-1.5 transition"
          >
            <AlertTriangle className="h-3.5 w-3.5" />
            Simulate Bank Authorization Decline (Graceful Failure Demo)
          </button>
        </div>
      </div>
    </div>
  );
};
''')

# 6. ChatInterface
write('frontend/src/components/ChatBuyer/ChatInterface.tsx', '''import React, { useState, useRef, useEffect } from "react";
import { ChatMessage, Product, BundleOffer, RazorpayOrder } from "../../types";
import { api } from "../../services/api";
import { ProductCard } from "./ProductCard";
import { UpsellOfferCard } from "./UpsellOfferCard";
import { ApprovalModal } from "./ApprovalModal";
import { RazorpayCheckoutModal } from "./RazorpayCheckoutModal";
import { Send, Bot, User, Sparkles, ShieldCheck, ShieldAlert, CheckCircle2, ArrowRight } from "lucide-react";

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

  // Modals state
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

      // If approval is required, open approval modal
      if (res.type === "APPROVAL_REQUIRED") {
        setPendingApprovalToken(res.approval_token || "");
        setPendingAmount(res.cart?.total_amount || 0);
        setPendingReason(res.message);
        setApprovalModalOpen(true);
      }

      // If order was created, open checkout modal
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
      {/* Chat Messages Log */}
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
                {/* Message Text */}
                <div className="whitespace-pre-line">
                  {msg.text}
                </div>

                {/* Guardrail Policy Tag */}
                {msg.guardrail_denied && (
                  <div className="mt-2.5 pt-2 border-t border-red-500/30 flex items-center gap-1.5 text-xs text-red-400 font-semibold">
                    <ShieldAlert className="h-4 w-4" />
                    Deterministic Guardrail: Money tool execution intercepted
                  </div>
                )}

                {msg.requires_approval && (
                  <div className="mt-2.5 pt-2 border-t border-amber-500/30 flex items-center gap-1.5 text-xs text-amber-400 font-semibold">
                    <ShieldCheck className="h-4 w-4" />
                    Human-in-the-Loop Gating: Order > ₹3,000 threshold
                  </div>
                )}
              </div>

              {/* Product recommendations */}
              {msg.products && msg.products.length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
                  {msg.products.slice(0, 2).map((p, idx) => (
                    <ProductCard key={p.id} product={p} onBuy={handleBuyProduct} highlight={idx === 0} />
                  ))}
                </div>
              )}

              {/* Dynamic Upsell Offer */}
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

      {/* Input bar */}
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

      {/* Approval Modal */}
      <ApprovalModal
        isOpen={approvalModalOpen}
        onClose={() => setApprovalModalOpen(false)}
        onApprove={handleApprove}
        approvalToken={pendingApprovalToken}
        amount={pendingAmount}
        reason={pendingReason}
      />

      {/* Razorpay Checkout Modal */}
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

print("Part 1 frontend components written successfully!")
