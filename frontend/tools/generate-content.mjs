import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../../", import.meta.url));
const out = path.join(root, "data/content");
for (const dir of ["", "claims", "playbooks"])
  await fs.mkdir(path.join(out, dir), { recursive: true });
const spec = await fs.readFile(path.join(root, "BATON_MVP_SPEC.md"), "utf8");
const full = await fs.readFile(
  path.join(root, "docs/BATON_PRODUCT_SPEC.md"),
  "utf8",
);
const source = (chapter) =>
  `https://ftp.hp.com/pub/softlib/NonStopOpMsgsMnl/ch${chapter}.html`;
const slug = (s) =>
  s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
const jsonl = async (name, records) =>
  fs.writeFile(
    path.join(out, name),
    records.map((r) => JSON.stringify(r)).join("\n") + "\n",
  );
const yaml = async (name, record) =>
  fs.writeFile(path.join(out, name), JSON.stringify(record, null, 2) + "\n"); // JSON is valid YAML 1.2.
const chunk = (id, doc_type, title, text, metadata = {}, chapter = "01") => ({
  id,
  doc_type,
  title,
  header: `${doc_type} · ${title} · ${metadata.subsystem || metadata.components?.[0] || "TORBANK"}`,
  text,
  metadata,
  status: "active",
  synthetic: true,
  source: source(chapter),
});

const claimSection = spec
  .split("**Claims** (C-001")[1]
  .split("**Past incidents**")[0];
