import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Check,
  LockKeyhole,
  RefreshCw,
  ShieldCheck,
  ShieldQuestion,
  TrendingUp,
} from "lucide-react";
import { api, mutate, MOCK } from "@/api/client";
import { useConsole } from "@/realtime/store";
import {
  Badge,
  Empty,
  ErrorState,
  Loading,
  Panel,
  Tier,
  ActorStamp,
} from "@/components/common";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { PageHeading } from "./Incident";
import { human, time } from "@/lib/utils";
import type { AuditRow, Ledger, Schema } from "@/api/types";

export function LedgerScreen() {
  const entries = useConsole((s) => s.ledger);
  const connected = useConsole((s) => s.connected);
  const [selected, setSelected] = useState<Ledger | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const users = useConsole((s) => s.users);
  const catalog = useQuery({
    queryKey: ["catalog"],
    queryFn: () => api<Schema<"CatalogResponse">>("/catalog"),
  });
  const all = Array.from(
    new Set([
      ...entries.map((e) => e.catalog_id),
      ...(catalog.data?.entries || []).map((e) => e.id),
    ]),
  );
  const pick = (entry: Ledger) => {
    setSelected(entry);
    setReason("");
    setError("");
  };
  const change = async (revoke = false) => {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      await mutate(
        `/ledger/${encodeURIComponent(selected.key)}/${revoke ? "revoke" : "grant"}`,
        revoke ? { reason } : { level: "L2", reason },
      );
      setSelected(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="page-content">
      <PageHeading
        eyebrow="GOVERNANCE / AUTONOMY"
        title="Trust Ledger"
        description="Review command permissions, approval history and scoped autonomy."
        action={
          <Badge>
            <ShieldCheck size={12} /> Human-granted trust
          </Badge>
        }
      />
      {entries
        .filter((e) => e.eligible_for)
        .map((e) => (
          <div className="promotion-banner" key={e.key}>
            <TrendingUp size={22} />
            <div>
              <strong>Ready for the next level</strong>
              <p>
                <code>{e.catalog_id}</code> · {e.counters.approved_unchanged}{" "}
                clean approvals · eligible for {e.eligible_for}
              </p>
            </div>
            <Button variant="default" onClick={() => pick(e)}>
              Review promotion <ArrowRight size={14} />
            </Button>
          </div>
        ))}
      <div className="ledger-legend">
        {[
          ["L0", "Suggest"],
          ["L1", "Approval required"],
          ["L2", "Auto-run read-only"],
          ["L3", "Guarded auto-act"],
        ].map(([level, label]) => (
          <span key={level}>
            <Badge tone={level === "L2" ? "baton" : "neutral"}>{level}</Badge>
            {label}
          </span>
        ))}
      </div>
      <Panel
        title="Command autonomy by role"
        action={<span className="meta">Levels come from backend policy</span>}
      >
        <div className="table-scroll">
          <table className="data-table ledger-table">
            <thead>
              <tr>
                <th>Catalog command</th>
                <th>Tier</th>
                {["operator", "senior", "expert", "steward"].map((r) => (
                  <th key={r}>{human(r)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {all.map((id) => {
                const catalogEntry = catalog.data?.entries.find(
                  (c) => c.id === id,
                );
                return (
                  <tr key={id}>
                    <td>
                      <code>{id}</code>
                      <small>{catalogEntry?.title}</small>
                    </td>
                    <td>
                      <Tier
                        tier={
                          catalogEntry?.tier ||
                          entries.find((e) => e.catalog_id === id)?.tier ||
                          "T0"
                        }
                      />
                    </td>
                    {["operator", "senior", "expert", "steward"].map((role) => {
                      const e = entries.find(
                        (e) => e.catalog_id === id && e.role === role,
                      );
                      return (
                        <td key={role}>
                          {e ? (
                            <button
                              className="ledger-cell"
                              onClick={() => pick(e)}
                            >
                              <Badge
                                tone={e.level === "L2" ? "baton" : "neutral"}
                              >
                                {e.level}
                              </Badge>
                              <span>{e.counters.approved_unchanged} clean</span>
                              {e.eligible_for && (
                                <TrendingUp size={13} className="baton-text" />
                              )}
                            </button>
                          ) : catalogEntry?.tier === "T3" ? (
                            <span className="muted">
                              <LockKeyhole size={14} /> Blocked
                            </span>
                          ) : (
                            <span className="muted">No grant</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>
      <Dialog
        open={!!selected}
        onOpenChange={(o) => !o && setSelected(null)}
        title="Review autonomy grant"
        description="Grants and revocations require a reason and are recorded in the audit chain."
        drawer
      >
        {selected && (
          <>
            <ActorStamp />
            <code className="command-code">{selected.catalog_id}</code>
            <div className="inline-gap">
              <Badge>{selected.role}</Badge>
              <Badge tone="baton">{selected.level}</Badge>
              <span className="meta">{selected.param_class} targets</span>
            </div>
            <div className="ledger-counters">
              {Object.entries(selected.counters).map(([k, v]) => (
                <div key={k}>
                  <span>{human(k)}</span>
                  <strong>{v}</strong>
                </div>
              ))}
            </div>
            <p>
              {selected.distinct_approvers} distinct approvers · granted by{" "}
              {users.find((u) => u.id === selected.granted_by)?.name ||
                selected.granted_by ||
                "No grant yet"}
            </p>
            <h3>History</h3>
            {selected.history?.map((h, i) => (
              <p className="meta" key={i}>
                {h.at} · {h.kind} · {h.reason}
              </p>
            ))}
            <label>
              Reason
              <textarea
                rows={3}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Why is this level appropriate for this role?"
              />
            </label>
            {error && (
              <p className="crit-text" role="alert">
                {error}
              </p>
            )}
            <div className="dialog-actions">
              <Button
                disabled={!connected || !reason.trim() || busy}
                onClick={() => void change(true)}
              >
                Revoke to L1
              </Button>
              <Button
                variant="default"
                disabled={
                  !connected || !reason.trim() || busy || !selected.eligible_for
                }
                onClick={() => void change()}
              >
                Grant L2
              </Button>
            </div>
          </>
        )}
      </Dialog>
    </div>
  );
}
export function AuditScreen() {
  const rows = useConsole((s) => s.audit);
  const [filter, setFilter] = useState("");
  const [incidentOnly, setIncidentOnly] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<AuditRow | null>(null);
  const incident = useConsole((s) => s.incidents.at(-1));
  const verify = useQuery({
    queryKey: ["audit-verify", rows.length],
    queryFn: () => api<Schema<"AuditVerify">>("/audit/verify"),
  });
  const filtered = rows.filter(
    (r) =>
      JSON.stringify(r).toLowerCase().includes(filter.toLowerCase()) &&
      (!incidentOnly || (incident && JSON.stringify(r).includes(incident.id))),
  );
  return (
    <div className="page-content">
      <PageHeading
        eyebrow="GOVERNANCE / AUDIT"
        title="Audit"
        description="Inspect decisions, actors and executions in the verified event chain."
        action={
          <Button onClick={() => void verify.refetch()}>
            <RefreshCw size={13} /> Verify chain
          </Button>
        }
      />
      <div className={`chain-banner ${verify.data?.valid ? "verified" : ""}`}>
        <ShieldCheck size={28} />
        <div>
          <strong>
            {verify.isFetching
              ? "Verifying chain…"
              : verify.data?.valid
                ? `Chain verified · ${verify.data.entries} entries`
                : verify.error
                  ? "Verification unavailable"
                  : "Chain verification failed"}
          </strong>
          <p>
            {verify.data
              ? `SHA-256 · Head ${verify.data.head_hash.slice(0, 24)}…`
              : verify.error?.message || "Checking every link in the chain"}
          </p>
        </div>
        {MOCK && <Badge>Rehearsal audit chain</Badge>}
      </div>
      <div className="table-tools">
        <input
          aria-label="Filter audit log"
          placeholder="Filter by actor, action, target or hash…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <label className="inline-gap">
          <input
            type="checkbox"
            checked={incidentOnly}
            onChange={(e) => setIncidentOnly(e.target.checked)}
          />
          Current incident only
        </label>
        <span className="meta">{filtered.length} entries</span>
      </div>
      <Panel title="Audit log">
        <div className="table-scroll">
          <table className="data-table audit-table">
            <thead>
              <tr>
                <th>Seq</th>
                <th>SIM time</th>
                <th>Actor</th>
                <th>Action</th>
                <th>Target</th>
                <th>Decision</th>
                <th>Hash</th>
              </tr>
            </thead>
            <tbody>
              {[...filtered].reverse().map((r) => (
                <tr key={r.seq}>
                  <td className="mono muted">
                    <button
                      className="audit-inspect"
                      aria-label={`Inspect audit entry ${r.seq}`}
                      onClick={() => setSelectedEntry(r)}
                    >
                      {String(r.seq).padStart(4, "0")}
                    </button>
                  </td>
                  <td className="mono">{time(r.sim_ts)}</td>
                  <td>{r.actor_id.replace("u_", "")}</td>
                  <td>
                    <Badge>{r.action}</Badge>
                  </td>
                  <td title={r.target || ""}>
                    <code>{r.target || "—"}</code>
                  </td>
                  <td>
                    {typeof r.payload.decision === "string"
                      ? human(r.payload.decision)
                      : "—"}
                  </td>
                  <td>
                    <button
                      className="audit-inspect"
                      onClick={() => setSelectedEntry(r)}
                    >
                      <code title={r.hash}>{r.hash.slice(0, 10)}</code>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rows.length && (
            <Empty title="The audit trail starts with your first action">
              Approvals, executions, claims, grants and simulator controls are
              recorded here.
            </Empty>
          )}
        </div>
      </Panel>
      <Dialog
        open={!!selectedEntry}
        onOpenChange={(open) => !open && setSelectedEntry(null)}
        title={`Audit entry ${selectedEntry?.seq ?? ""}`}
        description="The recorded payload, policy, model provenance and chain hashes for this action."
        drawer
      >
        {selectedEntry && (
          <>
            <Badge>{selectedEntry.action}</Badge>
            <dl className="detail-list">
              <dt>Actor</dt>
              <dd>
                {selectedEntry.actor_id} · {selectedEntry.actor_type}
              </dd>
              <dt>SIM time</dt>
              <dd>{selectedEntry.sim_ts}</dd>
              <dt>Target</dt>
              <dd>{selectedEntry.target || "—"}</dd>
              <dt>Policy rules</dt>
              <dd>
                {selectedEntry.policy_rule_ids.join(", ") || "None recorded"}
              </dd>
              <dt>Model / prompt hash</dt>
              <dd>
                {selectedEntry.model_id || "Deterministic"} ·{" "}
                {selectedEntry.prompt_hash || "—"}
              </dd>
              <dt>Recorded payload</dt>
              <dd>
                <pre>{JSON.stringify(selectedEntry.payload, null, 2)}</pre>
              </dd>
              <dt>Previous hash</dt>
              <dd>
                <code>{selectedEntry.prev_hash}</code>
              </dd>
              <dt>Entry hash</dt>
              <dd>
                <code>{selectedEntry.hash}</code>
              </dd>
            </dl>
          </>
        )}
      </Dialog>
    </div>
  );
}
export function EvalScreen() {
  const query = useQuery({
    queryKey: ["eval"],
    queryFn: () => api<Schema<"EvalLatestResponse">>("/eval/latest"),
  });
  return (
    <div className="page-content">
      <PageHeading
        eyebrow="ASSURANCE / EVALUATION"
        title="Evaluation"
        description="Measured command accuracy, safety gates and diagnosis results."
        action={
          <Badge>
            {MOCK ? "Contract example results" : "Latest backend run"}
          </Badge>
        }
      />
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <ErrorState
          message={query.error.message}
          retry={() => void query.refetch()}
        />
      ) : !query.data?.run ? (
        <Empty title="No evaluation run yet">
          Run make eval on the backend to populate this view.
        </Empty>
      ) : (
        <>
          <div className="eval-tiles">
            {query.data.run.tiles.map((t) => (
              <div className="eval-tile" key={t.id}>
                <div className="row-between">
                  <span>{t.label}</span>
                  {t.passed ? (
                    <Check size={15} className="ok-text" />
                  ) : (
                    <ShieldQuestion size={15} className="crit-text" />
                  )}
                </div>
                <strong className={t.passed ? "" : "crit-text"}>
                  {t.display}
                </strong>
                <span className="meta">Target {t.target}</span>
              </div>
            ))}
          </div>
          <Panel
            title="Case results"
            action={
              <Badge>
                Models: {String(query.data.run.config.llm_provider || "none")}
              </Badge>
            }
          >
            <table className="data-table">
              <thead>
                <tr>
                  <th>Case</th>
                  <th>Suite</th>
                  <th>Input</th>
                  <th>Result</th>
                  <th>Expected / actual</th>
                </tr>
              </thead>
              <tbody>
                {query.data.run.results.map((r) => (
                  <tr key={r.case_id}>
                    <td>
                      <code>{r.case_id}</code>
                    </td>
                    <td>{r.suite}</td>
                    <td>
                      {typeof r.input === "string"
                        ? r.input
                        : JSON.stringify(r.input)}
                    </td>
                    <td>
                      <Badge tone={r.passed ? "ok" : "crit"}>
                        {r.passed ? "Pass" : "Fail"}
                      </Badge>
                    </td>
                    <td>
                      <details>
                        <summary>Compare</summary>
                        <pre>
                          Expected: {JSON.stringify(r.expected, null, 2)}
                          {"\n"}Actual: {JSON.stringify(r.actual, null, 2)}
                        </pre>
                      </details>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
          {MOCK && (
            <p className="meta">
              These are synthetic contract fixtures, not measured results from
              this frontend session.
            </p>
          )}
        </>
      )}
    </div>
  );
}
