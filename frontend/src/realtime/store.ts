import { create } from "zustand";
import type {
  Approval,
  AuditRow,
  Card,
  Claim,
  Episode,
  Event,
  Health,
  Incident,
  Ledger,
  MetricPoint,
  Sim,
  TerminalEvent,
  Timeline,
  Trace,
  User,
  Schema,
} from "@/api/types";

export interface ConsoleState {
  actor: string;
  users: User[];
  connected: boolean;
  stale: boolean;
  error: string | null;
  readOnly: boolean;
  replay: string;
  sim: Sim | null;
  health: Health | null;
  values: Record<string, number>;
  series: Record<string, MetricPoint[]>;
  cards: Card[];
  cardSeq: Record<string, number>;
  trace: Trace[];
  traceThreads: Record<string, string>;
  traceSeq: Record<string, number>;
  incidents: Incident[];
  situations: Schema<"Situation">[];
  timeline: Timeline[];
  episodes: Episode[];
  approvals: Approval[];
  claims: Claim[];
  ledger: Ledger[];
  audit: AuditRow[];
  interrupts: Schema<"Interrupt">[];
  terminal: TerminalEvent[];
  terminalEpoch: number;
  threadId: string | null;
  rawTotal: number;
  eventRate: number;
  lastSeq: number;
  setActor: (id: string) => void;
  ingest: (event: Event) => void;
}
const upsert = <T>(items: T[], item: T, key: (t: T) => unknown): T[] => {
  const i = items.findIndex((t) => key(t) === key(item));
  return i < 0 ? [...items, item] : items.map((t, n) => (n === i ? item : t));
};
export const useConsole = create<ConsoleState>((set, get) => ({
  actor: "u_priya",
  users: [],
  connected: false,
  stale: false,
  error: null,
  readOnly: false,
  replay: "replay",
  sim: null,
  health: null,
  values: {},
  series: {},
  cards: [],
  cardSeq: {},
  trace: [],
  traceThreads: {},
  traceSeq: {},
  incidents: [],
  situations: [],
  timeline: [],
  episodes: [],
  approvals: [],
  claims: [],
  ledger: [],
  audit: [],
  terminal: [],
  terminalEpoch: 0,
  interrupts: [],
  threadId: null,
  rawTotal: 0,
  eventRate: 0,
  lastSeq: 0,
  setActor: (actor) => set({ actor }),
  ingest: (event) => {
    // Replay is globally ordered. Ignore duplicates on reconnect.
    const s = get();
    if (event.seq <= s.lastSeq) return;
    const p = event.payload;
    const patch: Partial<ConsoleState> = { lastSeq: event.seq, stale: false };
    switch (event.type) {
      case "sim.state":
        patch.sim = p as Sim;
        break;
      case "health.snapshot":
        patch.health = p as Health;
        break;
      case "telemetry.tick": {
        const tick = p as { sim_ts: string; values: Record<string, number> };
        patch.values = { ...s.values, ...tick.values };
        patch.series = { ...s.series };
        for (const [key, value] of Object.entries(tick.values))
          patch.series[key] = [
            ...(s.series[key] || []),
            [tick.sim_ts, value] as MetricPoint,
          ].slice(-360);
        break;
      }
      case "card.upsert":
        patch.cardSeq = { ...s.cardSeq, [(p as Card).id]: event.seq };
        patch.cards = upsert(s.cards, p as Card, (x) => x.id).sort(
          (a, b) => (a.seq || 0) - (b.seq || 0),
        );
        break;
      case "card.remove":
        patch.cardSeq = {
          ...s.cardSeq,
          [(p as { card_id: string }).card_id]: event.seq,
        };
        patch.cards = s.cards.filter(
          (x) => x.id !== (p as { card_id: string }).card_id,
        );
        break;
      case "node.started":
      case "node.ended":
        patch.traceSeq = {
          ...s.traceSeq,
          [`${(p as Trace).run_id}:${(p as Trace).step_id || (p as Trace).node}`]:
            event.seq,
        };
        patch.traceThreads = {
          ...s.traceThreads,
          [(p as Trace).run_id]: event.topic.slice(7),
        };
        patch.trace = upsert(
          s.trace,
          p as Trace,
          (x) => `${x.run_id}:${x.step_id || x.node}`,
        );
        break;
      case "incident.upsert": {
        const incident = p as Incident;
        patch.incidents = upsert(s.incidents, incident, (x) => x.id);
        patch.threadId = incident.thread_id;
        break;
      }
      case "situation.upsert":
        patch.situations = upsert(
          s.situations,
          p as Schema<"Situation">,
          (x) => x.id,
        );
        break;
      case "timeline.append":
        patch.timeline = upsert(
          s.timeline,
          (p as { item: Timeline }).item,
          (x) => x.id,
        ).slice(-500);
        break;
      case "episode.upsert":
        patch.episodes = upsert(s.episodes, p as Episode, (x) => x.id).slice(
          -100,
        );
        break;
      case "approval.upsert":
        patch.approvals = upsert(s.approvals, p as Approval, (x) => x.id);
        break;
      case "claim.upsert":
        patch.claims = upsert(s.claims, p as Claim, (x) => x.id);
        break;
      case "ledger.upsert":
        patch.ledger = upsert(s.ledger, p as Ledger, (x) => x.key);
        break;
      case "ledger.promotion_candidate":
        patch.ledger = upsert(
          s.ledger,
          (p as { entry: Ledger }).entry,
          (x) => x.key,
        );
        break;
      case "run.failed":
        patch.error = (p as { error: string }).error;
        break;
      case "interrupt.raised":
        patch.interrupts = upsert(
          s.interrupts,
          p as Schema<"Interrupt">,
          (x) => x.id,
        );
        break;
      case "interrupt.resolved":
        patch.interrupts = s.interrupts.filter(
          (x) => x.id !== (p as { interrupt_id: string }).interrupt_id,
        );
        break;
      case "audit.append":
        patch.audit = upsert(s.audit, p as AuditRow, (x) => x.seq).slice(-1000);
        break;
      case "events.rate":
        patch.rawTotal = (p as { raw_total: number }).raw_total;
        patch.eventRate = (p as { per_min: number }).per_min;
        break;
      default:
        if (event.type.startsWith("terminal."))
          patch.terminal = [...s.terminal, event as TerminalEvent].slice(-300);
    }
    set(patch);
  },
}));

export const resetRuntime = () =>
  useConsole.setState((state) => ({
    terminalEpoch: state.terminalEpoch + 1,
    cards: [],
    cardSeq: {},
    trace: [],
    traceThreads: {},
    traceSeq: {},
    incidents: [],
    situations: [],
    timeline: [],
    approvals: [],
    terminal: [],
    episodes: [],
    series: {},
    values: {},
    audit: [],
    threadId: null,
    interrupts: [],
  }));
