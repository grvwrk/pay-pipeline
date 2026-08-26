import React from "react";
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
