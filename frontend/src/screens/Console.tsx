import { useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowDownLeft,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  Cpu,
  Radio,
  Send,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
} from "lucide-react";
import { api, mutate } from "@/api/client";
import { useConsole } from "@/realtime/store";
import { Badge, Empty, Panel } from "@/components/common";
import { Button } from "@/components/ui/button";
import { TerminalPane } from "@/components/terminal/TerminalPane";
import { MetricChart } from "@/components/charts/MetricChart";
import { CardRenderer, type Inspect } from "@/components/cards/CardRenderer";
import { AgentTrace } from "@/components/trace/AgentTrace";
import { InterruptPrompt } from "@/components/InterruptPrompt";
import { AnimatedNumber } from "@/components/AnimatedNumber";
import { cn } from "@/lib/utils";
import type { Schema } from "@/api/types";

export function Console({
  inspect,
  navigate,
}: {
  inspect: Inspect;
  navigate: (route: string) => void;
}) {
  return (
    <div className="console-grid">
      <TerminalPane />
      <HealthBoard inspect={inspect} navigate={navigate} />
      <BatonPanel inspect={inspect} navigate={navigate} />
    </div>
  );
}
export function HealthBoard({
  inspect,
  navigate,
}: {
  inspect: Inspect;
  navigate: (route: string) => void;
}) {
  const health = useConsole((s) => s.health);
  const values = useConsole((s) => s.values);
  const series = useConsole((s) => s.series);
  const episodes = useConsole((s) => s.episodes);
  const rate = useConsole((s) => s.eventRate);
  const total = useConsole((s) => s.rawTotal);
  const situations = useConsole((s) => s.situations);
  const incidents = useConsole((s) => s.incidents);
  const incident = incidents.at(-1);
  const active = incident && incident.status !== "resolved";
  const component = (id: string) => health?.components.find((c) => c.id === id);
  const metric = (key: string, fallback?: number) => values[key] ?? fallback;
  return (
    <section className="health-pane">
      <div className="pane-title">
        <span>
          <Activity size={15} /> System health
        </span>
        <Badge tone={active ? "crit" : "ok"}>
          <i className="dot" />
          {active ? "Needs attention" : `${Math.round(rate || 302)}/min`}
        </Badge>
      </div>
      <div className="health-scroll">
        <Panel
          title={
            <>
              <Cpu size={14} /> Processor utilization
            </>
          }
          action={
            <button
              className="meta link"
              onClick={() => inspect("metric:cpu.*.busy")}
            >
              8 CPUs <ArrowUpRight size={11} />
            </button>
          }
          className="cpu-panel"
        >
          <div className="cpu-bars">
            <div className="cpu-threshold" aria-label="90 percent threshold">
              <span>90%</span>
            </div>
            {Array.from({ length: 8 }, (_, n) => {
              const c = component(`cpu:${n}`);
              const busy = metric(`cpu.${n}.busy`, c?.metrics.busy) || 0;
              const down = values[`cpu.${n}.up`] === 0 || c?.state === "down";
              return (
                <button
                  key={n}
                  className={cn("cpu-column", down && "cpu-down")}
                  title={`${c?.name || `CPU ${n}`}: ${down ? "Down" : `${busy.toFixed(1)}% busy`}. ${c?.reasons.map((r) => r.text).join(". ") || "Within operating range"}`}
                  onClick={() => inspect(`metric:cpu.${n}.busy`)}
                >
                  <strong
                    className={
                      down ? "crit-text" : busy >= 90 ? "crit-text" : ""
                    }
                  >
                    {down ? "×" : `${Math.round(busy)}%`}
                  </strong>
                  <div className="cpu-track">
                    <div
                      className={cn(
                        "cpu-fill",
                        busy >= 90 ? "critical" : busy >= 75 ? "warning" : "",
                      )}
                      style={{ height: down ? "100%" : `${busy}%` }}
                    />
                  </div>
                  <span>{String(n).padStart(2, "0")}</span>
                </button>
              );
            })}
          </div>
          <button
            className="n1-banner"
            onClick={() => inspect("concept:n1-headroom")}
          >
            <TriangleAlert size={14} />
            <span>{health?.n1.text || "Calculating N-1 headroom…"}</span>
            <ChevronRight size={13} />
          </button>
        </Panel>
        <div className="service-grid">
          {(["atm", "pos"] as const).map((s) => {
            const c = component(`svc:${s}`);
            const p95 = metric(`svc.${s}.p95_ms`, c?.metrics.p95_ms);
            const low = metric(`svc.${s}.band_low`, c?.metrics.band_low) || 120;
            const high =
              metric(`svc.${s}.band_high`, c?.metrics.band_high) || 240;
            const good = p95 != null && p95 <= high;
            return (
              <div className="service-tile" key={s}>
                <button
                  className="service-head"
                  onClick={() => inspect(`metric:svc.${s}.p95_ms`)}
                >
                  <span>{s.toUpperCase()} authorization</span>
                  <ArrowUpRight size={11} />
                </button>
                <div className={cn("service-value", good ? "" : "crit-text")}>
                  <AnimatedNumber value={p95} />
                  <span>ms</span>
                </div>
                <div className="service-description">
                  <span>p95 latency</span>
                  {good ? (
                    <Check size={12} className="ok-text" />
                  ) : (
                    <ArrowUpRight size={12} className="crit-text" />
                  )}
                </div>
                <MetricChart
                  points={series[`svc.${s}.p95_ms`] || []}
                  band={[low, high]}
                  color={good ? "#3FB950" : "#F85149"}
                  height={65}
                />
                <div className="service-band">
                  <i className="band-key" />
                  Band {Math.round(low)}–{Math.round(high)} ms
                </div>
                <div className="service-tps">
                  <strong>
                    {Math.round(metric(`svc.${s}.tps`) || 0).toLocaleString()}
                  </strong>{" "}
                  transactions / s
                </div>
              </div>
            );
          })}
        </div>
        <Panel
          title="Server classes"
          action={
            <button
              className="meta link"
              onClick={() => inspect("concept:server-classes")}
            >
              Learn <ArrowUpRight size={11} />
            </button>
          }
          className="server-panel"
        >
          <table className="server-table">
            <thead>
              <tr>
                <th>Class</th>
                <th title="Running / maximum">Servers</th>
                <th>Queue</th>
                <th>Avg ms</th>
              </tr>
            </thead>
            <tbody>
              {["ATM-AUTH", "POS-AUTH", "BAL-INQ", "CARD-MGMT"].map((name) => {
                const c = component(`sc:${name}`);
                const running = metric(
                  `sc.${name}.running`,
                  c?.metrics.running,
                );
                const max = metric(`sc.${name}.max`, c?.metrics.max);
                const queue = metric(`sc.${name}.queued`, c?.metrics.queued);
                return (
                  <tr
                    key={name}
                    onClick={() => inspect(`sc:${name}`)}
                    tabIndex={0}
                    onKeyDown={(e) =>
                      e.key === "Enter" && inspect(`sc:${name}`)
                    }
                  >
                    <td>
                      <i className={cn("dot", queue ? "crit" : "ok")} />
                      <code>{name}</code>
                    </td>
                    <td>
                      {running ?? "—"}
                      <span className="muted"> / {max ?? "—"}</span>
                    </td>
                    <td className={queue ? "crit-text" : ""}>{queue ?? "—"}</td>
                    <td>
                      {metric(`sc.${name}.avg_ms`, c?.metrics.avg_ms)?.toFixed(
                        0,
                      ) || "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Panel>
        <Panel
          title={
            <>
              <ShieldCheck size={13} /> TMF audit trail
            </>
          }
          action={
            <button
              className="meta link"
              onClick={() => inspect("metric:tmf.mat.fill_pct")}
            >
              {Math.round(
                metric(
                  "tmf.mat.fill_pct",
                  component("tmf:mat")?.metrics.fill_pct,
                ) || 0,
              )}
              % <ArrowUpRight size={11} />
            </button>
          }
          className="audit-gauge-panel"
        >
          <div className="audit-gauge">
            <i
              style={{
                width: `${metric("tmf.mat.fill_pct", component("tmf:mat")?.metrics.fill_pct) || 0}%`,
              }}
            />
            <b style={{ left: "80%" }} />
            <b style={{ left: "90%" }} />
          </div>
          <div className="row-between meta">
            <span>Normal</span>
            <span>Overflow 80% · Stop new work 90%</span>
          </div>
        </Panel>
        <div className="situation-section">
          <div className="section-heading">
            <h2>
              Situations <span>{active ? 1 : 0}</span>
            </h2>
            <span className="meta">Correlated, in context</span>
          </div>
          {active ? (
            <button
              className="situation-alert"
              onClick={() => navigate("/incidents")}
            >
              <TriangleAlert size={18} />
              <div>
                <strong>{incident.title}</strong>
                <span>
                  {(
                    situations.find((s) => s.id === incident.situation_id)
                      ?.counts.raw_events || total
                  ).toLocaleString()}{" "}
                  events → 1 situation
                </span>
              </div>
              <ArrowRight size={16} />
            </button>
          ) : (
            <div className="healthy-situation">
              <ShieldCheck size={16} />
              <span>
                {incident?.status === "resolved"
                  ? "Incident resolved. Recovery verified."
                  : "No active situations. Services are within range."}
              </span>
            </div>
          )}
        </div>
        <div className="event-river">
          <div className="section-heading">
            <h2>
              <Radio size={13} /> Event river
            </h2>
            <span className="meta">
              <i className="dot ok" /> {Math.round(rate || 302)} / min
            </span>
          </div>
          {episodes.length ? (
            episodes
              .slice(-5)
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
                      "event-mark",
                      e.quarantined
                        ? "warn-text"
                        : e.critical
                          ? "crit-text"
                          : "ok-text",
                    )}
                  >
                    {e.quarantined ? (
                      <ShieldCheck size={12} />
                    ) : (
                      <ArrowDownLeft size={12} />
                    )}
                  </span>
                  <span>
                    <code>
                      {e.subsystem} {e.event_number}
                    </code>
                    <small>
                      {e.quarantined
                        ? "Quarantined · instruction-like text"
                        : e.example_text}
                    </small>
                  </span>
                  <Badge tone={e.quarantined ? "warn" : "neutral"}>
                    {e.quarantined ? "isolated" : `×${e.count}`}
                  </Badge>
                </button>
              ))
          ) : (
            <p className="meta river-empty">
              <Radio size={12} /> Listening for EMS episodes…
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
export function BatonPanel({
  inspect,
  navigate,
}: {
  inspect: Inspect;
  navigate: (route: string) => void;
}) {
  const allCards = useConsole((s) => s.cards);
  const threadId = useConsole((s) => s.threadId);
  const cards = allCards.filter(
    (c) => !c.thread_id || c.thread_id === threadId,
  );
  const incident = useConsole((s) => s.incidents.at(-1));
  const connected = useConsole((s) => s.connected);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [request, setRequest] = useState<{ text: string; name: string } | null>(
    null,
  );
  const feed = useRef<HTMLDivElement>(null);
  const follow = useRef(true);
  useEffect(() => {
    if (follow.current && feed.current)
      feed.current.scrollTop = feed.current.scrollHeight;
  }, [cards.length]);
  const send = async (value: string) => {
    if (!value.trim() || sending) return;
    setSending(true);
    const s = useConsole.getState();
    setRequest({
      text: value.trim(),
      name: s.users.find((u) => u.id === s.actor)?.name || s.actor,
    });
    try {
      let threadId = useConsole.getState().threadId;
      if (!threadId) {
        const t = await api<Schema<"Thread">>("/threads", { mode: "auto" });
        threadId = t.id;
        useConsole.setState({ threadId });
      }
      await mutate(`/threads/${threadId}/messages`, { text: value.trim() });
      setText("");
    } catch (e) {
      useConsole.setState({ error: (e as Error).message });
    } finally {
      setSending(false);
    }
  };
  return (
    <section className="baton-pane">
      <div className="pane-title">
        <span>
          <span className="baton-glyph mini">b</span> Baton{" "}
          <Badge tone="baton">Co-pilot</Badge>
        </span>
        <span className="meta">
          <i className={cn("dot", connected ? "ok" : "warn")} />
          {connected ? "Ready" : "Offline"}
        </span>
      </div>
      <div className="context-strip">
        <span className="dot baton" />
        {incident
          ? `${incident.display_id} · ${incident.status}`
          : "Watching \TORBANK"}
        <span className="meta">Live context</span>
      </div>
      <AgentTrace />
      <InterruptPrompt />
      {request && (
        <div className="last-request">
          <span>{request.name} asked</span>
          <p>{request.text}</p>
        </div>
      )}
      <div
        className="baton-feed"
        ref={feed}
        onScroll={() => {
          if (feed.current)
            follow.current =
              feed.current.scrollHeight -
                feed.current.clientHeight -
                feed.current.scrollTop <
              100;
        }}
      >
        {cards.length ? (
          cards.map((c) => (
            <CardRenderer
              key={c.id}
              card={c}
              inspect={inspect}
              navigate={navigate}
            />
          ))
        ) : (
          <div className="baton-welcome">
            <div className="welcome-mark">
              <span className="baton-glyph">b</span>
            </div>
            <p className="eyebrow">YOUR NEXT MOVE, WITH CONTEXT</p>
            <h2>Experience on your side.</h2>
            <p>
              Ask in plain language. Baton checks the system, connects the
              evidence, and brings your experts’ knowledge into the moment.
            </p>
            <div className="welcome-suggestions">
              <button
                disabled={!connected}
                onClick={() => void send("Is ATM auth keeping up?")}
              >
                <Activity size={15} />
                <span>
                  Is ATM auth keeping up?<small>Check live performance</small>
                </span>
                <ArrowRight size={14} />
              </button>
              <button
                disabled={!connected}
                onClick={() =>
                  void send(
                    "What's the difference between NUMSTATIC and MAXSERVERS?",
                  )
                }
              >
                <ShieldCheck size={15} />
                <span>
                  NUMSTATIC vs. MAXSERVERS<small>Understand a concept</small>
                </span>
                <ArrowRight size={14} />
              </button>
            </div>
            <div className="welcome-assurance">
              <ShieldCheck size={13} /> You stay in control. Every action is
              visible.
            </div>
          </div>
        )}
      </div>
      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          void send(text);
        }}
      >
        <div className="composer-context">
          <span className="dot baton" />{" "}
          {incident ? incident.display_id : "\TORBANK"}
          <span>Catalog commands · cited answers</span>
        </div>
        <div className="composer-input">
          <textarea
            rows={2}
            placeholder="Ask Baton about your system…"
            aria-label="Ask Baton"
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
            variant="default"
            size="icon"
            type="submit"
            disabled={!connected || !text.trim() || sending}
            aria-label="Send message"
          >
            <Send size={15} />
          </Button>
        </div>
        <div className="composer-footer">
          <span>
            {sending
              ? "Baton is gathering evidence…"
              : "Enter to send · Shift + Enter for new line"}
          </span>
          <kbd>↵</kbd>
        </div>
      </form>
    </section>
  );
}
