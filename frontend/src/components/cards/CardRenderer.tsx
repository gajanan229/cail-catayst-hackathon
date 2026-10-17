import { useEffect, useState } from "react";
import {
  ArrowRight,
  Check,
  ChevronDown,
  CirclePause,
  Clock3,
  FileText,
  LockKeyhole,
  ShieldCheck,
  Undo2,
  UserRoundCheck,
  X,
} from "lucide-react";
import type { Approval, Card, Schema } from "@/api/types";
import { api, mutate } from "@/api/client";
import { useConsole } from "@/realtime/store";
import { Badge, Tier, Why, ActorStamp } from "../common";
import { Button } from "../ui/button";
import { Dialog } from "../ui/dialog";
import { cn, human } from "@/lib/utils";
import { SafeMarkdown } from "../Markdown";

export type Inspect = (id: string) => void;
export function Citations({ card, inspect }: { card: Card; inspect: Inspect }) {
  return (
    <div className="citations">
      {card.citations?.map((c) => (
        <button
          key={c.id}
          className="citation"
          onClick={() => inspect(c.id)}
          title={`Open source: ${c.id}`}
        >
          <FileText size={10} />
          {c.label}
        </button>
      ))}
    </div>
  );
}
export function ApprovalProgress({ approval }: { approval: Approval }) {
  const users = useConsole((s) => s.users);
  return (
    <div className="approval-progress">
      <div>
        <UserRoundCheck size={13} />
        <strong>
          {approval.progress_text ||
            `${approval.decisions.filter((d) => d.decision !== "reject").length} of ${approval.required.count} approvals`}
        </strong>
      </div>
      <div className="approval-people">
        {approval.decisions.map((d) => (
          <Badge key={d.actor} tone={d.decision === "reject" ? "crit" : "ok"}>
            {users.find((u) => u.id === d.actor)?.name ||
              d.actor_name ||
              d.actor}{" "}
            {d.decision === "reject" ? <X size={10} /> : <Check size={10} />}
          </Badge>
        ))}
        {approval.status === "partially_approved" && (
          <Badge tone="warn">
            <CirclePause size={10} /> Senior or Expert needed
          </Badge>
        )}
      </div>
    </div>
  );
}
export function CardRenderer({
  card,
  inspect,
  navigate,
}: {
  card: Card;
  inspect: Inspect;
  navigate: (route: string) => void;
}) {
  const source = card.source;
  return (
    <article
      id={card.id}
      className={cn(
        "baton-card",
        `card-${card.type}`,
        card.status === "blocked" && "blocked",
      )}
      aria-label={card.title}
    >
      {card.type !== "command" && (
        <div className="card-kicker">
          <span>
            {card.type === "hypotheses"
              ? "Working diagnosis"
              : card.type === "expert"
                ? "From your experts"
                : human(card.type)}
          </span>
          {source && <Badge>{source}</Badge>}
        </div>
      )}
      {card.type === "command" ? (
        <CommandCard card={card} inspect={inspect} />
      ) : card.type === "hypotheses" ? (
        <Hypotheses card={card} inspect={inspect} />
      ) : card.type === "decision" ? (
        <Decision card={card} />
      ) : card.type === "expert" ? (
        <>
          <h3>
            {card.body.title}
            <span className="version">v{card.body.version}</span>
          </h3>
          <p>{card.body.tip}</p>
          <div className="expert-provenance">
            <span className="avatar">
              {card.body.author.name.slice(0, 2).toUpperCase()}
            </span>
            <div>
              <strong>{card.body.author.name}’s playbook</strong>
              <span>
                <ShieldCheck size={12} /> Verified by{" "}
                {card.body.verified_by.map((p) => p.name).join(", ")}
              </span>
            </div>
            <Badge>synthetic</Badge>
          </div>
          <details>
            <summary>
              View playbook steps <ChevronDown size={12} />
            </summary>
            <ol>
              {card.body.steps.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ol>
            <p className="meta">Last validated {card.body.last_validated}</p>
          </details>
        </>
      ) : card.type === "situation" ? (
        <>
          <div className="row-between">
            <Badge tone="crit">Severity {card.body.severity} · Critical</Badge>
            <span className="meta">{card.body.age_s}s ago</span>
          </div>
          <h3>{card.title}</h3>
          <p className="collapse-line">
            <strong>{card.body.counts.raw_events.toLocaleString()}</strong>{" "}
            events <ArrowRight size={14} />
            <strong>1</strong> situation
          </p>
          <Button variant="ghost" onClick={() => navigate("/incidents")}>
            Open Incident Room <ArrowRight size={13} />
          </Button>
        </>
      ) : card.type === "text" ? (
        <>
          <h3>{card.title}</h3>
          <SafeMarkdown>{card.body.markdown}</SafeMarkdown>
        </>
      ) : card.type === "verification" ? (
        <>
          <div className="verification-title">
            <Check size={20} />
            <h3>{card.title}</h3>
          </div>
          {card.body.criteria.map((c, i) => (
            <div
              key={i}
              className={cn("criterion", c.met ? "ok-text" : "warn-text")}
            >
              {c.met ? <Check size={14} /> : <Clock3 size={14} />}
              <div>
                {c.text}
                <span className="meta">{c.value}</span>
              </div>
            </div>
          ))}
        </>
      ) : card.type === "evidence" ? (
        <>
          <h3>{card.title}</h3>
          <div className="evidence-list">
            {card.body.items.map((e) => (
              <button key={String(e.id)} onClick={() => inspect(String(e.id))}>
                <FileText size={14} />
                <span>
                  <strong>{String(e.label)}</strong>
                  <small>
                    {typeof e.preview === "string"
                      ? e.preview
                      : String(e.source || "")}
                  </small>
                </span>
                <ArrowRight size={12} />
              </button>
            ))}
          </div>
        </>
      ) : card.type === "plan" ? (
        <PlanCard card={card} />
      ) : card.type === "escalation" ? (
        <>
          <h3>
            <LockKeyhole size={15} /> {card.title}
          </h3>
          <p>{card.body.reason}</p>
          <p>
            {typeof card.body.contact === "string"
              ? card.body.contact
              : JSON.stringify(card.body.contact)}
          </p>
          <Button
            onClick={() => navigator.clipboard.writeText(card.body.summary)}
          >
            Copy evidence summary
          </Button>
        </>
      ) : card.type === "postmortem" ? (
        <>
          <h3>{card.title}</h3>
          <p>{card.body.summary}</p>
          <Button onClick={() => navigate("/incidents?tab=postmortem")}>
            Read postmortem <ArrowRight size={13} />
          </Button>
        </>
      ) : card.type === "claim_review" ? (
        <>
          <h3>{card.title}</h3>
          <p>{card.body.statement}</p>
          <Button onClick={() => navigate("/knowledge")}>
            Review in Knowledge Studio <ArrowRight size={13} />
          </Button>
        </>
      ) : null}
      <Citations card={card} inspect={inspect} />
    </article>
  );
}
function CommandCard({
  card,
  inspect,
}: {
  card: Schema<"CommandCard">;
  inspect: Inspect;
}) {
  const b = card.body;
  const readOnly = useConsole((s) => s.readOnly);
  const connected = useConsole((s) => s.connected);
  const approvals = useConsole((s) => s.approvals);
  const actor = useConsole((s) => s.actor);
  const approval = approvals.find((a) => a.id === b.approval_id);
  const [mode, setMode] = useState<"approve" | "edit" | "reject" | null>(null);
  const [reason, setReason] = useState("");
  const [comment, setComment] = useState("");
  const [params, setParams] = useState(b.params || {});
  const [preview, setPreview] =
    useState<Schema<"CommandPreviewResponse"> | null>(null);
  const [validating, setValidating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const disabled =
    !connected ||
    (readOnly && b.tier !== "T0") ||
    !!approval?.decisions.some((d) => d.actor === actor) ||
    card.status === "blocked";
  useEffect(() => {
    if (mode !== "edit") return;
    let cancelled = false;
    setValidating(true);
    setPreview(null);
    const timer = setTimeout(() => {
      api<Schema<"CommandPreviewResponse">>("/commands/preview", {
        catalog_id: b.catalog_id,
        params,
      })
        .then((p) => {
          if (!cancelled) {
            setPreview(p);
            setError("");
          }
        })
        .catch((e) => {
          if (!cancelled) setError(String(e));
        })
        .finally(() => {
          if (!cancelled) setValidating(false);
        });
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [params, mode, b.catalog_id]);
  const decide = async () => {
    setBusy(true);
    setError("");
    try {
      if (!b.approval_id)
        throw new Error("No approval record is attached to this command.");
      await mutate(`/approvals/${b.approval_id}/decide`, {
        decision:
          mode === "reject"
            ? "reject"
            : mode === "edit"
              ? "edit_approve"
              : "approve",
        ...(mode === "edit" ? { params } : {}),
        ...(mode === "reject" ? { reason_code: reason, comment } : {}),
      });
      setMode(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <div className="row-between">
        <div className="inline-gap">
          <Tier tier={b.tier} />
          <Badge tone="baton">
            {b.autonomy?.level} ·{" "}
            {b.autonomy?.level === "L2" ? "auto" : "approval"}
          </Badge>
        </div>
        <Badge
          tone={
            card.status === "done"
              ? "ok"
              : card.status === "blocked"
                ? "neutral"
                : "warn"
          }
        >
          {card.status === "done" ? (
            <Check size={10} />
          ) : card.status === "blocked" ? (
            <LockKeyhole size={10} />
          ) : (
            <Clock3 size={10} />
          )}{" "}
          {human(card.status)}
        </Badge>
      </div>
      <h3>{card.title}</h3>
      <code className="command-code">{b.rendered}</code>
      <p>{b.purpose}</p>
      <div className="command-context">
        <span>Expected</span>
        <p>{b.expected}</p>
        <span>Risk</span>
        <p>{b.risks || "No risk detail supplied"}</p>
        <span>Undo</span>
        <code>{b.undo?.rendered || "No state change"}</code>
      </div>
      <div className="autonomy-line">
        <ShieldCheck size={12} />
        {b.autonomy?.progress}
        {b.autonomy?.granted_by && ` · granted by ${b.autonomy?.granted_by}`}
      </div>
      <Why explanation={b.policy.explanation} rules={b.policy.rule_ids} />
      {b.policy.escalation && (
        <p className="warn-text">{b.policy.escalation}</p>
      )}
      {approval && <ApprovalProgress approval={approval} />}
      {["awaiting_approval", "partially_approved", "proposed"].includes(
        card.status,
      ) && (
        <>
          <div className="card-actions">
            <Button
              variant="default"
              disabled={disabled}
              onClick={() => {
                setMode("approve");
                setError("");
              }}
            >
              Approve <ArrowRight size={12} />
            </Button>
            <Button
              disabled={!connected}
              onClick={() => {
                setParams(b.params || {});
                setMode("edit");
                setError("");
              }}
            >
              Edit
            </Button>
            <Button
              variant="ghost"
              disabled={!connected}
              onClick={() => {
                setMode("reject");
                setError("");
              }}
            >
              Reject
            </Button>
            <ActorStamp />
          </div>
          {readOnly && b.tier !== "T0" && (
            <p className="warn-text meta">Read-only mode</p>
          )}
          {approval?.decisions.some((d) => d.actor === actor) && (
            <p className="meta">
              {approval.status === "partially_approved"
                ? "Your approval is recorded. Switch persona for the second approval."
                : "Your approval is recorded. Waiting for the execution result."}
            </p>
          )}
        </>
      )}
      {b.execution && (
        <details className="execution-detail">
          <summary>
            <Check size={12} /> {b.execution.summary || "Command completed"}{" "}
            <ChevronDown size={12} />
          </summary>
          <div className="facts-grid">
            {b.execution.facts_table?.map((f) => (
              <button
                key={f.label}
                onClick={() => inspect(b.execution!.exec_id)}
              >
                <span>{f.label}</span>
                <strong>{f.value}</strong>
              </button>
            ))}
          </div>
          <pre>{b.execution.raw_output}</pre>
          {b.undo && (
            <Button
              disabled={readOnly || !connected}
              onClick={() =>
                void mutate(`/executions/${b.execution!.exec_id}/undo`).catch(
                  () => {},
                )
              }
            >
              <Undo2 size={13} /> Propose undo
            </Button>
          )}
        </details>
      )}
      <Dialog
        open={mode !== null}
        onOpenChange={(o) => !o && setMode(null)}
        title={
          mode === "reject"
            ? "Reject command"
            : mode === "edit"
              ? "Edit & approve command"
              : "Approve command"
        }
        description="Your decision is recorded with your current persona."
      >
        <ActorStamp />
        <code className="command-code">
          {mode === "edit" ? preview?.rendered || b.rendered : b.rendered}
        </code>
        {mode === "edit" && (
          <div className="form-fields">
            {Object.entries(params).length ? (
              Object.entries(params).map(([key, value]) => (
                <label key={key}>
                  {human(key)}
                  <input
                    value={String(value)}
                    onChange={(e) =>
                      setParams({
                        ...params,
                        [key]:
                          typeof value === "number"
                            ? Number(e.target.value)
                            : e.target.value,
                      })
                    }
                  />
                </label>
              ))
            ) : (
              <p className="muted">This command has no editable parameters.</p>
            )}
            {validating ? (
              <p className="meta">Validating against live inventory…</p>
            ) : preview?.valid ? (
              <p className="ok-text">✓ Parameters validated by backend</p>
            ) : (
              preview?.errors.map((e, i) => (
                <p className="crit-text" key={i}>
                  {typeof e === "string" ? e : JSON.stringify(e)}
                </p>
              ))
            )}
          </div>
        )}
        <div className="confirmation-detail">
          <p>
            <strong>Risk</strong> {b.risks}
          </p>
          <p>
            <strong>Undo</strong> {b.undo?.rendered || "No state change"}
          </p>
          <p>
            <strong>Policy</strong>{" "}
            {preview?.policy?.explanation || b.policy.explanation}
          </p>
        </div>
        {mode === "reject" && (
          <>
            <label>
              Reason code
              <select
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              >
                <option value="">Choose a reason</option>
                {[
                  "wrong_command",
                  "wrong_target",
                  "unsafe_now",
                  "not_needed",
                  "other",
                ].map((r) => (
                  <option key={r} value={r}>
                    {human(r)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Comment (optional)
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
              />
            </label>
          </>
        )}
        {error && (
          <p role="alert" className="crit-text">
            {error}
          </p>
        )}
        <div className="dialog-actions">
          <Button onClick={() => setMode(null)}>Cancel</Button>
          <Button
            variant={mode === "reject" ? "destructive" : "default"}
            disabled={
              busy ||
              (!reason && mode === "reject") ||
              (mode === "edit" &&
                (!preview?.valid ||
                  validating ||
                  preview.policy?.effect === "deny")) ||
              (mode !== "reject" && disabled)
            }
            onClick={() => void decide()}
          >
            {busy
              ? "Saving…"
              : mode === "reject"
                ? "Reject with reason"
                : `Confirm as ${useConsole.getState().users.find((u) => u.id === actor)?.name || "operator"}`}
          </Button>
        </div>
      </Dialog>
    </>
  );
}
function Hypotheses({
  card,
  inspect,
}: {
  card: Schema<"HypothesesCard">;
  inspect: Inspect;
}) {
  return (
    <>
      <div className="row-between">
        <h3>What’s causing this?</h3>
        <span className="meta">Round {card.body.round}</span>
      </div>
      <div className="hypotheses">
        {[...card.body.hypotheses]
          .sort((a, b) => b.p - a.p)
          .map((h, i) => (
            <details
              key={h.id}
              className={cn("hypothesis", i === 0 && "leading")}
              open={i === 0}
            >
              <summary>
                <span className="hypothesis-label">{h.label}</span>
                <strong>
                  {Math.round(h.p * 100)}
                  <small>%</small>
                </strong>
                <div className="probability-track">
                  <i style={{ width: `${h.p * 100}%` }} />
                </div>
              </summary>
              <div className="hypothesis-evidence">
                {h.for.map((e) => (
                  <button
                    key={e.evidence_id}
                    onClick={() => inspect(e.evidence_id)}
                  >
                    <span className="ok-text">+</span>
                    {e.label}
                  </button>
                ))}
                {h.against.map((e) => (
                  <button
                    key={e.evidence_id}
                    onClick={() => inspect(e.evidence_id)}
                  >
                    <span className="warn-text">−</span>
                    {e.label}
                  </button>
                ))}
              </div>
              {h.would_change_mind && (
                <p className="meta">
                  Would change the ranking: {h.would_change_mind}
                </p>
              )}
            </details>
          ))}
      </div>
      <div className="stop-rule">
        <ShieldCheck size={12} />
        {card.body.stop_rule.met
          ? "Enough evidence to propose actions"
          : "Gathering evidence · awaiting next check"}
      </div>
    </>
  );
}
function Decision({ card }: { card: Schema<"DecisionCard"> }) {
  const [selected, setSelected] = useState<string[]>(
    card.body.selected?.length
      ? card.body.selected
      : card.body.options.find((o) => o.recommended)?.includes || [],
  );
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const readOnly = useConsole((s) => s.readOnly);
  const actor = useConsole((s) => s.actor);
  const connected = useConsole((s) => s.connected);
  const approvals = useConsole((s) => s.approvals);
  const options = card.body.options;
  const chosen = options.filter(
    (o) =>
      selected.includes(o.id) &&
      !o.includes.length &&
      !o.blocked &&
      o.steps.length,
  );
  const pending = chosen.filter((o) => {
    const approval =
      approvals.find((a) => a.id === o.approval_id) ||
      approvals.find((a) => a.option_ids.includes(o.id));
    return (
      o.status !== "executed" &&
      !["approved", "rejected", "expired"].includes(approval?.status || "")
    );
  });
  const decide = async () => {
    setBusy(true);
    setError("");
    try {
      const hasOptionApprovals = pending.some(
        (o) =>
          o.approval_id || approvals.some((a) => a.option_ids.includes(o.id)),
      );
      if (card.body.approval_id && !hasOptionApprovals) {
        await mutate(`/approvals/${card.body.approval_id}/decide`, {
          decision: "approve",
          option_ids: pending.map((o) => o.id),
        });
        setConfirm(false);
        return;
      }
      for (const option of pending) {
        const approval =
          approvals.find((a) => a.id === option.approval_id) ||
          approvals.find(
            (a) =>
              a.option_ids.includes(option.id) &&
              ["pending", "partially_approved"].includes(a.status),
          );
        const approvalId =
          approval?.id || option.approval_id || card.body.approval_id;
        if (approval?.decisions.some((d) => d.actor === actor)) continue;
        if (!approvalId)
          throw new Error(
            "The backend has not attached an approval record to this option yet.",
          );
        await mutate(`/approvals/${approvalId}/decide`, {
          decision: "approve",
          option_ids: [option.id],
        });
      }
      setConfirm(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <div className="row-between">
        <h3>Choose a recovery plan</h3>
        {card.body.options.find((o) => o.recommended) && (
          <Badge tone="baton">
            {card.body.options.find((o) => o.recommended)!.label} recommended
          </Badge>
        )}
      </div>
      <p className="meta">
        Review the cited recommendation, risks and recovery actions.
      </p>
      <div className="decision-options">
        {options
          .filter((o) => !o.includes.length)
          .map((o) => (
            <div
              key={o.id}
              className={cn(
                "decision-option",
                selected.includes(o.id) && "selected",
                o.blocked && "option-blocked",
              )}
            >
              <label className="option-select">
                {o.blocked ? (
                  <LockKeyhole size={14} />
                ) : o.steps.length ? (
                  <input
                    type="checkbox"
                    checked={selected.includes(o.id)}
                    disabled={readOnly || o.status === "executed"}
                    onChange={(e) =>
                      setSelected(
                        e.target.checked
                          ? [...selected, o.id]
                          : selected.filter((x) => x !== o.id),
                      )
                    }
                  />
                ) : (
                  <span className="muted">—</span>
                )}
                <strong>{o.label}</strong>
                {o.tier && <Tier tier={o.tier} />}
              </label>
              {o.steps.map((s) => (
                <div key={s.catalog_id}>
                  <code className="option-command">{s.rendered}</code>
                  <p className="meta">
                    <Undo2 size={11} /> {s.undo || "No undo available"}
                  </p>
                </div>
              ))}
              <p>{o.expected_effect || o.block_reason}</p>
              {o.risks && <p className="meta">Risk: {o.risks}</p>}
              {o.escalation && <p className="warn-text meta">{o.escalation}</p>}
              {o.required_approvers && (
                <span className="meta">
                  {o.required_approvers}{" "}
                  {o.required_approvers === 1
                    ? "approval"
                    : "approvals · includes Senior or Expert"}
                </span>
              )}
              {!o.blocked &&
                o.steps.length === 1 &&
                o.status !== "executed" && (
                  <OptionEditor
                    option={o}
                    approvalId={
                      o.approval_id ||
                      approvals.find((a) => a.option_ids.includes(o.id))?.id ||
                      null
                    }
                  />
                )}
              <Why
                explanation={
                  o.block_reason ||
                  `Backend requires ${o.required_approvers || 0} approval(s) for this option. ${o.recommender ? `Source: ${o.recommender.id}.` : ""}`
                }
                rules={
                  o.blocked
                    ? ["t3-block"]
                    : o.tier === "T2"
                      ? ["t2-two-person"]
                      : o.tier === "T1"
                        ? ["t1-single"]
                        : []
                }
              />
              {o.status === "executed" && (
                <Badge tone="ok">
                  <Check size={11} /> Executed
                </Badge>
              )}
              {approvals
                .filter((a) => a.option_ids.includes(o.id))
                .map((a) => (
                  <ApprovalProgress key={a.id} approval={a} />
                ))}
            </div>
          ))}
      </div>
      <div className="card-actions">
        <Button
          variant="default"
          disabled={readOnly || !connected || !pending.length}
          onClick={() => {
            setConfirm(true);
            setError("");
          }}
        >
          Approve selected <ArrowRight size={13} />
        </Button>
        <ActorStamp />
      </div>
      {readOnly && <p className="warn-text">Read-only mode</p>}
      <Dialog
        open={confirm}
        onOpenChange={setConfirm}
        title="Confirm recovery actions"
        description="T2 changes require two distinct approvers, including a Senior or Expert. Each selected option is approved separately."
      >
        <ActorStamp />
        {pending.map((o) => (
          <div className="confirmation-detail" key={o.id}>
            <h3>{o.label}</h3>
            {o.steps.map((s) => (
              <div key={s.catalog_id}>
                <code className="command-code">{s.rendered}</code>
                <p>
                  <strong>Undo:</strong> {s.undo || "None"}
                </p>
              </div>
            ))}
            <p>
              <strong>Risk:</strong> {o.risks}
            </p>
            <p>
              {o.required_approvers} approval(s) required. The first approval
              only executes actions whose requirements are fully met.
            </p>
          </div>
        ))}
        {error && (
          <p className="crit-text" role="alert">
            {error}
          </p>
        )}
        <div className="dialog-actions">
          <Button onClick={() => setConfirm(false)}>Cancel</Button>
          <Button
            variant="default"
            disabled={busy || readOnly || !connected}
            onClick={() => void decide()}
          >
            {busy ? "Recording…" : "Confirm selected actions"}
          </Button>
        </div>
      </Dialog>
    </>
  );
}

function PlanCard({ card }: { card: Schema<"PlanCard"> }) {
  const approvals = useConsole((s) => s.approvals);
  const connected = useConsole((s) => s.connected);
  const actor = useConsole((s) => s.actor);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const steps = card.body.steps.filter(
    (s) => s.tier === "T0" && s.status === "awaiting_approval",
  );
  const pending = approvals.filter(
    (a) =>
      a.tier === "T0" &&
      a.status === "pending" &&
      a.step_ids.some((id) => steps.some((s) => s.step_id === id)),
  );
  return (
    <>
      <h3>{card.title}</h3>
      <p>{card.body.rationale}</p>
      {card.body.steps.map((s) => (
        <div className="plan-step" key={s.step_id}>
          <Tier tier={s.tier} />
          <code>{s.rendered}</code>
          <Badge>{human(s.status)}</Badge>
        </div>
      ))}
      {card.actions.includes("approve_all_readonly") && (
        <Button
          variant="default"
          disabled={!connected || !pending.length}
          onClick={() => setOpen(true)}
        >
          Approve all read-only
        </Button>
      )}
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title="Approve read-only checks"
        description="Only T0 checks are included. State-changing steps retain their individual approval gates."
      >
        <ActorStamp />
        {pending.map((a) => (
          <div className="confirmation-detail" key={a.id}>
            {a.rendered.map((r) => (
              <code className="command-code" key={r}>
                {r}
              </code>
            ))}
            <p>Risk: read-only; negligible load. Undo: no state change.</p>
            <Why
              explanation={a.policy?.explanation || "Backend requires approval"}
              rules={a.policy?.rule_ids}
            />
          </div>
        ))}
        {error && <p className="crit-text">{error}</p>}
        <div className="dialog-actions">
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            variant="default"
            disabled={busy || !connected}
            onClick={() => {
              setBusy(true);
              setError("");
              void (async () => {
                try {
                  for (const a of pending)
                    await mutate(`/approvals/${a.id}/decide`, {
                      decision: "approve",
                    });
                  setOpen(false);
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  setBusy(false);
                }
              })();
            }}
          >
            Confirm read-only checks
          </Button>
        </div>
      </Dialog>
    </>
  );
}

function OptionEditor({
  option,
  approvalId,
}: {
  option: Schema<"DecisionOption">;
  approvalId: string | null;
}) {
  const [open, setOpen] = useState(false);
  const [params, setParams] = useState(option.steps[0].params);
  const [preview, setPreview] =
    useState<Schema<"CommandPreviewResponse"> | null>(null);
  const [validating, setValidating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const readOnly = useConsole((s) => s.readOnly);
  const connected = useConsole((s) => s.connected);
  const step = option.steps[0];
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setValidating(true);
    setPreview(null);
    const t = setTimeout(() => {
      void api<Schema<"CommandPreviewResponse">>("/commands/preview", {
        catalog_id: step.catalog_id,
        params,
      })
        .then((p) => {
          if (!cancelled) setPreview(p);
        })
        .catch((e) => {
          if (!cancelled) setError((e as Error).message);
        })
        .finally(() => {
          if (!cancelled) setValidating(false);
        });
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [open, params, step.catalog_id]);
  return (
    <>
      <Button
        size="sm"
        variant="ghost"
        disabled={readOnly || !connected || !approvalId}
        onClick={() => {
          setParams(step.params);
          setError("");
          setOpen(true);
        }}
      >
        Edit parameters
      </Button>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title="Edit & approve recovery action"
        description="Parameters are validated against live inventory and current policy before you can confirm."
      >
        <ActorStamp />
        {Object.entries(params).map(([key, value]) => (
          <label key={key}>
            {human(key)}
            <input
              value={String(value)}
              onChange={(e) =>
                setParams({
                  ...params,
                  [key]:
                    typeof value === "number"
                      ? Number(e.target.value)
                      : e.target.value,
                })
              }
            />
          </label>
        ))}
        <code className="command-code">
          {preview?.rendered || step.rendered}
        </code>
        {validating ? (
          <p className="meta">Checking parameters…</p>
        ) : (
          preview?.errors.map((e, i) => (
            <p className="crit-text" key={i}>
              {e}
            </p>
          ))
        )}
        <p>Risk: {option.risks}</p>
        <p>Undo: {step.undo || "None"}</p>
        <Why
          explanation={
            preview?.policy?.explanation ||
            `${option.required_approvers} approvals required`
          }
          rules={preview?.policy?.rule_ids}
        />
        {error && (
          <p role="alert" className="crit-text">
            {error}
          </p>
        )}
        <div className="dialog-actions">
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            variant="default"
            disabled={
              busy ||
              validating ||
              !preview?.valid ||
              preview.policy?.effect === "deny" ||
              readOnly ||
              !connected
            }
            onClick={() => {
              setBusy(true);
              void mutate(`/approvals/${approvalId}/decide`, {
                decision: "edit_approve",
                params,
                option_ids: [option.id],
              })
                .then(() => setOpen(false))
                .catch((e) => setError((e as Error).message))
                .finally(() => setBusy(false));
            }}
          >
            Confirm edited action
          </Button>
        </div>
      </Dialog>
    </>
  );
}
