import React, { useState } from "react";
import { RazorpayOrder } from "../../types";
import { ShieldCheck, CreditCard, Smartphone, CheckCircle2, AlertTriangle, X } from "lucide-react";
import { api } from "../../services/api";

interface RazorpayCheckoutModalProps {
  isOpen: boolean;
  onClose: () => void;
  order: RazorpayOrder;
  onPaymentComplete: (paymentId: string, status: "pending" | "failed") => void;
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

  const handlePay = async (shouldFail: boolean = false) => {
    setIsProcessing(true);
    try {
      const result = await api.initiatePayment(order.order_id, order.amount, method, shouldFail);
      const paymentId = result.payment?.payment_id || "pending";
      onPaymentComplete(paymentId, result.verification_pending ? "pending" : "failed");
      onClose();
    } finally {
      setIsProcessing(false);
    }
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