const claims = [...claimSection.matchAll(/^- (C-\d+) \((.*?)\): (.*)$/gm)].map(
  ([, id, credit, statement], i) => {
    const pending = i >= 16;
    const author = credit.split(/ ✓ |, /)[0].toLowerCase();
    const verifier = credit.includes("✓")
      ? credit.split("✓")[1].trim().toLowerCase()
      : null;
    const clean = statement
      .replace(/ \(good candidate.*$/, "")
      .replace(/^"|"\.?$/g, "")
      .replaceAll("`", "");
    const subject = Array.from(
      new Set(
        clean.match(/\$[A-Z0-9]+|ATM-AUTH|BAL-INQ|CPU \d|TMF|PATHWAY \d+/g) || [
          "NonStop operations",
        ],
      ),
    );
    let condition =
      "TORBANK site context; verify current state before applying";
    if (id === "C-001")
      condition =
        "Peak day, 11:00–13:00, CPU 5 constrained; resume after 13:00";
    if (["C-002", "C-005", "C-006", "C-013", "C-016"].includes(id))
      condition = "CPU failure or recovery on TORBANK";
    if (["C-008", "C-009"].includes(id))
      condition =
        "Month-end audit pressure; fill above 70% and rising faster than 0.8% per minute";
    const recommendation =
      id === "C-001"
        ? { catalog_id: "tacl.suspend_process", params: { process: "$STMT1" } }
        : id === "C-005"
          ? {
              catalog_id: "pathcom.alter_numstatic",
              params: { server_class: "ATM-AUTH", n: 28 },
            }
          : id === "C-007"
            ? { catalog_id: "tmfcom.status_audittrail", params: {} }
            : id === "C-008"
              ? {
                  catalog_id: "tacl.suspend_process",
                  params: { process: "$MEB01" },
                }
              : undefined;
    return {
      id,
      statement: clean,
      structured: {
        subject,
        condition,
        assertion: clean,
        ...(recommendation ? { recommendation } : {}),
        rationale:
          id === "C-001"
            ? "Statements are due by 18:00; the synthetic site batch catches up in about 40 minutes."
            : "Synthetic expert seed from Baton MVP Appendix C; site-specific guidance requires current evidence.",
      },
      scope: {
        site: "TORBANK",
        ...(["C-001", "C-014"].includes(id)
          ? { calendar: ["black_friday", "christmas_eve"] }
          : {}),
      },
      confidence: pending ? "sometimes" : "certain",
      status: pending ? "pending_review" : "verified",
      author: `u_${author}`,
      reviews: verifier
        ? [{ user: `u_${verifier}`, decision: "confirm", at: "2026-09-14" }]
        : [],
      version: 1,
      provenance: {
        source_type: "interview",
        source_id: "synthetic-seed-appendix-c",
      },
      synthetic: true,
      source: source(
        ["C-003", "C-004", "C-005", "C-012", "C-015"].includes(id)
          ? "78"
          : "68",
      ),
    };
  },
);
for (const claim of claims) await yaml(`claims/${claim.id}.yaml`, claim);

const playbooks = [
  {
    id: "PB-CPU-LOSS-PEAK",
    title: "CPU loss at peak",
    version: 3,
    author: "u_dave",
    verified_by: [{ user: "u_maria", at: "2026-09-14" }],
    trigger: { causal_template: "cpu_loss_cascade" },
    steps: [
      {
        kind: "check",
        catalog_id: "meas.cpu_busy",
        read: "Which survivor is hottest?",
      },
      {
        kind: "check",
        catalog_id: "pathcom.status_server",
        params: { server_class: "$affected_critical_class" },
        read: "How many servers were lost?",
      },
      {
        kind: "check",
        catalog_id: "tmfcom.status_audittrail",
        read: "Rule out audit pressure early on peak days (C-007).",
      },
      {
        kind: "note",
        text: "TMF is rarely the cause here, but rule it out on peak days (Maria).",
      },
      {
        kind: "action",
        catalog_id: "tacl.suspend_process",
        params: { process: "$STMT1" },
        when: "CPU 5 is the hottest survivor between 11:00 and 13:00",
        expected_effect: "CPU 5 down 12–18 points within 30 s",
        undo: "ACTIVATE $STMT1",
      },
      {
        kind: "action",
        catalog_id: "pathcom.alter_numstatic",
        params: { server_class: "ATM-AUTH", n: "+8" },
        expected_effect:
          "Queue clears and p95 returns to band within about 2 minutes",
        undo: "Restore previous NUMSTATIC",
      },
      {
        kind: "escalate",
        text: "Never reload the CPU yourself. Call HPE hardware support with the evidence pack.",
      },
      {
        kind: "note",
        text: "After repair, restore NUMSTATIC and ACTIVATE $STMT1 after 13:00.",
      },
    ],
  },
  {
    id: "PB-SC-STARVATION",
    title: "Link errors 1007/1034 on a critical class",
    version: 2,
    author: "u_maria",
    verified_by: [{ user: "u_dave", at: "2026-09-14" }],
    trigger: { failure_mode: "server_class_starvation" },
    steps: [
      {
        kind: "check",
        catalog_id: "pathcom.status_server",
        params: { server_class: "$affected_critical_class" },
        read: "Compare running servers, maximum and queue.",
      },
      {
        kind: "check",
        catalog_id: "pathcom.info_server",
        params: { server_class: "$affected_critical_class" },
        read: "Read configured limits and CPU placement.",
      },
      {
        kind: "check",
        catalog_id: "baton.recent_events",
        params: { subsystem: "PATHWAY", minutes: 5 },
        read: "Look for 1166 configuration changes before the 1034 burst.",
      },
      {
        kind: "action",
        catalog_id: "pathcom.alter_maxservers",
        params: {
          server_class: "$affected_critical_class",
          n: "$verified_limit",
        },
        when: "Running equals MAXSERVERS and requests queue; two approvals including Senior or Expert",
        expected_effect: "Allow capacity to grow within the verified limit",
      },
      {
        kind: "note",
        text: "Never raise ATM-AUTH MAXSERVERS above 40. NUMSTATIC must not exceed MAXSERVERS (PATHWAY 2049).",
      },
    ],
  },
  {
    id: "PB-AUDIT-PRESSURE",
    title: "Audit trail climbing at month-end",
    version: 4,
    author: "u_dave",
    verified_by: [{ user: "u_maria", at: "2026-09-14" }],
    trigger: { causal_template: "audit_trail_pressure" },
    steps: [
      {
        kind: "check",
        catalog_id: "tmfcom.status_audittrail",
        read: "Read fill, trend and thresholds.",
      },
      {
        kind: "check",
        catalog_id: "tacl.status_process",
        params: { process: "$MEB01" },
        read: "Confirm the month-end batch is running.",
      },
      {
        kind: "action",
        catalog_id: "tacl.suspend_process",
        params: { process: "$MEB01" },
        when: "Fill exceeds 70% and rises faster than 0.8% per minute",
        expected_effect:
          "Reduce audit generation while expert reviews dump handling",
        undo: "ACTIVATE $MEB01",
      },
      {
        kind: "escalate",
        text: "Call Maria, the TMF expert, for dump handling. Never stop TMF to relieve audit pressure.",
      },
    ],
  },
  {
    id: "PB-RUNAWAY-BATCH",
    title: "One batch process eating a CPU",
    version: 1,
    author: "u_maria",
    verified_by: [{ user: "u_dave", at: "2026-09-14" }],
    trigger: { failure_mode: "runaway_process" },
    steps: [
      {
        kind: "check",
        catalog_id: "meas.cpu_busy",
        read: "Identify the hottest CPU.",
      },
      {
        kind: "check",
        catalog_id: "tacl.status_cpu",
        params: { cpu: "$hottest_cpu" },
        read: "Identify the batch process and confirm ownership.",
      },
      {
        kind: "action",
        catalog_id: "tacl.altpri_process",
        params: { process: "$batch_process", priority: 100 },
        when: "Owner confirms the process can yield capacity",
        expected_effect: "Lower batch scheduling priority",
        undo: "Restore previous priority",
      },
      {
        kind: "note",
        text: "Lower priority first. Suspend only with the owner’s OK. Never stop without the owner.",
      },
    ],
  },
];
for (const pb of playbooks)
  await yaml(`playbooks/${pb.id}.yaml`, {
    ...pb,
    status: "verified",
    synthetic: true,
    source: source(pb.id === "PB-SC-STARVATION" ? "78" : "68"),
  });

const concepts = [
  [
    "process-pairs",
    "Process pairs",
    "A primary and backup run on different CPUs. If the primary fails, the backup can take over. A surviving backup does not mean all CPU capacity is restored.",
    "cpu",
  ],
  [
    "takeover",
    "Takeover",
    "A backup assumes the primary role after failure. Correlate takeover messages with the originating CPU event before opening separate investigations.",
    "cpu",
  ],
  [
    "cpu-loss",
    "CPU loss on NonStop",
    "Redundant processes can continue after a CPU halt while unpaired server processes on that CPU are lost. Check survivor utilization and customer-facing latency.",
    "cpu",
  ],
  [
    "server-classes",
    "Pathway server classes",
    "A named group of equivalent server processes serves a workload. Inspect running count, maximum, queue and response time together.",
    "pathway",
  ],
  [
    "links",
    "Pathway links",
    "Links connect requesters to server processes. A link-grant failure can indicate unavailable capacity rather than a broken link manager.",
    "pathway",
  ],
  [
    "numstatic-maxservers",
    "NUMSTATIC versus MAXSERVERS",
    "NUMSTATIC keeps a configured floor of static servers. MAXSERVERS limits total instances. A lower static floor can coexist with more running dynamic servers; the floor cannot exceed the ceiling.",
    "pathway",
  ],
  [
    "tmf-audit",
    "TMF audit trails",
    "TMF records transaction changes for recovery. Trail pressure can constrain new work even when CPU utilization is otherwise healthy.",
    "tmf",
  ],
  [
    "audit-overflow",
    "Audit overflow thresholds",
    "TORBANK uses synthetic guards at 80% overflow and 90% begin-transaction disable. These are demo configuration values; read the live trail before proposing action.",
    "tmf",
  ],
  [
    "n1-headroom",
    "N-1 headroom",
    "Ask whether the node can carry its workload after losing one CPU. Baton projects each loss using backup placement and lost server capacity. A risk warning can precede any current service breach.",
    "cpu",
  ],
  [
    "measure-cpu-busy",
    "Reading CPU busy",
    "Utilization shows how occupied a processor is during the measurement interval. Compare survivors, batch placement and service latency; high busy alone does not identify the cause.",
    "cpu",
  ],
  [
    "ems-collector",
    "EMS collectors",
    "Collectors gather subsystem events into an event log for distribution. Keep event provenance when reducing repeated messages into episodes.",
    "ems",
  ],
  [
    "ems-distributor",
    "EMS distributors",
    "Printing distributors produce operator-readable event text. Consumer distributors expose events to applications, and forwarding distributors send events to another node.",
    "ems",
  ],
  [
    "latency-p95",
    "p95 service latency",
    "95% of sampled requests complete at or below this value. Compare with the expected calendar band and timeout rate rather than reading the average alone.",
    "service",
  ],
  [
    "baseline-band",
    "Calendar baseline bands",
    "A service band represents expected behavior at this simulated time and load. Black Friday demand differs from an ordinary weekday. A synthetic band is not a production guarantee.",
    "service",
  ],
  [
    "queue-capacity",
    "Queues and capacity",
    "A queue forms when offered work exceeds available service capacity. Inspect running versus maximum, CPU load and recent changes to distinguish lost capacity from a configured ceiling.",
    "pathway",
  ],
  [
    "critical-processes",
    "Protected processes",
    "TORBANK protects PATHMON, disk processes and link managers. A generic suspend request cannot bypass target protection. Use the approved escalation path.",
    "governance",
  ],
  [
    "two-person",
    "Two-person approval",
    "An impactful T2 change needs distinct approvals and at least one senior operator or expert. The first approval remains visible while the action waits.",
    "governance",
  ],
  [
    "earned-autonomy",
    "Earned autonomy",
    "The trust ledger records outcomes per catalog template, parameter class and role. L2 permits approved read-only automation after an expert grants it; an eligible counter does not grant itself.",
    "governance",
  ],
  [
    "recovery-verification",
    "Verifying recovery",
    "The CPU-loss scenario requires ATM p95 back within its band for 60 simulated seconds and the hottest CPU below 90%. A single improved sample is not recovery.",
    "service",
  ],
  [
    "temporary-mitigations",
    "Temporary mitigations and undo",
    "Suspending batch and adding static servers buy time. Record inverses, verify service recovery, and retain a follow-up to restore configuration after hardware repair.",
    "governance",
  ],
];
await jsonl(
  "concepts.jsonl",
  concepts.map(([id, title, text, component]) =>
    chunk(
      `concept:${id}`,
      "concept",
      title,
      text,
      { components: [component] },
      component === "pathway"
        ? "78"
        : component === "cpu" || component === "tmf"
          ? "68"
          : "01",
    ),
  ),
);

const catalog = spec
  .split("### 8.1 Catalog")[1]
  .split("The validator enforces")[0];
const commands = catalog
  .split("\n")
  .filter((line) => line.startsWith("| `"))
  .map((line) => {
    const parts = line
      .split("|")
      .slice(1, -1)
      .map((s) => s.trim().replaceAll("`", ""));
    const [id, interpreter, syntax, tier, parameters, undo, fields] = parts;
    const title = id.split(".").slice(1).join(" ").replaceAll("_", " ");
    return {
      ...chunk(
        `cmdref:${id}`,
        "command_ref",
        title,
        `${title}. Simulated syntax: ${interpreter}; ${syntax}. Output: ${fields}. Read the output against inventory, baseline and policy before acting.`,
        { catalog_id: id, subsystem: id.split(".")[0] },
        id.startsWith("pathcom") ? "78" : "01",
      ),
      catalog_id: id,
      purpose: title,
      syntax,
      interpreter,
      syntax_status: "simulated",
      parameters,
      output_fields: fields,
      how_to_read: `Inspect ${fields.toLowerCase()}; compare with current inventory and evidence.`,
      cautions: tier.startsWith("T3")
        ? "Blocked in Baton; use human escalation."
        : tier.startsWith("T0")
          ? "Read-only, still subject to backend validation and role autonomy."
          : "State change; backend policy and approvals required.",
      tier,
      undo,
    };
  });
await jsonl("command_reference.jsonl", commands);

const appendix = spec
  .split("## Appendix A: EMS message set")[1]
  .split("**S1 triggers:**")[0];
const descriptions = {
  "OMF:100": [
    "CPU monitoring reports an up state.",
    "Processor availability changed.",
    "Confirm expected recovery and rebalance only after repair.",
  ],
  "OMF:101": [
    "CPU utilization crossed its configured guard.",
    "Less spare capacity remains.",
    "Inspect survivor demand and batch work.",
  ],
  "OMF:102": [
    "A CPU is fully occupied.",
    "Services on this CPU may slow.",
    "Inspect the leading capacity hypothesis.",
  ],
  "OMF:103": [
    "A monitored CPU is down.",
    "Primaries may take over and unpaired servers may be lost.",
    "Check survivors; escalate hardware repair.",
  ],
  "OMF:217": [
    "The disk primary CPU is inaccessible.",
    "The surviving backup may continue service.",
    "Check disk paths; do not restart protected processes.",
  ],
  "PATHWAY:1034": [
    "No server is available for the requested link.",
    "The requester remains unlinked.",
    "Inspect capacity and configured limits.",
  ],
  "PATHWAY:1077": [
    "The PATHMON backup has taken over.",
    "Management continues on its backup CPU.",
    "Correlate with the originating fault.",
  ],
  "PATHWAY:1093": [
    "The backup processor is down.",
    "This process lacks its former redundancy.",
    "Escalate repair with CPU evidence.",
  ],
};
const opmessages = appendix
  .split("\n")
  .filter((line) => /^\| (OMF|PATHWAY|APP) \|/.test(line))
  .map((line, i) => {
    const p = line
      .split("|")
      .slice(1, -1)
      .map((s) => s.trim());
    const subsystem = p[0],
      number = Number(p[1]);
    let text = p[2].replaceAll("`", "");
    if (text.startsWith("Same as 101"))
      text =
        "CPU {cpu}, Current State = FULL, Previous State = {prev}, Current Usage = {usage}, Configured Threshold = {thr}, Sampling Interval = {n} minutes";
    if (text.startsWith("Same as 1203"))
      text =
        "TMF Audit Trail File {id}, Current State = OVER THRESHOLD, Current Usage = {usage}, Configured Threshold = {thr}";
    const info = descriptions[`${subsystem}:${number}`] || [
      "A monitored object changed or reported activity.",
      "Read current state with related events.",
      "Use the scoped playbook and validated catalog checks.",
    ];
    return {
      id: `opmsg:${subsystem}:${number}${subsystem === "APP" ? `:${i}` : ""}`,
      doc_type: "operator_message",
      subsystem,
      number,
      text_template: text,
      variables: [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]),
      cause: info[0],
      effect: info[1],
      recovery: info[2],
      critical: p[3] === "yes",
      severity_hint: p[3] === "yes" ? 4 : subsystem === "APP" ? 1 : 3,
      real: subsystem !== "APP",
      synthetic: true,
      synthetic_note:
        subsystem === "APP"
          ? "Invented application chatter"
          : "Real message identifiers; MVP fallback templates and synthetic brief annotations; state words and simplified layout may be simulated.",
      source: source(
        subsystem === "PATHWAY" ? "78" : subsystem === "OMF" ? "68" : "01",
      ),
      status: "active",
    };
  });
