import React from "react";
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
