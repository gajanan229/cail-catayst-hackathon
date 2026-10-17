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
import type { Schema } from "@/api/types";
import { SafeMarkdown } from "@/components/Markdown";

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
  const readOnly = useConsole((s) => s.readOnly);
  const [filter, setFilter] = useState("all");
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
              {find("hypotheses").map((c) => (
                <CardRenderer
                  key={c.id}
                  card={c}
                  inspect={inspect}
                  navigate={navigate}
                />
              ))}
              <AgentTrace full />
              {find("expert").map((c) => (
                <CardRenderer
                  key={c.id}
                  card={c}
                  inspect={inspect}
                  navigate={navigate}
                />
              ))}
              {find("evidence").map((c) => (
                <CardRenderer
                  key={c.id}
                  card={c}
                  inspect={inspect}
                  navigate={navigate}
                />
              ))}
            </div>
            <div className="incident-decisions">
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
                        disabled={readOnly || u.status !== "pending"}
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
                band={[137, 240]}
                color="#58A6FF"
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
                color="#D29922"
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
            disabled={readOnly}
            onClick={() => {
              void mutate(`/executions/${undo!.execution_id}/undo`)
                .then(() => setUndo(null))
                .catch(() => {});
            }}
          >
            Submit undo for policy check
          </Button>
        </div>
      </Dialog>
    </div>
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
