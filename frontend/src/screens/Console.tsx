import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  ChevronRight,
  CircleAlert,
  Copy,
  Maximize2,
  Minimize2,
  Radio,
  Send,
  ShieldCheck,
} from "lucide-react";
import { api, mutate } from "@/api/client";
import { useConsole } from "@/realtime/store";
import { Badge, Empty, ErrorState } from "@/components/common";
import { TabStrip } from "@/components/TabStrip";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { TerminalPane } from "@/components/terminal/TerminalPane";
import { MetricChart } from "@/components/charts/MetricChart";
import {
  ApprovalProgress,
  CardRenderer,
  type Inspect,
} from "@/components/cards/CardRenderer";
import { AgentTrace } from "@/components/trace/AgentTrace";
import { InterruptPrompt } from "@/components/InterruptPrompt";
import { AnimatedNumber } from "@/components/AnimatedNumber";
import { cn, human, time } from "@/lib/utils";
import type { Card, MetricPoint, Schema } from "@/api/types";

type Props = { inspect: Inspect; navigate: (route: string) => void };
type HealthTab = "Service health" | "Servers" | "Processors" | "Events";

export function Console({ inspect, navigate }: Props) {
  const incident = useConsole((s) => s.incidents.at(-1));
  const health = useConsole((s) => s.health);
  const timeline = useConsole((s) => s.timeline);
  const situations = useConsole((s) => s.situations);
  const [tab, setTab] = useState<HealthTab>("Service health");
  const [dockTab, setDockTab] = useState("Command workspace");
  const [expanded, setExpanded] = useState(false);
  const active = incident && incident.status !== "resolved";
  const unhealthy = health?.components.filter(
    (c) =>
      c.state === "down" || c.state === "critical" || c.state === "degraded",
  );
  return (
    <div className={cn("ops-console", expanded && "dock-expanded")}>
      <section className="ops-workspace" aria-label="Operations workspace">
        <div className="ops-main">
          <header className="ops-heading">
            <div className="ops-breadcrumb">
              Overview{" "}
              {incident && (
                <>
                  <span>/</span>
                  <button onClick={() => navigate("/incidents")}>
                    {incident.display_id}
                  </button>
                </>
              )}
            </div>
            <div className="row-between">
              <div>
                <h1>
                  {active
                    ? incident.title
                    : incident?.status === "resolved"
                      ? "Recovery verified. Services are stable."
                      : "Your services, at a glance."}
                </h1>
                <p>
                  {active
                    ? `${(situations.find((s) => s.id === incident.situation_id)?.counts.raw_events || 0).toLocaleString()} events → 1 situation. Follow the evidence and review the next step.`
                    : unhealthy?.length
                      ? `${unhealthy.length} components need attention. Open a diagnostic tab for details.`
                      : "Live service health and the tools for your next check."}
                </p>
              </div>
              {incident && (
                <button
                  className="text-action"
                  onClick={() => navigate("/incidents")}
                >
                  Open incident <ArrowRight size={15} />
                </button>
              )}
            </div>
          </header>
          <TabStrip
            label="System diagnostics"
            items={["Service health", "Servers", "Processors", "Events"]}
            value={tab}
            onChange={(t) => setTab(t as HealthTab)}
          />
          <div className="diagnostic-content" role="tabpanel" aria-label={tab}>
            {tab === "Service health" ? (
              <ServiceHealth inspect={inspect} navigate={navigate} />
            ) : tab === "Servers" ? (
              <ServerClasses inspect={inspect} />
            ) : tab === "Processors" ? (
              <SystemResources inspect={inspect} detailed />
            ) : (
              <EventRiver inspect={inspect} navigate={navigate} />
            )}
          </div>
        </div>
        <section className="working-dock" aria-label="Operator tools">
          <div className="dock-header">
            <TabStrip
              label="Operator tools"
              className="dock-tabs"
              items={["Command workspace", "Event stream", "Activity"]}
              value={dockTab}
              onChange={setDockTab}
            />
            <button
              className="dock-expand"
              onClick={() => setExpanded(!expanded)}
              aria-label={
                expanded
                  ? "Restore command workspace"
                  : "Expand command workspace"
              }
            >
              {expanded ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
              <span>{expanded ? "Restore" : "Expand"}</span>
            </button>
          </div>
          <div
            className="dock-content"
            hidden={dockTab !== "Command workspace"}
          >
            <TerminalPane />
          </div>
          {dockTab === "Event stream" && (
            <div className="dock-scroll">
              <EventRiver inspect={inspect} navigate={navigate} />
            </div>
          )}
          {dockTab === "Activity" && (
            <div className="dock-scroll">
              {timeline.length ? (
                <div className="activity-list">
                  {timeline
                    .slice(-30)
                    .reverse()
                    .map((t) => (
                      <button
                        key={t.id}
                        onClick={() => t.ref?.id && inspect(t.ref.id)}
                      >
                        <time>{time(t.sim_ts)}</time>
                        <span>
                          <strong>{t.title}</strong>
                          <small>
                            {t.actor.name} · {human(t.kind)}
                          </small>
                        </span>
                        <ChevronRight size={14} />
                      </button>
                    ))}
                </div>
              ) : (
                <Empty title="No incident activity yet">
                  Checks, approvals, actions and verification appear here in
                  simulated time.
                </Empty>
              )}
            </div>
          )}
        </section>
      </section>
      <BatonPanel inspect={inspect} navigate={navigate} />
    </div>
  );
}

function ServiceHealth({ inspect, navigate }: Props) {
  const health = useConsole((s) => s.health);
  const values = useConsole((s) => s.values);
  const live = useConsole((s) => s.series);
  const simTs = useConsole((s) => s.sim?.sim_ts);
  const timeline = useConsole((s) => s.timeline);
  const [service, setService] = useState("atm");
  const [windowS, setWindowS] = useState(900);
  const key = `svc.${service}.p95_ms`;
  const history = useQuery({
    queryKey: ["console-metric-window", key, windowS],
    queryFn: () =>
      api<Schema<"MetricsResponse">>(
        `/metrics?keys=${encodeURIComponent(key)}&window_s=${windowS}`,
      ),
  });
  const component = health?.components.find((c) => c.id === `svc:${service}`);
  const low = values[`svc.${service}.band_low`] ?? component?.metrics.band_low;
  const high =
    values[`svc.${service}.band_high`] ?? component?.metrics.band_high;
  const points = new Map<string, number>(
    history.data?.series.find((s) => s.key === key)?.points || [],
  );
  for (const [t, v] of live[key] || []) points.set(t, v);
  const cutoff = simTs ? Date.parse(simTs) - windowS * 1000 : 0;
  const chartPoints = [...points]
    .filter(([t]) => Date.parse(t) >= cutoff)
    .sort((a, b) => Date.parse(a[0]) - Date.parse(b[0])) as MetricPoint[];
  const good = component?.state === "ok";
  const markers = timeline
    .filter((t) => t.kind === "action_executed" || t.kind === "situation")
    .map((t) => ({
      time: t.sim_ts,
      label: t.kind === "situation" ? "Incident opened" : t.title,
    }));
  return (
    <>
      <div className="service-overview">
        {(["atm", "pos"] as const).map((s) => {
          const c = health?.components.find((c) => c.id === `svc:${s}`);
          const sc = s === "atm" ? "ATM-AUTH" : "POS-AUTH";
          const status = c?.state || "unknown";
          return (
            <button
              key={s}
              className={cn("service-row", service === s && "selected")}
              onClick={() => setService(s)}
              aria-label={`Inspect ${s === "atm" ? "ATM authorization" : "POS payments"}`}
            >
              <span
                className={cn(
                  "service-state-icon",
                  status === "ok"
                    ? "healthy"
                    : status === "unknown"
                      ? "unknown"
                      : "attention",
                )}
              >
                {status === "ok" ? (
                  <Check size={18} />
                ) : (
                  <CircleAlert size={18} />
                )}
              </span>
              <span className="service-identity">
                <strong>
                  {s === "atm" ? "ATM authorization" : "POS payments"}
                  <code>{sc}</code>
                </strong>
                <span className="service-facts">
                  <span>
                    <b>
                      {values[`sc.${sc}.running`] ?? "—"} /{" "}
                      {values[`sc.${sc}.max`] ?? "—"}
                    </b>{" "}
                    servers
                  </span>
                  <span>
                    <b>{values[`sc.${sc}.queued`] ?? "—"}</b> queued
                  </span>
                  <span>
                    <b>{values[`svc.${s}.timeout_pct`]?.toFixed(1) ?? "—"}%</b>{" "}
                    timeouts
                  </span>
                </span>
              </span>
              <span
                className={cn(
                  "service-state-label",
                  status === "ok" ? "ok-text" : "warn-text",
                )}
              >
                <i className={cn("dot", status === "ok" ? "ok" : "warn")} />
                {status === "ok" ? "Normal" : human(status)}
              </span>
              <span className="service-response">
                <strong>
                  <AnimatedNumber
                    value={values[`svc.${s}.p95_ms`] ?? c?.metrics.p95_ms}
                  />
                  <small> ms</small>
                </strong>
                <small>p95 response time</small>
              </span>
              <ChevronRight size={15} />
            </button>
          );
        })}
      </div>
      <section className="primary-chart" aria-label="Service response history">
        <header>
          <h2>{service.toUpperCase()} response time</h2>
          <div className="chart-tools">
            <div className="time-range" aria-label="Chart history window">
              {[
                [900, "15m"],
                [3600, "1h"],
                [14400, "4h"],
              ].map(([seconds, label]) => (
                <button
                  key={seconds}
                  aria-pressed={windowS === seconds}
                  onClick={() => setWindowS(Number(seconds))}
                >
                  {label}
                </button>
              ))}
            </div>
            <button
              className="text-action"
              onClick={() => inspect(`metric:${key}`)}
            >
              Source <ArrowUpRight size={12} />
            </button>
          </div>
        </header>
        {history.error && (
          <ErrorState
            message={history.error.message}
            retry={() => void history.refetch()}
          />
        )}
        <MetricChart
          points={chartPoints}
          band={low != null && high != null ? [low, high] : undefined}
          color={good ? "#39835c" : "#c88724"}
          axes
          height={140}
          markers={markers}
        />
        <div className="chart-caption">
          <span>
            <i className="expected-key" />
            Expected range
            {low != null && high != null
              ? ` ${Math.round(low)}–${Math.round(high)} ms`
              : " unavailable"}
          </span>
          <span>
            {history.isFetching ? "Loading history…" : "Live · simulated time"}
          </span>
        </div>
      </section>
      <SystemResources inspect={inspect} />
    </>
  );
}

function SystemResources({
  inspect,
  detailed = false,
}: {
  inspect: Inspect;
  detailed?: boolean;
}) {
  const health = useConsole((s) => s.health);
  const values = useConsole((s) => s.values);
  const fill =
    values["tmf.mat.fill_pct"] ??
    health?.components.find((c) => c.id === "tmf:mat")?.metrics.fill_pct;
  const tmf = health?.components.find((c) => c.id === "tmf:mat");
  return (
    <section
      className={cn("resource-overview", detailed && "resource-detailed")}
      aria-label="Processor and audit health"
    >
      <header>
        <h2>Processors</h2>
        <button
          className={cn(
            "resource-tmf",
            tmf?.state === "ok" ? "ok-text" : "warn-text",
          )}
          onClick={() => inspect("metric:tmf.mat.fill_pct")}
        >
          <ShieldCheck size={13} /> TMF audit trail{" "}
          {fill == null ? "—" : `${Math.round(fill)}%`} ·{" "}
          {tmf?.state === "ok" ? "Normal" : human(tmf?.state || "unknown")}
        </button>
      </header>
      <div className="processor-strip">
        {Array.from({ length: 8 }, (_, n) => {
          const c = health?.components.find((c) => c.id === `cpu:${n}`);
          const busy = values[`cpu.${n}.busy`] ?? c?.metrics.busy;
          const down = values[`cpu.${n}.up`] === 0 || c?.state === "down";
          return (
            <button
              key={n}
              className={cn(
                "processor",
                down ? "offline" : c?.state !== "ok" ? "attention" : "",
              )}
              onClick={() => inspect(`metric:cpu.${n}.busy`)}
              title={`${c?.name || `CPU ${n}`}: ${down ? "Offline" : busy == null ? "No measurement" : `${busy.toFixed(1)}% busy`}. ${c?.reasons.map((r) => r.text).join(". ") || ""}`}
            >
              <span className="processor-track">
                <i
                  style={{
                    height: down
                      ? "12%"
                      : `${Math.max(0, Math.min(100, busy || 0))}%`,
                  }}
                />
              </span>
              <span>CPU {n}</span>
              <small>
                {down
                  ? "Offline"
                  : detailed || c?.state !== "ok"
                    ? `${busy?.toFixed(0) ?? "—"}%`
                    : ""}
              </small>
            </button>
          );
        })}
      </div>
      <button
        className={cn(
          "headroom-note",
          health?.n1.safe ? "ok-text" : "warn-text",
        )}
        onClick={() => inspect("concept:n1-headroom")}
      >
        <CircleAlert size={13} />
        <span>{health?.n1.text || "Waiting for N-1 analysis…"}</span>
        <ChevronRight size={13} />
      </button>
      {detailed && (
        <>
          <div className="tmf-detail">
            <h3>TMF audit headroom</h3>
            <div className="audit-gauge">
              <i style={{ width: `${Math.min(100, fill || 0)}%` }} />
              <b style={{ left: "80%" }} />
              <b style={{ left: "90%" }} />
            </div>
            <p className="meta">Overflow threshold 80% · Stop new work 90%</p>
            <button
              className="text-action"
              onClick={() => inspect("metric:tmf.mat.fill_pct")}
            >
              Inspect audit trail <ArrowRight size={14} />
            </button>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Component</th>
                <th>Status</th>
                <th>Backend explanation</th>
              </tr>
            </thead>
            <tbody>
              {health?.components
                .filter(
                  (c) =>
                    c.type === "cpu" || c.type === "tmf" || c.type === "volume",
                )
                .map((c) => (
                  <tr key={c.id}>
                    <td>{c.name}</td>
                    <td>{human(c.state)}</td>
                    <td>
                      {c.reasons.map((r) => r.text).join(" · ") ||
                        "No active health rule"}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}

function ServerClasses({ inspect }: { inspect: Inspect }) {
  const health = useConsole((s) => s.health);
  const values = useConsole((s) => s.values);
  return (
    <section className="server-diagnostics">
      <div className="row-between">
        <h2>Server classes</h2>
        <button
          className="text-action"
          onClick={() => inspect("concept:server-classes")}
        >
          <BookOpen size={14} /> Explain server classes
        </button>
      </div>
      <p className="meta">
        Running capacity, queue depth and response time from the simulator.
      </p>
      <table className="data-table">
        <thead>
          <tr>
            <th>Class</th>
            <th>Health</th>
            <th>Running / max</th>
            <th>Queued</th>
            <th>Average response</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {health?.components
            .filter((c) => c.type === "server_class")
            .map((c) => {
              const name = c.id.replace(/^sc:/, "");
              const m = (key: string) =>
                values[`sc.${name}.${key}`] ?? c.metrics[key];
              return (
                <tr key={c.id}>
                  <td>
                    <button onClick={() => inspect(c.id)}>
                      <code>{name}</code>
                    </button>
                  </td>
                  <td>
                    <Badge tone={c.state === "ok" ? "ok" : "warn"}>
                      {human(c.state)}
                    </Badge>
                  </td>
                  <td>
                    {m("running") ?? "—"} / {m("max") ?? "—"}
                  </td>
                  <td>{m("queued") ?? "—"}</td>
                  <td>{m("avg_ms")?.toFixed(0) ?? "—"} ms</td>
                  <td>
                    <button
                      className="text-action"
                      onClick={() => inspect(c.id)}
                      aria-label={`Inspect ${name}`}
                    >
                      <ArrowUpRight size={15} />
                    </button>
                  </td>
                </tr>
              );
            })}
        </tbody>
      </table>
    </section>
  );
}

function SituationSummary({ navigate }: Props) {
  const situations = useConsole((s) => s.situations);
  const incident = useConsole((s) => s.incidents.at(-1));
  const total = useConsole((s) => s.rawTotal);
  const active = incident && incident.status !== "resolved";
  const count =
    situations.find((s) => s.id === incident?.situation_id)?.counts
      .raw_events ?? total;
  return (
    <button
      className={cn("situation-summary", active && "active")}
      onClick={() => navigate("/incidents")}
    >
      <span>
        {active ? <CircleAlert size={15} /> : <ShieldCheck size={15} />}
        <strong>
          {active
            ? `${count.toLocaleString()} events → 1 situation`
            : incident
              ? "Recovery verified"
              : "No active situations"}
        </strong>
        <small>
          {active
            ? "Open the correlated evidence"
            : "The system is being monitored"}
        </small>
      </span>
      <ArrowRight size={15} />
    </button>
  );
}

function EventRiver({ inspect, navigate }: Props) {
  const episodes = useConsole((s) => s.episodes);
  const total = useConsole((s) => s.rawTotal);
  const rate = useConsole((s) => s.eventRate);
  const [filter, setFilter] = useState("all");
  const visible = episodes.filter(
    (e) =>
      filter === "all" ||
      (filter === "quarantined" ? e.quarantined : e.critical),
  );
  return (
    <section className="episode-workspace">
      <header className="row-between">
        <div>
          <h2>
            Event stream{" "}
            <span className="meta">
              {Math.round(rate).toLocaleString()} / min
            </span>
          </h2>
          <p className="meta">
            {total.toLocaleString()} events grouped into {episodes.length}{" "}
            episodes
          </p>
        </div>
        <select
          aria-label="Filter event stream"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="all">All episodes</option>
          <option value="critical">Critical</option>
          <option value="quarantined">Quarantined</option>
        </select>
      </header>
      <SituationSummary inspect={inspect} navigate={navigate} />
      {visible.length ? (
        <div className="episode-list">
          {visible
            .slice()
            .reverse()
            .map((e) => (
              <button
                key={e.id}
                onClick={() =>
                  inspect(`opmsg:${e.subsystem}:${e.event_number}`)
                }
              >
                <span
                  className={cn(
                    "episode-icon",
                    e.quarantined
                      ? "warn-text"
                      : e.critical
                        ? "crit-text"
                        : "muted",
                  )}
                >
                  {e.quarantined ? (
                    <ShieldCheck size={16} />
                  ) : (
                    <Radio size={16} />
                  )}
                </span>
                <span>
                  <strong>
                    <code>
                      {e.subsystem} {e.event_number}
                    </code>
                    <small>
                      {e.quarantined
                        ? "Quarantined · instruction-like text"
                        : `Severity ${e.severity}`}
                    </small>
                  </strong>
                  <p>{e.example_text}</p>
                </span>
                <Badge tone={e.quarantined ? "warn" : "neutral"}>
                  ×{e.count.toLocaleString()}
                </Badge>
                <ChevronRight size={14} />
              </button>
            ))}
        </div>
      ) : (
        <Empty
          title={
            filter === "all"
              ? "Listening for EMS episodes"
              : "No matching episodes"
          }
        >
          Event counts update on the SIM clock. Quarantined text is never used
          as an instruction.
        </Empty>
      )}
    </section>
  );
}

export function BatonPanel({ inspect, navigate }: Props) {
  const allCards = useConsole((s) => s.cards);
  const threadId = useConsole((s) => s.threadId);
  const incident = useConsole((s) => s.incidents.at(-1));
  const connected = useConsole((s) => s.connected);
  const approvals = useConsole((s) => s.approvals);
  const trace = useConsole((s) => s.trace);
  const cards = allCards.filter(
    (c) => !c.thread_id || c.thread_id === threadId,
  );
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [history, setHistory] = useState(false);
  const [request, setRequest] = useState<string | null>(null);
  // Surface the unresolved human task; all earlier cards remain inspectable in order.
  const pending = cards
    .filter(
      (c) =>
        (c.type === "command" || c.type === "plan") &&
        [
          "awaiting_approval",
          "partially_approved",
          "running",
          "auto_running",
        ].includes(c.status),
    )
    .at(-1);
  const decision = cards.filter((c) => c.type === "decision").at(-1) as
    Schema<"DecisionCard"> | undefined;
  const latest = cards.at(-1);
  const focus: Card | undefined = pending || latest;
  const reviewCount = cards.filter((c) =>
    ["awaiting_approval", "partially_approved"].includes(c.status),
  ).length;
  const send = async (value: string) => {
    if (!value.trim() || sending || !connected) return;
    setSending(true);
    setRequest(value.trim());
    try {
      let id = useConsole.getState().threadId;
      if (!id) {
        const thread = await api<Schema<"Thread">>("/threads", {
          mode: "auto",
        });
        id = thread.id;
        useConsole.setState({ threadId: id });
      }
      await mutate(`/threads/${id}/messages`, { text: value.trim() });
      setText("");
    } catch (e) {
      useConsole.setState({ error: (e as Error).message });
    } finally {
      setSending(false);
    }
  };
  return (
    <aside className="baton-pane" aria-label="Baton assistant">
      <header className="assistant-header">
        <h2>
          <span className="baton-glyph mini">b</span> Baton
        </h2>
        <span className="meta">
          <i className={cn("dot", connected ? "ok" : "warn")} />
          {connected ? "Ready" : "Offline"}
        </span>
      </header>
      <div className="assistant-content">
        <InterruptPrompt />
        {reviewCount > 1 && (
          <button
            className="review-queue-link"
            onClick={() => setHistory(true)}
          >
            {reviewCount} items need your review <ArrowRight size={13} />
          </button>
        )}
        {approvals
          .filter(
            (a) =>
              a.status === "partially_approved" && a.thread_id === threadId,
          )
          .map((a) => (
            <ApprovalProgress key={a.id} approval={a} />
          ))}
        {request && (
          <div className="request-context">
            <small>Your request</small>
            <p>{request}</p>
          </div>
        )}
        {focus ? (
          focus.type === "decision" ? (
            <DecisionPreview
              card={focus}
              cards={cards}
              navigate={navigate}
              inspect={inspect}
            />
          ) : (
            <CardRenderer card={focus} inspect={inspect} navigate={navigate} />
          )
        ) : (
          <div className="assistant-idle">
            <span className="meta">
              {incident && incident.status !== "resolved"
                ? "Following the incident"
                : "Connected to your system"}
            </span>
            <h2>
              {incident && incident.status !== "resolved"
                ? "Gathering the evidence."
                : "Ready for your next check."}
            </h2>
            <p>
              {incident && incident.status !== "resolved"
                ? "Checks and recommendations appear here as Baton investigates. You can follow each step in the trace."
                : "Ask a question, check a service, or look up a command. Baton will show its sources and ask before running a gated action."}
            </p>
            <div className="quiet-prompts">
              <button
                disabled={!connected || sending}
                onClick={() => void send("Is ATM auth keeping up?")}
              >
                Is ATM auth keeping up? <ArrowRight size={14} />
              </button>
              <button
                disabled={!connected || sending}
                onClick={() =>
                  void send(
                    "What's the difference between NUMSTATIC and MAXSERVERS?",
                  )
                }
              >
                NUMSTATIC vs. MAXSERVERS <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}
        {cards.length > 0 && (
          <button className="history-link" onClick={() => setHistory(true)}>
            <Copy size={13} /> View all {cards.length} cards{" "}
            <ArrowRight size={13} />
          </button>
        )}
        {decision &&
          focus?.id !== decision.id &&
          incident?.status !== "resolved" && (
            <button
              className="history-link"
              onClick={() => navigate("/incidents")}
            >
              Recovery plan & approvals <ArrowRight size={13} />
            </button>
          )}
      </div>
      <div className="assistant-bottom">
        {trace.length > 0 && <AgentTrace />}
        <div className="assistant-links">
          <button
            disabled={!focus?.citations?.length}
            onClick={() =>
              focus?.citations?.[0] && inspect(focus.citations[0].id)
            }
          >
            <BookOpen size={13} /> Sources
          </button>
          <button onClick={() => navigate("/audit")}>
            <ShieldCheck size={13} /> Audit trail <ArrowRight size={12} />
          </button>
        </div>
        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            void send(text);
          }}
        >
          <div className="composer-input">
            <textarea
              rows={2}
              aria-label="Ask Baton"
              placeholder="Ask Baton or explain a command…"
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void send(text);
                }
              }}
            />
            <Button
              type="submit"
              size="icon"
              variant="default"
              disabled={!connected || !text.trim() || sending}
              aria-label="Send message"
            >
              <Send size={16} />
            </Button>
          </div>
          <div className="composer-footer">
            <span>
              {sending
                ? "Gathering evidence…"
                : "Nothing runs without the required approval."}
            </span>
          </div>
        </form>
      </div>
      <Dialog
        open={history}
        onOpenChange={setHistory}
        title="Conversation & investigation"
        description="All cards in this thread, in their original order. Sources and policy explanations remain available."
        drawer
      >
        <div className="conversation-history">
          {cards.map((c) => (
            <CardRenderer
              key={c.id}
              card={c}
              inspect={inspect}
              navigate={navigate}
            />
          ))}
        </div>
      </Dialog>
    </aside>
  );
}

function DecisionPreview({
  card,
  cards,
  navigate,
  inspect,
}: {
  card: Schema<"DecisionCard">;
  cards: Card[];
  navigate: Props["navigate"];
  inspect: Inspect;
}) {
  const recommended = card.body.options.find((o) => o.recommended);
  const steps = recommended?.steps || [];
  const expert = cards.find((c) => c.type === "expert") as
    Schema<"ExpertCard"> | undefined;
  return (
    <section className="recovery-preview">
      <div className="investigation-status">
        <Check size={15} /> Recovery options ready{" "}
        <button onClick={() => navigate("/incidents")}>
          View evidence <ArrowRight size={12} />
        </button>
      </div>
      {card.source && (
        <span className="meta decision-source">Source: {card.source}</span>
      )}
      <h2>Recover service capacity</h2>
      <p>
        {recommended
          ? recommended.expected_effect
          : "Review the available actions and their supporting evidence."}
      </p>
      <ol className="recovery-steps">
        {steps.map((step, i) => (
          <li key={`${step.catalog_id}:${i}`}>
            <span>{i + 1}</span>
            <div>
              <code>{step.rendered}</code>
              <small>
                {card.body.options.find(
                  (o) =>
                    o.steps.length === 1 &&
                    o.steps[0].catalog_id === step.catalog_id,
                )?.required_approvers === 2
                  ? "Two distinct approvers required"
                  : `${step.tier} · review before execution`}
              </small>
            </div>
            <ChevronRight size={14} />
          </li>
        ))}
      </ol>
      {expert && (
        <button
          className="preview-provenance"
          onClick={() => inspect(expert.citations?.[0]?.id || expert.body.id)}
        >
          <BookOpen size={18} />
          <span>
            {expert.body.author.name}’s playbook · verified by{" "}
            {expert.body.verified_by.map((p) => p.name).join(", ")} · v
            {expert.body.version}
          </span>
          <ArrowUpRight size={13} />
        </button>
      )}
      <Button
        variant="default"
        className="full-width"
        onClick={() => navigate("/incidents")}
      >
        Review plan & approvals <ArrowRight size={15} />
      </Button>
      <button
        className="compare-options"
        onClick={() => navigate("/incidents")}
      >
        Compare options, risks & undo
      </button>
      <p className="meta">Nothing runs without the required approval.</p>
    </section>
  );
}