opmessages.push({
  id: "opmsg:PATHWAY:2049",
  doc_type: "operator_message",
  subsystem: "PATHWAY",
  number: 2049,
  text_template: "NUMSTATIC EXCEEDS MAXSERVERS",
  variables: [],
  cause: "The requested static server count exceeds the configured maximum.",
  effect: "The parameter combination is invalid.",
  recovery:
    "Keep the static count at or below the maximum and resubmit a validated change.",
  critical: false,
  severity_hint: 2,
  real: true,
  synthetic: true,
  synthetic_note: "MVP-supplied message text with short synthetic annotations.",
  source: source("78"),
  status: "active",
});
await jsonl("operator_messages.jsonl", opmessages);

const incidentSection = spec
  .split("**Past incidents**")[1]
  .split("## Appendix D")[0];
const incidents = [
  ...incidentSection.matchAll(/^\d+\. (INC-[\d-]+): (.*)$/gm),
].map(([, id, text]) => ({
  ...chunk(`incident:${id}`, "incident", id, text, { site: "TORBANK" }),
  display_id: id,
  summary: text,
  status: "resolved",
  synthetic: true,
}));
await jsonl("incidents.jsonl", incidents);

const glossarySection = full.split("## 22. Glossary")[1].split("## 23.")[0];
const glossary = glossarySection
  .split("\n")
  .filter((line) => line.startsWith("| ") && !/^\| (Term|---)/.test(line))
  .map((line) =>
    line
      .split("|")
      .slice(1, -1)
      .map((s) => s.trim()),
  );
