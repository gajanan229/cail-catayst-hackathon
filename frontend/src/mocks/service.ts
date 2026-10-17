/** Contract-derived rehearsal transport. This file is the only source of mock behavior. */
import { resetRuntime, useConsole } from "@/realtime/store";
import type {
  Approval,
  AuditRow,
  Card,
  Event,
  Incident,
  Schema,
  Timeline,
  Trace,
} from "@/api/types";
import content from "./content.json";
import recorded from "./recorded-fixtures.json";

const files = import.meta.glob("./fixtures/**/*.json", {
  eager: true,
  import: "default",
});
export const fixture = <T>(name: string): T =>
  structuredClone(
    (recorded.overrides as Record<string, unknown>)[name] ??
      files[`./fixtures/${name}.json`],
  ) as T;
const state = () => useConsole.getState();
const now = () => state().sim?.sim_ts || "2026-11-27T11:45:00Z";
let sequence = 10000,
  id = 0,
  fault = false,
  recovered = false,
  elapsed = 0;
let verificationStart: number | null = null;
let metricPhase: keyof typeof recorded.phases = "healthy";
let phaseStarted = Date.parse("2026-11-27T11:45:00Z");
function setMetricPhase(phase: typeof metricPhase) {
  metricPhase = phase;
  phaseStarted = Date.parse(now());
}
function recordedValues(simTs: string) {
  const rows = recorded.phases[metricPhase] as {
    offset_s: number;
    sim_ts: string;
    values: Record<string, number>;
  }[];
  const offset = Math.max(0, (Date.parse(simTs) - phaseStarted) / 1000);
  return rows.length
    ? {
        ...([...rows].reverse().find((r) => r.offset_s <= offset) || rows[0])
          .values,
      }
    : null;
}
function recordedHealth(simTs: string) {
  const rows = recorded.healthPhases[
    metricPhase
  ] as unknown as (Schema<"HealthResponse"> & { offset_s: number })[];
  const offset = Math.max(0, (Date.parse(simTs) - phaseStarted) / 1000);
  const row = [...rows].reverse().find((r) => r.offset_s <= offset) || rows[0];
  if (!row) return null;
  const { offset_s: _, ...health } = row;
  return { ...health, sim_ts: simTs };
}
let ticker: ReturnType<typeof setInterval> | undefined;
let seeded = false;
function seedContent() {
  if (seeded) return;
  seeded = true;
  const base = fixture<Schema<"LedgerResponse">>("rest/GET_ledger").entries[0];
  const seeds: [string, number, string, string | null][] = [
    ["pathcom.status_server", 214, "L2", "Dave"],
    ["meas.cpu_busy", 180, "L2", "Dave"],
    ["pathcom.info_server", 66, "L2", "Maria"],
    ["pathcom.stats_server", 12, "L1", null],
    ["tacl.status_cpu", 7, "L1", null],
    ["scf.status_disk", 15, "L1", null],
    ["tmfcom.status_tmf", 9, "L1", null],
    ["tacl.suspend_process", 41, "L1", null],
    ["pathcom.alter_numstatic", 3, "L1", null],
  ];
  useConsole.setState({
    claims: content.claims as unknown as Schema<"Claim">[],
    ledger: [
      base,
      ...seeds.map(
        ([catalog_id, count, level, granted_by]) =>
          ({
            ...base,
            key: `${catalog_id}|any|operator`,
            catalog_id,
            counters: { ...base.counters, approved_unchanged: count },
            level,
            granted_by,
            tier:
              catalog_id === "pathcom.alter_numstatic"
                ? "T2"
                : catalog_id === "tacl.suspend_process"
                  ? "T1"
                  : "T0",
          }) as Schema<"LedgerEntry">,
      ),
    ],
  });
  const tick = fixture<{ payload: { values: Record<string, number> } }>(
    "ws/telemetry.tick",
  ).payload;
  const series: Record<string, import("@/api/types").MetricPoint[]> = {};
  for (const [key, value] of Object.entries(tick.values))
    series[key] = Array.from({ length: 60 }, (_, n) => [
      new Date(
        Date.parse("2026-11-27T11:45:00Z") - (59 - n) * 15000,
      ).toISOString(),
      value +
        (key.endsWith(".p95_ms") || key.endsWith(".busy")
          ? Math.sin(n * 0.7) * value * 0.035
          : 0),
    ]);
  useConsole.setState({
    values: tick.values,
    series,
    rawTotal: 2135,
    eventRate: 302,
  });
}
const timers = new Set<ReturnType<typeof setTimeout>>();
const later = (ms: number, fn: () => void) => {
  const t = setTimeout(() => {
    timers.delete(t);
    fn();
  }, ms);
  timers.add(t);
};
export function emit(
  type: Event["type"],
  payload: unknown,
  topic = type.split(".")[0],
) {
  const event: Event = {
    topic,
    type,
    seq: ++sequence,
    ts: new Date().toISOString(),
    sim_ts: now(),
    payload,
  };
  state().ingest(event);
  return event;
}
function card(name: string): Card {
  return fixture<Card>(`cards/${name}`);
}
function put(c: Card) {
  c.thread_id = state().threadId || c.thread_id;
  c.incident_id = state().incidents.at(-1)?.id || null;
  c.sim_ts = now();
  emit("card.upsert", c, `thread:${c.thread_id}`);
}
function note(title: string, kind = "check", actor = "baton", ref?: string) {
  if (!state().incidents.length) return;
  const template = fixture<{ payload: { item: Timeline } }>(
    "ws/timeline.append",
  ).payload.item;
  const name =
    state().users.find((u) => u.id === actor)?.name ||
    (actor === "baton" ? "Baton" : "System");
  emit(
    "timeline.append",
    {
      incident_id: state().incidents[0]?.id,
      item: {
        ...template,
        id: `tml_mock_${++id}`,
        sim_ts: now(),
        kind,
        title,
        actor: { type: actor === "baton" ? "agent" : "user", id: actor, name },
        ref: ref ? { type: "card", id: ref } : null,
      },
    },
    "incidents",
  );
}
function trace(label: string, summary: string, status = "done") {
  const t = fixture<{ payload: Trace }>("ws/node.ended").payload;
  emit(
    "node.ended",
    {
      ...t,
      run_id: `run_mock_${state().threadId}`,
      step_id: `step_mock_${++id}`,
      node: label.toLowerCase().replaceAll(" ", "_"),
      label,
      summary,
      status,
      detail: {
        tools: [],
        evidence_ids: [],
        model: "fallback",
        prompt_hash: null,
      },
    },
    `thread:${state().threadId}`,
  );
}
let auditQueue: Promise<void> = Promise.resolve();
async function hash(input: string) {
  return Array.from(
    new Uint8Array(
      await crypto.subtle.digest("SHA-256", new TextEncoder().encode(input)),
    ),
  )
    .map((x) => x.toString(16).padStart(2, "0"))
    .join("");
}
function audit(action: string, target: string, actor: string) {
  auditQueue = auditQueue.then(async () => {
    const template = fixture<{ rows: AuditRow[] }>("rest/GET_audit").rows[0];
    const entries = state().audit;
    const row = {
      ...template,
      seq: entries.length + 1,
      sim_ts: now(),
      wall_ts: new Date().toISOString(),
      actor_type: actor === "baton" ? "agent" : "user",
      actor_id: actor,
      action,
      target,
      payload: { mock: true, incident_id: state().incidents[0]?.id || null },
      prev_hash: entries.at(-1)?.hash || "0".repeat(64),
    } as AuditRow;
    row.hash = await hash(
      row.prev_hash + JSON.stringify({ ...row, hash: undefined }),
    );
    emit("audit.append", row);
  });
  return auditQueue;
}
function ghost(
  text: string,
  lines: string[],
  auto = false,
  actor = state().actor,
) {
  const exec = `exe_mock_${++id}`;
  emit(
    "terminal.ghost",
    {
      exec_id: exec,
      text,
      actor,
      auto,
      approved_by: auto ? [] : [actor],
      ms_per_char: 25,
      label: auto
        ? "Baton · auto · L2 (granted by Dave)"
        : `Baton · approved by ${state().users.find((u) => u.id === actor)?.name || actor}`,
    },
    "terminal",
  );
  later(text.length * 25 + 50, () => {
    emit("terminal.output", { exec_id: exec, lines }, "terminal");
    emit("terminal.prompt", { text: "$SYSTEM STARTUP 17> " }, "terminal");
  });
  void audit("command.executed", text, auto ? "baton" : actor);
  return exec;
}
function beginFault() {
  if (fault)
    throw new Error(
      "CPU 3 fault is already active. Reset the scenario to rehearse again.",
    );
  fault = true;
  elapsed = 0;
  const sim = {
    ...state().sim!,
    sim_ts: "2026-11-27T11:52:04Z",
    speed: 1,
    active_faults: [
      { fault: "cpu_halt", params: { cpu: 3 }, at: "2026-11-27T11:52:04Z" },
    ],
  };
  emit("sim.state", sim);
  setMetricPhase("fault");
  emit(
    "health.snapshot",
    {
      ...fixture<{ payload: Schema<"HealthResponse"> }>(
        "ws/health.snapshot.fault",
      ).payload,
      sim_ts: now(),
    },
    "health",
  );
  emit(
    "telemetry.tick",
    {
      ...fixture<{ payload: { values: Record<string, number> } }>(
        "ws/telemetry.tick.fault",
      ).payload,
      sim_ts: now(),
    },
    "telemetry",
  );
  const incident = {
    ...fixture<Incident>("rest/GET_incidents_id"),
    undo_stack: [],
    status: "open",
  };
  emit("incident.upsert", incident, "incidents");
  emit(
    "situation.upsert",
    fixture<{ payload: unknown }>("ws/situation.upsert").payload,
    "situations",
  );
  put(card("situation"));
  note("CPU 3 halted. PATHMON took over on CPU 5.", "situation", "system");
  trace(
    "Read the situation",
    "CPU loss and takeover correlate with ATM latency.",
  );
  later(500, () => {
    const h = card("hypotheses");
    if (h.type === "hypotheses") {
      h.body.hypotheses[0].p = 0.54;
      h.body.hypotheses[1].p = 0.3;
      h.body.stop_rule.met = false;
    }
    put(h);
    put(card("evidence"));
    trace(
      "Gather evidence",
      "Read telemetry, episodes and verified knowledge.",
    );
  });
  later(1000, () => {
    trace("Run checks", "Two read-only checks allowed by the trust ledger.");
    ghost(
      "MEASCOM; LIST CPU *, BUSY",
      ["CPU  STATE  BUSY-%", "  3  DOWN      —", "  5  UP     97.2"],
      true,
    );
    const c = card("command_auto_done");
    put(c);
    ghost(
      "PATHCOM $PM1; STATUS SERVER ATM-AUTH",
      [
        "SERVER    STATE    RUNNING  MAXSERVERS  QUEUED  AVG-MS",
        "ATM-AUTH  RUNNING       20          32     142     846",
      ],
      true,
    );
    note("Two automatic checks completed · L2 granted by Dave");
    const h = card("hypotheses");
    if (h.type === "hypotheses") h.body.stop_rule.met = false;
    put(h);
  });
  later(2500, () => {
    const c = card("command");
    put(c);
    emit(
      "approval.upsert",
      fixture<Schema<"ApprovalsResponse">>("rest/GET_approvals").approvals[0],
    );
    trace(
      "Wait for approval",
      "Rule out TMF pressure · 19 of 20 clean runs",
      "waiting",
    );
    note("TMF audit check needs approval", "approval_requested", "baton", c.id);
  });
}
function options() {
  trace(
    "Enough evidence?",
    "Yes · evidence supports capacity loss; TMF pressure ruled down.",
  );
  const h = card("hypotheses");
  if (h.type === "hypotheses") {
    h.body.stop_rule.met = true;
    h.body.hypotheses[0].p = 0.95;
  }
  put(h);
  put(card("expert"));
  trace(
    "Find expert knowledge",
    "Dave’s playbook v3, verified by Maria · C-001 and C-005.",
  );
  const c = card("decision");
  if (c.type === "decision")
    for (const option of c.body.options.filter(
      (o) => o.id === "opt_a" || o.id === "opt_b",
    )) {
      const a =
        fixture<Schema<"ApprovalsResponse">>("rest/GET_approvals").approvals[0];
      const approval = {
        ...a,
        id: `apr_mock_${option.id}`,
        card_id: c.id,
        option_ids: [option.id],
        decisions: [],
        status: "pending",
        tier: option.tier,
        rendered: option.steps.map((s) => s.rendered),
        required: {
          count: option.required_approvers || 1,
          roles: ["operator", "senior", "expert"],
          at_least_one_of: option.id === "opt_b" ? ["senior", "expert"] : [],
        },
        progress_text: `0 of ${option.required_approvers} approvals`,
        policy: {
          ...a.policy,
          effect: "require_approval",
          rule_ids: [option.id === "opt_b" ? "t2-two-person" : "t1-single"],
          explanation:
            option.id === "opt_b"
              ? "Two distinct approvers, at least one Senior or Expert"
              : "One operator approval",
        },
      } as Approval;
      option.approval_id = approval.id;
      emit("approval.upsert", approval);
    }
  put(c);
  trace("Build options", "A + B recommended; CPU reload blocked by policy.");
}
function performOption(optionId: string, actor: string) {
  const incident = state().incidents[0];
  if (!incident) return;
  const c = state().cards.find((c) => c.type === "decision");
  if (c?.type !== "decision") return;
  const option = c.body.options.find((o) => o.id === optionId);
  if (!option) return;
  setMetricPhase(optionId === "opt_a" ? "suspended" : "recovering");
  for (const step of option.steps) {
    const exec = ghost(
      step.rendered,
      [
        optionId === "opt_a"
          ? "PROCESS $STMT1 SUSPENDED"
          : "ATM-AUTH ALTERED · NUMSTATIC 28",
      ],
      false,
      actor,
    );
    const undo = {
      id: `und_${++id}`,
      execution_id: exec,
      catalog_id:
        optionId === "opt_a"
          ? "tacl.activate_process"
          : "pathcom.alter_numstatic",
      params:
        optionId === "opt_a"
          ? { process: "$STMT1" }
          : { server_class: "ATM-AUTH", n: 20 },
      rendered: step.undo || "",
      label: step.undo || "",
      status: "pending",
      created_sim_ts: now(),
    };
    emit(
      "incident.upsert",
      {
        ...state().incidents[0],
        status: "mitigating",
        undo_stack: [...state().incidents[0].undo_stack, undo],
      },
      "incidents",
    );
    note(step.rendered, "action_executed", actor, c.id);
  }
  const updated = structuredClone(c);
  if (updated.type === "decision")
    updated.body.options = updated.body.options.map((o) =>
      o.id === optionId ? { ...o, status: "executed" } : o,
    );
  put(updated);
  if (
    updated.type === "decision" &&
    updated.body.options
      .filter((o) => ["opt_a", "opt_b"].includes(o.id))
      .every((o) => o.status === "executed")
  ) {
    trace(
      "Verify recovery",
      "Watching service latency and CPU load for 60 simulated seconds.",
      "running",
    );
    emit(
      "incident.upsert",
      { ...state().incidents[0], status: "verifying" },
      "incidents",
    );
    emit("sim.state", { ...state().sim!, speed: 4 });
    verificationStart = Date.parse(now());
  }
}
function resolveIncident() {
  recovered = true;
  put(card("verification"));
  put(card("postmortem"));
  emit(
    "incident.upsert",
    { ...state().incidents[0], status: "resolved", resolved_at: now() },
    "incidents",
  );
  trace("Verify recovery", "Recovered: ATM p95 in band for 60 s.");
  trace(
    "Write postmortem and claims",
    "Two synthetic claims drafted for expert review.",
  );
  note("Recovered: ATM p95 in band for 60 s", "verification", "baton");
  const template =
    fixture<Schema<"ClaimsResponse">>("rest/GET_claims").claims[0];
  emit("claim.upsert", template);
  emit("claim.upsert", {
    ...template,
    id: "clm_mock_scope",
    statement:
      "Adding eight ATM-AUTH static servers helped recovery after a peak CPU halt.",
    structured: {
      ...template.structured,
      condition: "TORBANK · Black Friday peak · one CPU down",
    },
  });
  const entry = state().ledger.find(
    (x) => x.catalog_id === "tmfcom.status_audittrail",
  );
  if (entry)
    emit("ledger.promotion_candidate", {
      entry: {
        ...entry,
        counters: { ...entry.counters, approved_unchanged: 20 },
        eligible_for: "L2",
      },
      text: "20 clean runs · eligible for L2",
    });
  void audit("incident.resolved", state().incidents[0].id, "baton");
}
function reset() {
  for (const t of timers) clearTimeout(t);
  timers.clear();
  fault = false;
  recovered = false;
  elapsed = 0;
  verificationStart = null;
  resetRuntime();
  const system = fixture<Schema<"SystemStatus">>("rest/GET_system_status");
  seeded = false;
  seedContent();
  useConsole.setState({
    sim: system.sim,
    health: fixture("rest/GET_health"),
    readOnly: false,
  });
  setMetricPhase("healthy");
  emit("health.snapshot", fixture("rest/GET_health"), "health");
  emit(
    "telemetry.tick",
    fixture<{ payload: unknown }>("ws/telemetry.tick").payload,
    "telemetry",
  );
  emit(
    "terminal.system",
    { text: "Baton simulator reset. S1 ready. All runtime actions cleared." },
    "terminal",
  );
}
export function startMock() {
  seedContent();
  if (ticker) clearInterval(ticker);
  ticker = setInterval(() => {
    const sim = state().sim;
    if (!sim || sim.paused || !sim.running) return;
    elapsed += sim.speed;
    const date = new Date(new Date(sim.sim_ts!).getTime() + 1000 * sim.speed);
    emit("sim.state", { ...sim, sim_ts: date.toISOString() });
    const values =
      recordedValues(date.toISOString()) ||
      fixture<{ payload: { values: Record<string, number> } }>(
        `ws/telemetry.tick${fault ? ".fault" : ""}`,
      ).payload.values;
    emit("telemetry.tick", { sim_ts: date.toISOString(), values }, "telemetry");
    const health = recordedHealth(date.toISOString());
    if (health) emit("health.snapshot", health, "health");
    emit(
      "events.rate",
      {
        per_min: fault && !recovered ? 612 : 302,
        raw_total: state().rawTotal + (fault ? 10 : 5),
      },
      "events",
    );
    if (
      verificationStart !== null &&
      !recovered &&
      date.getTime() - verificationStart >= 60000
    )
      resolveIncident();
    if (elapsed % 20 < sim.speed)
      emit(
        "episode.upsert",
        fixture<{ payload: unknown }>(
          "ws/episode.upsert" + (elapsed > 40 && !fault ? ".quarantined" : ""),
        ).payload,
        "events",
      );
  }, 1000);
  return () => {
    if (ticker) clearInterval(ticker);
    ticker = undefined;
    for (const t of timers) clearTimeout(t);
    timers.clear();
  };
}
export async function mockRequest(
  path: string,
  body?: object,
): Promise<unknown> {
  seedContent();
  const [url, search = ""] = path.split("?");
  const q = new URLSearchParams(search);
  const b = (body || {}) as Record<string, unknown>;
  const actor = String(b.actor || state().actor);
  if (!body) {
    const mapping: Record<string, string> = {
      "/users": "GET_users",
      "/eval/latest": "GET_eval_latest",
      "/topology": "GET_topology",
    };
    if (mapping[url]) return fixture(`rest/${mapping[url]}`);
    if (url === "/system/status")
      return {
        ...fixture<Schema<"SystemStatus">>("rest/GET_system_status"),
        sim: state().sim || fixture("rest/GET_sim_state"),
        read_only: state().readOnly,
      };
    if (url === "/sim/state")
      return state().sim || fixture("rest/GET_sim_state");
    if (url === "/health") return state().health || fixture("rest/GET_health");
    if (url === "/incidents") return { incidents: state().incidents };
    if (url === "/situations") return { situations: state().situations };
    if (url === "/catalog") {
      const base =
        fixture<Schema<"CatalogResponse">>("rest/GET_catalog").entries[0];
      return {
        entries: content.commands.map((ref) => ({
          ...base,
          id: ref.catalog_id,
          title: ref.title,
          description: ref.text,
          interpreter: ref.interpreter,
          template: ref.syntax,
          tier: ref.tier.slice(0, 2),
          tier_rules: ref.tier,
          params: [],
          reversible: ref.undo !== "none",
          undo_template: ref.undo === "none" ? null : ref.undo,
          risks: ref.cautions,
          blocked: ref.tier.startsWith("T3"),
          internal: ref.catalog_id.startsWith("baton."),
          utility: ref.interpreter.split(" ")[0],
        })),
      };
    }
    if (url === "/claims")
      return {
        claims: state().claims.filter(
          (c) => !q.get("status") || c.status === q.get("status"),
        ),
      };
    if (url === "/ledger")
      return {
        entries: state().ledger.length
          ? state().ledger
          : fixture<Schema<"LedgerResponse">>("rest/GET_ledger").entries,
      };
    if (url === "/approvals") return { approvals: state().approvals };
    if (url === "/episodes") return { episodes: state().episodes };
    if (url === "/audit/verify") {
      await auditQueue;
      let previous = "0".repeat(64),
        valid = true;
      for (const row of state().audit) {
        if (
          row.prev_hash !== previous ||
          (await hash(
            row.prev_hash + JSON.stringify({ ...row, hash: undefined }),
          )) !== row.hash
        )
          valid = false;
        previous = row.hash;
      }
      return { valid, entries: state().audit.length, head_hash: previous };
    }
    if (url === "/audit") {
      await auditQueue;
      return { rows: state().audit };
    }
    if (url.endsWith("/timeline")) return { items: state().timeline };
    if (url.endsWith("/postmortem"))
      return fixture("rest/GET_incidents_id_postmortem");
    if (url.startsWith("/incidents/")) return state().incidents[0];
    if (url.startsWith("/threads/"))
      return {
        thread: { id: state().threadId },
        cards: state().cards,
        trace: state().trace,
        pending_interrupts: [],
      };
    if (url === "/kb/search") {
      const result = fixture<Schema<"KbSearchResponse">>("rest/GET_kb_search");
      return {
        ...result,
        query: q.get("q"),
        results: [
          ...result.results,
          ...state()
            .claims.filter((c) => c.status === "verified")
            .map((c) => ({
              id: c.id,
              doc_type: "claim",
              title: c.statement,
              snippet: c.structured.condition,
              synthetic: true,
              provenance: "expert_verified",
              scores: { authority: 1.2 },
            })),
        ].filter((r) =>
          (q.get("q") || "")
            .split(" ")
            .some((term) =>
              `${r.title} ${r.snippet}`
                .toLowerCase()
                .includes(term.toLowerCase()),
            ),
        ),
      };
    }
    if (url.startsWith("/kb/items/")) {
      const wanted = decodeURIComponent(url.split("/").at(-1)!);
      const records = [
        ...content.operator_messages,
        ...content.commands,
        ...content.concepts,
        ...content.glossary,
        ...content.incidents,
        ...content.playbooks.map((p) => ({ ...p, id: `playbook:${p.id}` })),
        ...state().claims.map((c) => ({
          ...c,
          id: c.id.startsWith("C-") ? `claim:${c.id}` : c.id,
        })),
      ];
      const record = records.find((r) => r.id === wanted);
      if (!record) throw new Error(`No local source record for ${wanted}.`);
      return record;
    }
    if (url === "/metrics")
      return {
        series: Object.entries(state().series).map(([key, points]) => ({
          key,
          points,
        })),
      };
    throw new Error(`No mock fixture for ${url}`);
  }
  if (url === "/sim/reset") {
    reset();
    await audit("sim.reset", "S1", actor);
    return state().sim;
  }
  if (url === "/sim/start") {
    reset();
    emit("sim.state", {
      ...state().sim!,
      scenario: b.scenario,
      scenario_name:
        b.scenario === "S0"
          ? "Healthy normal day"
          : "CPU loss at Black Friday peak",
      profile: b.profile,
      seed: b.seed || 42,
      running: true,
      ...(b.scenario === "S0"
        ? { sim_ts: "2026-11-17T10:00:00Z", calendar: "normal" }
        : {}),
    });
    await audit("sim.start", String(b.scenario), actor);
    return state().sim;
  }
  if (url === "/sim/inject") {
    if (
      b.fault !== "cpu_halt" ||
      Number((b.params as Record<string, unknown>)?.cpu) !== 3
    )
      throw new Error(
        "This rehearsal contains the S1 CPU 3 halt. Use the real backend for other faults.",
      );
    beginFault();
    await audit("sim.fault", "CPU 3 halt", actor);
    return state().sim;
  }
  if (url === "/sim/clock") {
    const { actor: _, ...clock } = b;
    emit("sim.state", { ...state().sim!, ...clock });
    return state().sim;
  }
  if (url === "/sim/replay") {
    useConsole.setState({ replay: String(b.mode) });
    await audit("sim.replay", String(b.mode), actor);
    return {};
  }
  if (url === "/system/read-only") {
    useConsole.setState({ readOnly: !!b.enabled });
    await audit("system.read_only", String(b.enabled), actor);
    return {};
  }
  if (url === "/threads") {
    const threadId = state().threadId || "thr_mock_console";
    useConsole.setState({ threadId });
    return { id: threadId };
  }
  if (url.endsWith("/investigate"))
    return {
      thread_id: state().threadId,
      incident_id: state().incidents[0]?.id,
    };
  if (url === "/commands/preview") {
    const params = (b.params || {}) as Record<string, unknown>;
    const catalogId = String(b.catalog_id);
    const ref = content.commands.find((c) => c.catalog_id === catalogId);
    const errors: string[] = [];
    if (!ref)
      return {
        valid: false,
        errors: ["Catalog entry not found"],
        rendered: null,
        tier: null,
        policy: null,
      };
    for (const match of ref.syntax.matchAll(/\{(\w+)\}/g))
      if (params[match[1]] == null) errors.push(`${match[1]} is required`);
    if (
      params.server_class &&
      !["ATM-AUTH", "POS-AUTH", "BAL-INQ", "CARD-MGMT"].includes(
        String(params.server_class),
      )
    )
      errors.push("Server class not found in inventory");
    if (
      params.n != null &&
      (!Number.isInteger(Number(params.n)) || Number(params.n) < 1)
    )
      errors.push("Server count must be a positive integer");
    if (catalogId === "pathcom.alter_numstatic" && Number(params.n) > 32)
      errors.push("NUMSTATIC cannot exceed MAXSERVERS (32) · PATHWAY 2049");
    let tier = ref.tier.slice(0, 2);
    if (
      catalogId === "pathcom.alter_numstatic" &&
      params.server_class === "ATM-AUTH"
    )
      tier = "T2";
    const protectedTarget = [
      "$PM1",
      "$DATA01",
      "$DATA02",
      "$DATA03",
      "$DATA04",
    ].includes(String(params.process));
    const denied =
      (state().readOnly && tier !== "T0") ||
      tier === "T3" ||
      (protectedTarget && tier !== "T0");
    const syntax = ref.syntax.replace(/\{(\w+)\}/g, (_, key) =>
      String(params[key] ?? `{${key}}`),
    );
    const rendered =
      ref.interpreter === "TACL"
        ? syntax
        : ref.interpreter.startsWith("Baton")
          ? null
          : `${ref.interpreter}; ${syntax}`;
    return {
      valid: !errors.length,
      errors,
      rendered,
      tier,
      undo:
        ref.undo === "none"
          ? null
          : ref.undo.replace(/\{(\w+)\}/g, (_, key) =>
              String(params[key] ?? `{${key}}`),
            ),
      policy: {
        effect: denied ? "deny" : "require_approval",
        required_approvers: tier === "T2" ? 2 : 1,
        required_roles: [],
        at_least_one_of: tier === "T2" ? ["senior", "expert"] : [],
        rule_ids: [
          state().readOnly && tier !== "T0"
            ? "read-only"
            : protectedTarget
              ? "protected"
              : tier === "T3"
                ? "t3-block"
                : tier === "T2"
                  ? "t2-two-person"
                  : tier === "T1"
                    ? "t1-single"
                    : "t0-default",
        ],
        explanation: denied
          ? state().readOnly
            ? "Read-only mode"
            : protectedTarget
              ? "Protected system process"
              : "Destructive or outage-capable: human-only, outside Baton"
          : tier === "T2"
            ? "Two distinct approvers, at least one Senior or Expert"
            : tier === "T1"
              ? "One operator approval; reversible action"
              : "One approval required for this read-only check",
      },
    };
  }
  if (url.startsWith("/approvals/") && url.endsWith("/decide")) {
    const a = state().approvals.find((a) => a.id === url.split("/")[2]);
    if (!a) throw new Error("Approval not found. Refresh the incident.");
    if (!["pending", "partially_approved"].includes(a.status))
      throw new Error("This approval is already complete.");
    if (new Date(a.expires_sim_ts).getTime() < new Date(now()).getTime())
      throw new Error("Approval expired. Refresh to request a new one.");
    if (state().readOnly && a.tier !== "T0") throw new Error("Read-only mode");
    if (a.decisions.some((d) => d.actor === actor))
      throw new Error(
        "Switch to a different eligible persona for the second approval.",
      );
    const decisions = [
      ...a.decisions,
      {
        actor,
        actor_name: state().users.find((u) => u.id === actor)?.name,
        decision: b.decision,
        at: now(),
      },
    ];
    const approved =
      b.decision !== "reject" && decisions.length >= a.required.count;
    if (
      approved &&
      a.tier === "T2" &&
      !decisions.some((d) =>
        ["senior", "expert"].includes(
          state().users.find((u) => u.id === d.actor)?.role || "",
        ),
      )
    )
      throw new Error("At least one Senior or Expert must approve.");
    if (b.decision === "reject" && !b.reason_code)
      throw new Error("Choose a rejection reason.");
    if (b.decision === "edit_approve" && a.option_ids.length && b.params) {
      if (a.decisions.length)
        throw new Error(
          "This rehearsal requires edits before the first approval. Re-propose the action to change an already approved command.",
        );
      const c = state().cards.find((c) => c.type === "decision");
      if (c?.type === "decision") {
        const changed = structuredClone(c);
        for (const option of changed.body.options.filter((o) =>
          a.option_ids.includes(o.id),
        )) {
          const step = option.steps[0];
          const preview = (await mockRequest("/commands/preview", {
            catalog_id: step.catalog_id,
            params: b.params,
            actor,
          })) as Schema<"CommandPreviewResponse">;
          if (!preview.valid || preview.policy?.effect === "deny")
            throw new Error(
              preview.errors.join(", ") ||
                preview.policy?.explanation ||
                "Validation failed",
            );
          step.params = b.params as Record<string, unknown>;
          step.rendered = preview.rendered!;
        }
        put(changed);
      }
    }
    const next = {
      ...a,
      decisions,
      status:
        b.decision === "reject"
          ? "rejected"
          : approved
            ? "approved"
            : "partially_approved",
      progress_text: approved
        ? "Approved"
        : `${decisions.length} of ${a.required.count}: needs Senior or Expert`,
    } as Approval;
    emit("approval.upsert", next);
    await audit(`approval.${b.decision}`, a.id, actor);
    note(
      `${state().users.find((u) => u.id === actor)?.name} · ${b.decision}`,
      "approval_decided",
      actor,
      a.card_id || undefined,
    );
    const command = state().cards.find(
      (c) => c.type === "command" && c.body.approval_id === a.id,
    );
    if (command?.type === "command") {
      const done = structuredClone(command);
      done.status = b.decision === "reject" ? "blocked" : "done";
      if (approved) {
        const stats = done.body.catalog_id === "pathcom.stats_server";
        let lines = stats
          ? [
              "SERVER    TPS  AVG-MS  MAX-MS  QUEUED",
              "ATM-AUTH  812      31     171       0",
            ]
          : [
              "TRAIL  FILL-%  OVERFLOW-%  DUMPS",
              "MAT      31.2        80.0  ENABLED",
            ];
        const recordedExecution = fixture<Schema<"CommandCard"> | undefined>(
          stats ? "cards/command_stats_done" : "cards/command_tmf_done",
        )?.body.execution;
        if (recordedExecution?.raw_output)
          lines = recordedExecution.raw_output
            .split("\n")
            .filter((line) => !line.includes("$SYSTEM STARTUP"));
        const exec = ghost(done.body.rendered, lines, false, actor);
        done.body.execution = {
          ...fixture<Schema<"CommandCard">>("cards/command_auto_done").body
            .execution!,
          exec_id: exec,
          auto: false,
          approved_by: [actor],
          summary: stats
            ? "ATM-AUTH: 24 of 32 servers running, no queued requests; within the Black Friday late-morning range."
            : "Audit fill 31.2%, below 80% threshold. TMF pressure ruled out.",
          raw_output: lines.join("\n"),
          facts: stats
            ? { tps: 812, avg_ms: 31, queued: 0 }
            : { fill_pct: 31.2 },
          facts_table: stats
            ? [
                { label: "Running", value: "24 of 32" },
                { label: "Queued", value: "0" },
                { label: "Average", value: "31 ms" },
              ]
            : [{ label: "Audit fill", value: "31.2%" }],
        };
        if (recordedExecution) {
          done.body.execution = {
            ...recordedExecution,
            exec_id: exec,
            auto: false,
            approved_by: [actor],
            ...(stats
              ? {
                  summary: `${recordedExecution.summary} · within the Black Friday late-morning range.`,
                }
              : {}),
          };
        }
      }
      put(done);
      if (approved && done.body.catalog_id === "tmfcom.status_audittrail")
        later(700, options);
    } else if (approved)
      for (const option of a.option_ids) performOption(option, actor);
    return { approval: next };
  }
  if (url.endsWith("/messages") || url === "/terminal/input") {
    const text = String(b.text || b.line || "");
    const lower = text.toLowerCase();
    await audit("message.sent", text, actor);
    trace("Understand", text);
    if (/reload|stop tmf|suspend.*\$pm1/i.test(text)) {
      const c = card("command");
      c.id = `card_blocked_${++id}`;
      c.seq = 100 + id;
      c.status = "blocked";
      if (c.type === "command") {
        c.title = "Action blocked";
        c.body.rendered = text;
        c.body.tier = "T3";
        c.body.policy = {
          ...c.body.policy,
          effect: "deny",
          rule_ids: [lower.includes("$pm1") ? "protected" : "t3-block"],
          explanation: lower.includes("$pm1")
            ? "Protected system process"
            : "Destructive or outage-capable: human-only, outside Baton",
          escalation: "Call HPE hardware support with the evidence pack",
        };
        c.body.approval_id = null;
      }
      put(c);
    } else if (/numstatic|maxservers/.test(lower) && !/^alter/.test(lower)) {
      const c = card("text");
      c.id = `card_answer_${++id}`;
      c.seq = 100 + id;
      c.title = "NUMSTATIC and MAXSERVERS";
      c.citations = [
        {
          id: "concept:numstatic-maxservers",
          label: "Concept note",
          kind: "concept",
          url: null,
        },
        {
          id: "cmdref:pathcom.alter_numstatic",
          label: "Command reference",
          kind: "command_ref",
          url: null,
        },
        {
          id: "opmsg:PATHWAY:2049",
          label: "PATHWAY 2049",
          kind: "hpe_manual",
          url: "https://ftp.hp.com/pub/softlib/NonStopOpMsgsMnl/ch78.html",
        },
      ];
      if (c.type === "text")
        c.body = {
          markdown:
            "**NUMSTATIC** is the number of static servers kept running. **MAXSERVERS** caps the total servers in the class, including dynamic servers. NUMSTATIC must not exceed MAXSERVERS (PATHWAY 2049).",
          sentences: [],
          unknown: false,
          alternatives: [],
        };
      put(c);
    } else if (fault) {
      const c = card("text");
      c.id = `card_answer_${++id}`;
      c.seq = 100 + id;
      put(c);
    } else if (/atm|status|keeping|stats/.test(lower)) {
      ghost(
        "PATHCOM $PM1; STATUS SERVER ATM-AUTH",
        [
          "SERVER    RUNNING  MAXSERVERS  QUEUED  AVG-MS",
          "ATM-AUTH       24          32       0      31",
        ],
        true,
      );
      const c = card("command");
      c.id = "card_flow_b";
      c.seq = 10;
      c.title = "ATM authorization performance";
      if (c.type === "command") {
        c.body.catalog_id = "pathcom.stats_server";
        c.body.rendered = "PATHCOM $PM1; STATS SERVER ATM-AUTH";
        c.body.params = { server_class: "ATM-AUTH" };
        c.body.approval_id = "apr_flow_b";
        c.body.purpose =
          "Check requests and response times for ATM authorization.";
        if (c.body.autonomy) c.body.autonomy.progress = "12 clean runs";
      }
      put(c);
      const a =
        fixture<Schema<"ApprovalsResponse">>("rest/GET_approvals").approvals[0];
      emit("approval.upsert", {
        ...a,
        id: "apr_flow_b",
        card_id: c.id,
        rendered: ["PATHCOM $PM1; STATS SERVER ATM-AUTH"],
      });
    } else {
      const c = card("text");
      c.id = `card_answer_${++id}`;
      c.seq = 100 + id;
      if (c.type === "text")
        c.body.markdown =
          "I can check ATM authorization, explain NUMSTATIC and MAXSERVERS, or investigate an active situation. Try one of those requests.";
      put(c);
    }
    return { run_id: `run_mock_${id}` };
  }
  if (url.startsWith("/claims/") && url.endsWith("/review")) {
    const c = state().claims.find((c) => c.id === url.split("/")[2]);
    if (!c) throw new Error("Claim not found");
    if (
      !["expert", "steward"].includes(
        state().users.find((u) => u.id === actor)?.role || "",
      )
    )
      throw new Error("Switch to an Expert to review this claim.");
    const edits = (b.edits || {}) as Record<string, unknown>;
    emit("claim.upsert", {
      ...c,
      ...edits,
      status: b.decision === "reject" ? "rejected" : "verified",
      reviews: [...c.reviews, { user: actor, decision: b.decision, at: now() }],
    });
    await audit(`claim.${b.decision}`, c.id, actor);
    return {};
  }
  if (url.startsWith("/ledger/")) {
    if (state().users.find((u) => u.id === actor)?.role !== "expert")
      throw new Error("An Expert must grant or revoke autonomy.");
    if (!String(b.reason || "").trim())
      throw new Error("A reason is required.");
    const key = decodeURIComponent(url.split("/")[2]);
    const entry = state().ledger.find((e) => e.key === key);
    if (!entry) throw new Error("Ledger entry not found");
    emit("ledger.upsert", {
      ...entry,
      level: url.endsWith("/revoke") ? "L1" : b.level,
      granted_by: actor,
      grant_reason: b.reason,
      eligible_for: null,
    });
    await audit("ledger.granted", key, actor);
    return {};
  }
  if (url.startsWith("/executions/") && url.endsWith("/undo")) {
    if (state().readOnly) throw new Error("Read-only mode");
    const incident = state().incidents[0];
    const undo = incident?.undo_stack.find(
      (u) => u.execution_id === url.split("/")[2],
    );
    if (!undo) throw new Error("Undo entry not found");
    ghost(undo.rendered, ["Undo executed in rehearsal"], false, actor);
    emit(
      "incident.upsert",
      {
        ...incident,
        undo_stack: incident.undo_stack.map((u) =>
          u.id === undo.id ? { ...u, status: "applied" } : u,
        ),
      },
      "incidents",
    );
    await audit("execution.undone", undo.execution_id, actor);
    return {};
  }
  if (url === "/eval/run")
    throw new Error(
      "Mock mode displays contract example results. Run real evaluations with the backend.",
    );
  throw new Error(`No mock action for ${url}`);
}
