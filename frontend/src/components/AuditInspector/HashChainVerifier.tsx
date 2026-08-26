import React, { useState } from "react";
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
