import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL("../../", import.meta.url));
const file =
  process.argv[2] || path.join(root, "contracts/recordings/golden_s1.json");
const doc = JSON.parse(await fs.readFile(file, "utf8"));
const version = (
  await fs.readFile(path.join(root, "contracts/VERSION"), "utf8")
).trim();
if (!doc.ok || doc.version !== version)
  throw new Error(
    "Recording must be successful and match the current contracts.",
  );
const events = doc.events.map((e) => e.envelope);
const cards = events
  .filter((e) => e.type === "card.upsert")
  .map((e) => e.payload);
const first = (type, predicate = () => true) =>
  events.find((e) => e.type === type && predicate(e.payload));
const lastCard = (type, predicate = () => true) =>
  cards.filter((c) => c.type === type && predicate(c)).at(-1);
const firstCard = (type, predicate = () => true) =>
  cards.find((c) => c.type === type && predicate(c));
const overrides = {};
for (const name of ["users", "catalog", "topology"])
  if (doc.rest[`GET /api/${name}`])
    overrides[`rest/GET_${name}`] = doc.rest[`GET /api/${name}`];
const initialSim = first("sim.state")?.payload;
const initialHealth = first(
  "health.snapshot",
  (p) => !p.components.some((c) => c.id === "cpu:3" && c.state === "down"),
)?.payload;
const faultHealth = first("health.snapshot", (p) =>
  p.components.some((c) => c.id === "cpu:3" && c.state === "down"),
);
const initialTick = first("telemetry.tick", (p) => p.values["cpu.3.up"] !== 0);
const faultTick = first("telemetry.tick", (p) => p.values["cpu.3.up"] === 0);
if (initialHealth) overrides["rest/GET_health"] = initialHealth;
if (initialTick) overrides["ws/telemetry.tick"] = initialTick;
if (faultHealth) overrides["ws/health.snapshot.fault"] = faultHealth;
if (faultTick) overrides["ws/telemetry.tick.fault"] = faultTick;
const incident = first("incident.upsert", (p) => !!p.thread_id)?.payload;
if (incident)
  overrides["rest/GET_incidents_id"] = { ...incident, undo_stack: [] };
const tmf = firstCard(
  "command",
  (c) =>
    c.body.catalog_id === "tmfcom.status_audittrail" &&
    c.status === "awaiting_approval" &&
    c.body.approval_id,
);
if (tmf) overrides["cards/command"] = tmf;
const tmfApproval = first(
  "approval.upsert",
  (p) =>
    p.rendered.some((r) => r.includes("STATUS AUDITTRAIL")) &&
    p.status === "pending",
)?.payload;
if (tmfApproval) overrides["rest/GET_approvals"] = { approvals: [tmfApproval] };
const auto = lastCard(
  "command",
  (c) => c.body.catalog_id === "pathcom.status_server" && c.status === "done",
);
if (auto) overrides["cards/command_auto_done"] = auto;
for (const [name, id] of [
  ["command_tmf_done", "tmfcom.status_audittrail"],
  ["command_stats_done", "pathcom.stats_server"],
]) {
  const c = lastCard(
    "command",
    (c) => c.body.catalog_id === id && c.status === "done",
  );
  if (c) overrides[`cards/${name}`] = c;
}
for (const type of [
  "hypotheses",
  "expert",
  "decision",
  "situation",
  "evidence",
  "verification",
  "postmortem",
  "text",
]) {
  const value =
    type === "decision"
      ? firstCard(type, (c) => !!c.body.approval_id)
      : lastCard(type);
  if (value) overrides[`cards/${type}`] = value;
}
const situation = first("situation.upsert");
if (situation) overrides["ws/situation.upsert"] = situation;
const draft = first(
  "claim.upsert",
  (p) =>
    p.status === "pending_review" && p.provenance.source_type === "incident",
)?.payload;
if (draft) overrides["rest/GET_claims"] = { claims: [draft] };
const episode = first(
  "episode.upsert",
  (p) => p.event_number === 1007 && !p.quarantined,
);
if (episode) overrides["ws/episode.upsert"] = episode;
const quarantine = first("episode.upsert", (p) => p.quarantined);
if (quarantine) overrides["ws/episode.upsert.quarantined"] = quarantine;
const timeline = first("timeline.append");
if (timeline) overrides["ws/timeline.append"] = timeline;
const trace = first("node.ended");
if (trace) overrides["ws/node.ended"] = trace;
const phases = { healthy: [], fault: [], suspended: [], recovering: [] };
const healthPhases = { healthy: [], fault: [], suspended: [], recovering: [] };
let phase = "healthy";
for (const env of events) {
  if (
    phase === "healthy" &&
    ((env.type === "health.snapshot" &&
      env.payload.components.some(
        (c) => c.id === "cpu:3" && c.state === "down",
      )) ||
      (env.type === "telemetry.tick" && env.payload.values["cpu.3.up"] === 0))
  )
    phase = "fault";
  if (
    env.type === "timeline.append" &&
    env.payload.item.kind === "action_executed"
  ) {
    if (env.payload.item.title.includes("SUSPEND")) phase = "suspended";
    if (env.payload.item.title.includes("NUMSTATIC")) phase = "recovering";
  }
  if (env.type === "telemetry.tick")
    phases[phase].push(structuredClone(env.payload));
  if (env.type === "health.snapshot")
    healthPhases[phase].push(structuredClone(env.payload));
}
for (const values of Object.values(phases))
  if (values.length) {
    const start = Date.parse(values[0].sim_ts);
    for (const row of values)
      row.offset_s = (Date.parse(row.sim_ts) - start) / 1000;
  }
for (const values of Object.values(healthPhases))
  if (values.length) {
    const start = Date.parse(values[0].sim_ts);
    for (const row of values)
      row.offset_s = (Date.parse(row.sim_ts) - start) / 1000;
  }
const destination = path.join(root, "frontend/src/mocks/recordings");
await fs.mkdir(destination, { recursive: true });
await fs.writeFile(
  path.join(destination, "golden_s1.json"),
  JSON.stringify(doc),
);
await fs.writeFile(
  path.join(root, "frontend/src/mocks/recorded-fixtures.json"),
  JSON.stringify({
    meta: {
      version,
      recorded_at: doc.recorded_at,
      event_count: events.length,
      initial_sim: initialSim,
    },
    overrides,
    phases,
    healthPhases,
  }),
);
console.log(
  `Imported ${events.length} real events, ${Object.keys(overrides).length} fixtures; clock phases ${Object.entries(
    phases,
  )
    .map(([k, v]) => `${k}:${v.length}`)
    .join(", ")}.`,
);