const extras = [
  ["NUMSTATIC", "Configured floor of static servers.", "static servers"],
  [
    "MAXSERVERS",
    "Upper bound on server processes in a class.",
    "server ceiling",
  ],
  [
    "ATM-AUTH",
    "Synthetic critical server class for ATM authorization.",
    "atm auth, withdrawals",
  ],
  [
    "POS-AUTH",
    "Synthetic critical server class for POS authorization.",
    "point of sale",
  ],
  [
    "MAT fill",
    "Percentage of the synthetic master audit trail in use.",
    "audit fill",
  ],
];
const terms = [...glossary, ...extras]
  .slice(0, 60)
  .map(([term, definition, aliases]) => ({
    ...chunk(`glossary:${slug(term)}`, "glossary", term, definition),
    term,
    definition,
    synonyms: aliases
      ? aliases.split(", ")
      : term.split(/, | \/ /).map((t) => t.trim()),
  }));
await jsonl("glossary.jsonl", terms);

const manifest = {
  synthetic: true,
  source_spec: "BATON_MVP_SPEC.md §10.1 / §16 / Appendix C",
  operator_message_mode:
    "Appendix A fallback; full manual crawl is an Engine/human follow-up",
  counts: {
    operator_messages: opmessages.length,
    command_reference: commands.length,
    concepts: concepts.length,
    playbooks: playbooks.length,
    claims: claims.length,
    verified_claims: claims.filter((c) => c.status === "verified").length,
    pending_claims: claims.filter((c) => c.status === "pending_review").length,
    incidents: incidents.length,
    glossary: terms.length,
  },
};
await yaml("manifest.json", manifest);
await fs.mkdir(path.join(root, "frontend/src/mocks"), { recursive: true });
await fs.writeFile(
  path.join(root, "frontend/src/mocks/content.json"),
  JSON.stringify({
    claims,
    playbooks,
    concepts: concepts.map(([id, title, text]) => ({
      id: `concept:${id}`,
      title,
      text,
    })),
    commands,
    incidents,
    glossary: terms,
    operator_messages: opmessages,
  }),
);
console.log(JSON.stringify(manifest.counts));
