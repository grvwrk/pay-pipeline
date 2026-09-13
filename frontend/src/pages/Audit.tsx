import { useMemo, useState } from "react";
import { api, ApiError } from "../lib/api";
import { shortHash, when } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import type { AuditRecord } from "../lib/types";
import { PageHeader } from "../components/PageHeader";
import { Badge, Empty, ErrorNote, Json, Panel, Row, Spinner, Stat, toneForState } from "../components/ui";

const GENESIS = "0".repeat(64);

export default function Audit() {
  const { data, error, loading, reload } = useAsync(() => api.auditChain(), []);
  const [selected, setSelected] = useState<AuditRecord | null>(null);
  const [filter, setFilter] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [verdict, setVerdict] = useState<{ ok: boolean; text: string } | null>(null);

  const chain = data?.chain ?? [];

  const records = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return chain;
    return chain.filter((r) =>
      [r.action, r.actor_role, r.actor_id, r.tool_name ?? "", r.result_status, r.explainability_notes]
        .join(" ")
        .toLowerCase()
        .includes(q),
    );
  }, [chain, filter]);

  const denied = chain.filter((r) => r.result_status === "DENIED").length;

  async function verify() {
    setVerifying(true);
    setVerdict(null);
    try {
      const res = await api.auditVerify();
      setVerdict({ ok: res.is_valid, text: res.message });
    } catch (err) {
      setVerdict({ ok: false, text: err instanceof ApiError ? err.message : String(err) });
    } finally {
      setVerifying(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Audit chain"
        subtitle="Every security-relevant event is hash-chained to its predecessor and HMAC-signed, so a record cannot be altered without breaking everything after it."
        actions={
          <>
            <button className="btn-ghost" onClick={reload}>Refresh</button>
            <button className="btn-primary" onClick={verify} disabled={verifying || chain.length === 0}>
              {verifying ? "Walking chain…" : "Verify integrity"}
            </button>
          </>
        }
      />

      <div className="space-y-6 p-8">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Stat label="Records" value={data?.total_events ?? 0} />
          <Stat label="Denied events" value={denied} tone={denied > 0 ? "warn" : "neutral"} hint="Guardrail interceptions" />
          <Stat
            label="Head hash"
            value={<span className="mono text-sm">{shortHash(chain.at(-1)?.record_hash)}</span>}
          />
          <Stat
            label="Integrity"
            value={verdict ? (verdict.ok ? "VERIFIED" : "BROKEN") : "—"}
            tone={verdict ? (verdict.ok ? "good" : "bad") : "neutral"}
            hint={verdict?.text ?? "Run a verification pass"}
          />
        </div>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_26rem]">
          <Panel
            title={`Ledger (${records.length})`}
            actions={
              <input
                className="field w-56 py-1.5 text-xs"
                placeholder="Filter by action, actor, tool…"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              />
            }
          >
            {loading && <div className="px-5 py-6"><Spinner /></div>}
            {error && <ErrorNote error={error} onRetry={reload} />}
            {!loading && !error && records.length === 0 && (
              <Empty
                title="No audit records"
                hint="The ledger fills as soon as the agent searches, checks out, or a guardrail intercepts something."
              />
            )}

            <ul className="divide-y divide-ink-800">
              {records.map((r) => (
                <li key={r.event_id}>
                  <button
                    className={`flex w-full items-start gap-4 px-5 py-3 text-left transition-colors hover:bg-ink-850 ${
                      selected?.event_id === r.event_id ? "bg-ink-850" : ""
                    }`}
                    onClick={() => setSelected(r)}
                  >
                    <span className="mono w-10 shrink-0 pt-0.5 text-ink-400">#{r.index}</span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="mono text-ink-100">{r.action}</span>
                        <Badge tone={toneForState(r.result_status)}>{r.result_status}</Badge>
                        <span className="text-xs text-ink-400">{r.actor_role}</span>
                      </div>
                      {r.explainability_notes && (
                        <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-ink-400">
                          {r.explainability_notes}
                        </p>
                      )}
                    </div>
                    <span className="mono shrink-0 pt-0.5 text-ink-400">
                      {shortHash(r.record_hash, 8)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </Panel>

          <div>
            {selected ? (
              <RecordDetail record={selected} />
            ) : (
              <Panel title="Record detail">
                <p className="px-5 py-8 text-center text-xs leading-relaxed text-ink-400">
                  Select a record to see its links into the chain and the signature that covers it.
                </p>
              </Panel>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function RecordDetail({ record }: { record: AuditRecord }) {
  const isGenesis = record.prev_hash === GENESIS;
  return (
    <div className="space-y-4">
      <Panel
        title={`Record #${record.index}`}
        actions={<Badge tone={toneForState(record.result_status)}>{record.result_status}</Badge>}
      >
        <div className="divide-y divide-ink-800 px-5 py-2">
          <Row k="Event ID" v={<span className="mono break-all">{record.event_id}</span>} />
          <Row k="Timestamp" v={when(record.timestamp)} />
          <Row k="Actor" v={<span className="mono">{record.actor_id}</span>} />
          <Row k="Role" v={record.actor_role} />
          <Row k="Action" v={<span className="mono">{record.action}</span>} />
          <Row k="Tool" v={<span className="mono">{record.tool_name ?? "—"}</span>} />
          <Row k="Guardrail" v={record.guardrail_decision ?? "—"} />
          <Row k="State" v={record.transaction_state ?? "—"} />
          <Row k="Approval required" v={record.approval_required ? "yes" : "no"} />
          <Row k="Latency" v={`${record.latency_ms.toFixed(1)} ms`} />
        </div>
      </Panel>

      <Panel title="Chain linkage">
        <div className="space-y-3 px-5 py-4">
          <div>
            <p className="label">Previous hash {isGenesis && "(genesis)"}</p>
            <p className="mono mt-1 break-all text-ink-300">{record.prev_hash}</p>
          </div>
          <div>
            <p className="label">Record hash</p>
            <p className="mono mt-1 break-all text-ink-100">{record.record_hash}</p>
          </div>
          <div>
            <p className="label">HMAC signature</p>
            <p className="mono mt-1 break-all text-signal">{record.signature}</p>
          </div>
          <p className="text-xs leading-relaxed text-ink-400">
            The hash covers this record plus its predecessor; the signature is computed with a separate secret, so
            recomputing the chain after a direct database edit still will not produce a valid signature.
          </p>
        </div>
      </Panel>

      {record.explainability_notes && (
        <Panel title="Explainability">
          <p className="px-5 py-4 text-sm leading-relaxed text-ink-300">{record.explainability_notes}</p>
        </Panel>
      )}

      {Object.keys(record.arguments ?? {}).length > 0 && (
        <Panel title="Arguments">
          <div className="p-4"><Json data={record.arguments} /></div>
        </Panel>
      )}
    </div>
  );
}
