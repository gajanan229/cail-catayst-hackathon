import { useState } from "react";
import {
  ArrowLeft,
  Check,
  Clock3,
  FileText,
  Filter,
  Undo2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api, mutate } from "@/api/client";
import { useConsole } from "@/realtime/store";
import {
  Badge,
  Empty,
  Panel,
  Loading,
  ErrorState,
  ActorStamp,
  Why,
  Tier,
} from "@/components/common";
import {
  ApprovalProgress,
  CardRenderer,
  type Inspect,
} from "@/components/cards/CardRenderer";
import { AgentTrace } from "@/components/trace/AgentTrace";
import { MetricChart } from "@/components/charts/MetricChart";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { human, time } from "@/lib/utils";
import type { Approval, Schema } from "@/api/types";
import { SafeMarkdown } from "@/components/Markdown";
import { TabStrip } from "@/components/TabStrip";

export function IncidentScreen({
  inspect,
  navigate,
}: {
  inspect: Inspect;
  navigate: (route: string) => void;
}) {
  const approvals = useConsole((s) => s.approvals);
  const incidents = useConsole((s) => s.incidents);
  const allCards = useConsole((s) => s.cards);
  const timeline = useConsole((s) => s.timeline);
  const series = useConsole((s) => s.series);
  const values = useConsole((s) => s.values);
  const simTs = useConsole((s) => s.sim?.sim_ts);
  const readOnly = useConsole((s) => s.readOnly);
  const connected = useConsole((s) => s.connected);
  const [undoBusy, setUndoBusy] = useState(false);
  const [filter, setFilter] = useState("all");
  const [investigationTab, setInvestigationTab] = useState("Diagnosis");
  const [tab, setTab] = useState(
    new URLSearchParams(location.search).get("tab") || "overview",
  );
  const [undo, setUndo] = useState<Schema<"UndoEntry"> | null>(null);
  const incident = incidents.at(-1);
  const cards = allCards.filter(
    (c) =>
      c.thread_id === incident?.thread_id || c.incident_id === incident?.id,
  );
  const postmortem = useQuery({
    queryKey: ["postmortem", incident?.id],
    queryFn: () =>
      api<Schema<"PostmortemResponse">>(
        `/incidents/${incident!.id}/postmortem`,
      ),
    enabled: !!incident && tab === "postmortem",
  });
  if (!incident)
    return (
      <div className="page-content">
        <PageHeading
          eyebrow="OPERATIONS / INCIDENTS"
          title="Incident Room"
          description="One shared picture, from the first signal to recovery."
        />
        <Panel title="Active incidents">
          <Empty title="No active incidents">
            A correlated critical situation opens an incident automatically. Use
            Director to rehearse the CPU loss scenario.
          </Empty>
        </Panel>
      </div>
    );
  const find = (type: string) => cards.filter((c) => c.type === type);
  const markers = timeline
    .filter((t) => t.kind === "action_executed" || t.kind === "undo")
    .map((t) => ({ time: t.sim_ts, label: t.title }));
  return (
    <div className="incident-screen">
      <div className="incident-heading">
        <div>
          <div className="eyebrow">
            <button onClick={() => navigate("/console")}>
              <ArrowLeft size={11} /> CONSOLE
            </button>
            <span>/</span>
            <code>{incident.display_id}</code>
          </div>
          <h1>{incident.title}</h1>
          <p>
            ATM authorization <span>·</span> Peak p95{" "}
            {incident.impact.p95_ms_peak == null
              ? "awaiting measurement"
              : `${Math.round(incident.impact.p95_ms_peak)} ms`}{" "}
            <span>·</span> Opened {time(incident.opened_at)} SIM
            {simTs && (
              <>
                {" "}
                <span>·</span>{" "}
                {Math.max(
                  0,
                  Math.floor(
                    (Date.parse(incident.resolved_at || simTs) -
                      Date.parse(incident.opened_at)) /
                      60000,
                  ),
                )}{" "}
                min elapsed
              </>
            )}
          </p>
        </div>
        <div className="inline-gap">
          <Badge tone={incident.status === "resolved" ? "ok" : "crit"}>
            {incident.status === "resolved" ? (
              <Check size={12} />
            ) : (
              <Clock3 size={12} />
            )}{" "}
            {human(incident.status)}
          </Badge>
          <Badge>Severity {incident.severity}</Badge>
        </div>
      </div>
      <div className="tabs">
        <button
          className={tab === "overview" ? "active" : ""}
          onClick={() => setTab("overview")}
        >
          Overview
        </button>
        <button
          className={tab === "postmortem" ? "active" : ""}
          onClick={() => setTab("postmortem")}
        >
          Postmortem{" "}
          {incident.status === "resolved" && <i className="dot ok" />}
        </button>
      </div>
      {tab === "postmortem" ? (
        <div className="postmortem-view">
          <Panel
            title="Incident postmortem"
            action={<Badge>Draft · expert review required</Badge>}
          >
            {postmortem.isPending ? (
              <Loading />
            ) : postmortem.error ? (
              <ErrorState
                message={postmortem.error.message}
                retry={() => void postmortem.refetch()}
              />
            ) : (
              <Postmortem data={postmortem.data} />
            )}
          </Panel>
        </div>
      ) : (
        <>
          <div className="incident-grid">
            <Panel
              title="Timeline"
              subtitle="Every step, in simulated time"
              className="timeline-panel"
              action={<Filter size={13} className="muted" />}
            >
              <select
                className="timeline-filter"
                aria-label="Filter timeline"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              >
                {[
                  "all",
                  "events",
                  "check",
                  "approval",
                  "action",
                  "verification",
                  "note",
                ].map((f) => (
                  <option key={f} value={f}>
                    {f === "all" ? "All activity" : human(f)}
                  </option>
                ))}
              </select>
              <div className="timeline-list">
                {timeline
                  .filter(
                    (t) =>
                      filter === "all" ||
                      (filter === "events"
                        ? ["situation", "episode"].includes(t.kind)
                        : t.kind.includes(filter)),
                  )
                  .map((t) => (
                    <button
                      className="timeline-item"
                      key={t.id}
                      onClick={() => t.ref?.id && inspect(t.ref.id)}
                    >
                      <time>{time(t.sim_ts)}</time>
                      <i className={`timeline-dot kind-${t.kind}`} />
                      <span>
                        <strong>{t.title}</strong>
                        <small>
                          {t.actor.name} · {human(t.kind)}
                        </small>
                      </span>
                    </button>
                  ))}
              </div>
            </Panel>
            <div className="incident-centre">
              <TabStrip
                label="Investigation detail"
                className="investigation-tabs"
                items={["Diagnosis", "Steps", "Evidence", "Playbook"]}
                value={investigationTab}
                onChange={setInvestigationTab}
              />
              {investigationTab === "Diagnosis" && (
                <div role="tabpanel" aria-label="Diagnosis">
                  {find("hypotheses").map((c) => (
                    <CardRenderer
                      key={c.id}
                      card={c}
                      inspect={inspect}
                      navigate={navigate}
                    />
                  ))}
                  {!find("hypotheses").length && (
                    <Empty title="Building the diagnosis">
                      Hypotheses appear as evidence arrives. Follow the live
                      checks in Steps.
                    </Empty>
                  )}
                  <button
                    className="text-action investigation-next"
                    onClick={() => setInvestigationTab("Playbook")}
                    disabled={!find("expert").length}
                  >
                    <FileText size={13} />{" "}
                    {find("expert").length
                      ? "Expert playbook available"
                      : "Looking for expert guidance"}
                  </button>
                </div>
              )}
              {investigationTab === "Steps" && (
                <div role="tabpanel" aria-label="Steps">
                  <AgentTrace full threadId={incident.thread_id} />
                </div>
              )}
              {investigationTab === "Playbook" && (
                <div role="tabpanel" aria-label="Playbook">
                  {find("expert").map((c) => (
                    <CardRenderer
                      key={c.id}
                      card={c}
                      inspect={inspect}
                      navigate={navigate}
                    />
                  ))}
                  {!find("expert").length && (
                    <Empty title="No playbook selected yet">
                      Verified guidance appears here when the investigation
                      finds a relevant source.
                    </Empty>
                  )}
                </div>
              )}
              {investigationTab === "Evidence" && (
                <div role="tabpanel" aria-label="Evidence">
                  {find("evidence").map((c) => (
                    <CardRenderer
                      key={c.id}
                      card={c}
                      inspect={inspect}
                      navigate={navigate}
                    />
                  ))}
                  {find("command").map((c) => (
                    <CardRenderer
                      key={c.id}
                      card={c}
                      inspect={inspect}
                      navigate={navigate}
                    />
                  ))}
                  {!find("evidence").length && !find("command").length && (
                    <Empty title="Waiting for evidence">
                      Telemetry, command output and cited sources appear here.
                    </Empty>
                  )}
                </div>
              )}
            </div>
            <div className="incident-decisions">
              {approvals
                .filter(
                  (a) =>
                    a.incident_id === incident.id &&
                    !a.card_id &&
                    !a.option_ids.length &&
                    ["pending", "partially_approved"].includes(a.status) &&
                    incident.undo_stack.some((u) =>
                      a.rendered.includes(u.rendered),
                    ),
                )
                .map((a) => (
                  <PendingUndoApproval key={a.id} approval={a} />
                ))}
              {approvals
                .filter(
                  (a) =>
                    a.incident_id === incident.id &&
                    a.status === "partially_approved",
                )
                .map((a) => (
                  <div className="sticky-approval" key={a.id}>
                    <ApprovalProgress approval={a} />
                  </div>
                ))}
              {[
                ...find("command").filter(
                  (c) =>
                    c.status === "awaiting_approval" ||
                    c.status === "partially_approved",
                ),
                ...find("decision"),
                ...find("verification"),
              ].map((c) => (
                <CardRenderer
                  key={c.id}
                  card={c}
                  inspect={inspect}
                  navigate={navigate}
                />
              ))}
              <Panel
                title={
                  <>
                    <Undo2 size={14} /> Undo stack
                  </>
                }
              >
                {incident.undo_stack.length ? (
                  incident.undo_stack.map((u) => (
                    <div className="undo-entry" key={u.id}>
                      <code>{u.rendered}</code>
                      <Badge tone={u.status === "applied" ? "ok" : "neutral"}>
                        {u.status}
                      </Badge>
                      <Button
                        size="sm"
                        disabled={
                          readOnly || !connected || u.status !== "pending"
                        }
                        onClick={() => setUndo(u)}
                      >
                        Undo
                      </Button>
                    </div>
                  ))
                ) : (
                  <p className="muted">
                    Reversible actions appear here after execution.
                  </p>
                )}
              </Panel>
            </div>
          </div>
          <div className="incident-charts">
            <Panel
              title="ATM authorization · p95 latency"
              action={<Badge tone="ok">Baseline band</Badge>}
            >
              <MetricChart
                points={series["svc.atm.p95_ms"] || []}
                band={
                  values["svc.atm.band_low"] != null &&
                  values["svc.atm.band_high"] != null
                    ? [values["svc.atm.band_low"], values["svc.atm.band_high"]]
                    : undefined
                }
                color="#7662a1"
                height={165}
                axes
                markers={markers}
              />
            </Panel>
            <Panel
              title="CPU 5 · utilization"
              action={<Badge>Threshold 90%</Badge>}
            >
              <MetricChart
                points={series["cpu.5.busy"] || []}
                color="#b8832d"
                height={165}
                axes
                markers={markers}
              />
            </Panel>
          </div>
        </>
      )}
      <Dialog
        open={!!undo}
        onOpenChange={(o) => !o && setUndo(null)}
        title="Propose undo"
        description="Undo follows the same backend policy and approval rules as any other action."
      >
        <ActorStamp />
        <code className="command-code">{undo?.rendered}</code>
        <p>
          Risk: temporary mitigation will be reversed. The backend revalidates
          current state before execution.
        </p>
        <div className="dialog-actions">
          <Button onClick={() => setUndo(null)}>Cancel</Button>
          <Button
            variant="default"
            disabled={readOnly || !connected || undoBusy}
            onClick={() => {
              setUndoBusy(true);
              void mutate(`/executions/${undo!.execution_id}/undo`)
                .then(() => setUndo(null))
                .catch(() => {})
                .finally(() => setUndoBusy(false));
            }}
          >
            {undoBusy ? "Checking policy…" : "Submit undo for policy check"}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
function PendingUndoApproval({ approval }: { approval: Approval }) {
  const connected = useConsole((s) => s.connected);
  const readOnly = useConsole((s) => s.readOnly);
  const [decision, setDecision] = useState<"approve" | "reject" | null>(null);
  const [reason, setReason] = useState("unsafe_now");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <section
      className="baton-card undo-approval"
      aria-label="Pending undo approval"
    >
      <div className="row-between">
        <h3>Undo awaiting approval</h3>
        <Tier tier={approval.tier} />
      </div>
      {approval.rendered.map((command) => (
        <code className="command-code" key={command}>
          {command}
        </code>
      ))}
      <p className="meta">
        Reverses a previous mitigation. Review the current service impact before
        continuing.
      </p>
      <ApprovalProgress approval={approval} />
      <Why
        explanation={approval.policy.explanation}
        rules={approval.policy.rule_ids}
      />
      <div className="card-actions">
        <Button
          variant="default"
          disabled={!connected || readOnly}
          onClick={() => {
            setDecision("approve");
            setError("");
          }}
        >
          Review undo approval
        </Button>
        <Button
          disabled={!connected}
          onClick={() => {
            setDecision("reject");
            setError("");
          }}
        >
          Reject
        </Button>
      </div>
      {readOnly && (
        <p className="warn-text">Read-only mode prevents changes.</p>
      )}
      <Dialog
        open={!!decision}
        onOpenChange={(open) => !open && setDecision(null)}
        title={decision === "reject" ? "Reject undo" : "Confirm undo approval"}
        description="The backend checks the acting persona and all required approvals before executing."
      >
        <ActorStamp />
        {approval.rendered.map((command) => (
          <code className="command-code" key={command}>
            {command}
          </code>
        ))}
        <p>
          <strong>Risk:</strong> Reversing the mitigation may restore the
          earlier load or capacity limit.
        </p>
        <p>
          <strong>Undo:</strong> Reapplying the original mitigation requires a
          new governed action.
        </p>
        <ApprovalProgress approval={approval} />
        {decision === "reject" && (
          <label>
            Reason code
            <select value={reason} onChange={(e) => setReason(e.target.value)}>
              <option value="unsafe_now">Unsafe now</option>
              <option value="wrong_command">Wrong command</option>
              <option value="wrong_target">Wrong target</option>
              <option value="not_needed">Not needed</option>
              <option value="other">Other</option>
            </select>
          </label>
        )}
        {error && (
          <p role="alert" className="crit-text">
            {error}
          </p>
        )}
        <div className="dialog-actions">
          <Button onClick={() => setDecision(null)}>Cancel</Button>
          <Button
            variant="default"
            disabled={
              busy || !connected || (decision === "approve" && readOnly)
            }
            onClick={async () => {
              setBusy(true);
              try {
                await mutate(`/approvals/${approval.id}/decide`, {
                  decision,
                  ...(decision === "reject" ? { reason_code: reason } : {}),
                });
                setDecision(null);
              } catch (e) {
                setError((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            {busy
              ? "Recording…"
              : decision === "reject"
                ? "Record rejection"
                : "Confirm undo approval"}
          </Button>
        </div>
      </Dialog>
    </section>
  );
}
export function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
function Postmortem({ data }: { data: unknown }) {
  if (!data) return <Empty title="Postmortem will appear after recovery" />;
  const record = data as Record<string, unknown>;
  const content = (record.postmortem || record) as Record<string, unknown>;
  return (
    <div className="postmortem-document">
      {Object.entries(content)
        .filter(
          ([key]) =>
            !["incident_id", "generated_by", "source", "id"].includes(key),
        )
        .map(([key, value]) => (
          <section key={key}>
            <h2>{human(key)}</h2>
            {typeof value === "string" ? (
              <SafeMarkdown>{value}</SafeMarkdown>
            ) : Array.isArray(value) ? (
              <ul>
                {value.map((item, i) => (
                  <li key={i}>
                    {typeof item === "string" ? item : JSON.stringify(item)}
                  </li>
                ))}
              </ul>
            ) : (
              <pre>{JSON.stringify(value, null, 2)}</pre>
            )}
          </section>
        ))}
    </div>
  );
}
