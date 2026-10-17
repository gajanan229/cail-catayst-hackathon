import { useState } from "react";
import {
  BookOpen,
  Check,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { Claim, Schema } from "@/api/types";
import { api, mutate } from "@/api/client";
import { useConsole } from "@/realtime/store";
import {
  Badge,
  Empty,
  Panel,
  ErrorState,
  Loading,
  ActorStamp,
} from "@/components/common";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { PageHeading } from "./Incident";
import type { Inspect } from "@/components/cards/CardRenderer";

export function Knowledge({ inspect }: { inspect: Inspect }) {
  const [tab, setTab] = useState("review");
  const claims = useConsole((s) => s.claims);
  const users = useConsole((s) => s.users);
  const actor = useConsole((s) => s.actor);
  const connected = useConsole((s) => s.connected);
  const [q, setQ] = useState("1034 link errors ATM");
  const [query, setQuery] = useState("1034 link errors ATM");
  const [debug, setDebug] = useState(false);
  const [selected, setSelected] = useState<Claim | null>(null);
  const [action, setAction] = useState("confirm");
  const [statement, setStatement] = useState("");
  const [condition, setCondition] = useState("");
  const [siteScope, setSiteScope] = useState("");
  const [calendarScope, setCalendarScope] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const search = useQuery({
    queryKey: ["kb", query],
    queryFn: () =>
      api<Schema<"KbSearchResponse">>(
        `/kb/search?q=${encodeURIComponent(query)}&k=8&debug=true`,
      ),
    enabled: tab === "search",
  });
  const pending = claims.filter((c) => c.status === "pending_review");
  const verified = claims.filter((c) => c.status === "verified");
  const review = (c: Claim, kind: string) => {
    setSelected(c);
    setAction(kind);
    setStatement(c.statement);
    setCondition(c.structured.condition);
    setSiteScope(String(c.scope.site || ""));
    setCalendarScope(
      Array.isArray(c.scope.calendar)
        ? c.scope.calendar.join(", ")
        : String(c.scope.calendar || ""),
    );
    setReason("");
    setError("");
  };
  const save = async () => {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      const scope: Record<string, unknown> = {
        ...selected.scope,
        site: siteScope.trim(),
      };
      if (calendarScope.trim())
        scope.calendar = calendarScope
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
      else delete scope.calendar;
      await mutate(`/claims/${selected.id}/review`, {
        decision: action,
        ...(action === "edit_confirm"
          ? {
              edits: {
                statement,
                structured: { ...selected.structured, condition },
                scope,
              },
            }
          : {}),
        ...(action === "reject" ? { reason } : {}),
      });
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
        eyebrow="EXPERTISE / KNOWLEDGE"
        title="Knowledge Studio"
        description="Review incident lessons and search verified guidance."
        action={
          <Badge tone="baton">
            <BookOpen size={13} /> Expert knowledge, with provenance
          </Badge>
        }
      />
      <div className="tabs">
        <button
          className={tab === "review" ? "active" : ""}
          onClick={() => setTab("review")}
        >
          Review queue <Badge>{pending.length}</Badge>
        </button>
        <button
          className={tab === "search" ? "active" : ""}
          onClick={() => setTab("search")}
        >
          Search knowledge
        </button>
        <button
          className={tab === "verified" ? "active" : ""}
          onClick={() => setTab("verified")}
        >
          Verified knowledge <Badge>{verified.length}</Badge>
        </button>
      </div>
      {tab === "search" ? (
        <>
          <form
            className="knowledge-search"
            onSubmit={(e) => {
              e.preventDefault();
              setQuery(q);
            }}
          >
            <Search size={18} />
            <input
              aria-label="Search knowledge"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search a message, command or symptom…"
            />
            <Button type="submit" variant="default">
              Search
            </Button>
            <Button aria-pressed={debug} onClick={() => setDebug(!debug)}>
              <SlidersHorizontal size={14} /> Ranking details
            </Button>
          </form>
          <p className="meta search-caption">
            Exact message matches → lexical + semantic search → ranked evidence
          </p>
          {search.isPending ? (
            <Loading />
          ) : search.error ? (
            <ErrorState
              message={search.error.message}
              retry={() => void search.refetch()}
            />
          ) : search.data?.results.length ? (
            <div className="search-results">
              {search.data.results.map((r, i) => (
                <article className="search-result" key={r.id}>
                  <div className="search-rank">
                    {String(i + 1).padStart(2, "0")}
                  </div>
                  <div>
                    <div className="inline-gap">
                      <Badge
                        tone={
                          r.provenance === "expert_verified" ? "baton" : "info"
                        }
                      >
                        {r.provenance === "hpe_manual"
                          ? "HPE manual"
                          : r.provenance === "expert_verified"
                            ? "Expert verified"
                            : r.doc_type}
                      </Badge>
                      {r.synthetic && <Badge>synthetic</Badge>}
                    </div>
                    <button onClick={() => inspect(r.id)}>
                      <h2>{r.title}</h2>
                    </button>
                    <p>{r.snippet}</p>
                    <div className="meta">
                      {r.id}{" "}
                      {r.source_url && (
                        <a href={r.source_url} target="_blank" rel="noreferrer">
                          Open HPE chapter ↗
                        </a>
                      )}
                    </div>
                    {debug && (
                      <table className="debug-table">
                        <thead>
                          <tr>
                            <th>BM25 rank</th>
                            <th>Vector rank</th>
                            <th>Fused score</th>
                            <th>Authority</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr>
                            <td>{r.scores?.bm25_rank ?? "—"}</td>
                            <td>{r.scores?.vector_rank ?? "—"}</td>
                            <td>{r.scores?.fused?.toFixed(4) ?? "—"}</td>
                            <td>{r.scores?.authority ?? "—"}</td>
                          </tr>
                        </tbody>
                      </table>
                    )}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <Empty title="No matching knowledge">
              Try a message number, a server-class name, or a shorter question.
            </Empty>
          )}
        </>
      ) : (
        <div className="review-layout">
          <div>
            {(tab === "review" ? pending : verified).length ? (
              (tab === "review" ? pending : verified).map((c) => (
                <article className="claim-card" key={c.id}>
                  <div className="row-between">
                    <div className="inline-gap">
                      <Badge tone={c.status === "verified" ? "ok" : "warn"}>
                        {c.status === "verified" ? (
                          <ShieldCheck size={11} />
                        ) : (
                          <BookOpen size={11} />
                        )}{" "}
                        {c.status === "verified"
                          ? "Verified"
                          : "Needs expert review"}
                      </Badge>
                      <Badge>synthetic</Badge>
                    </div>
                    <code className="meta">{c.id}</code>
                  </div>
                  <h2>{c.statement}</h2>
                  <div className="claim-scope">
                    <span>Applies when</span>
                    <p>{c.structured.condition}</p>
                    <span>Scope</span>
                    <p>
                      {Object.entries(c.scope)
                        .map(
                          ([k, v]) =>
                            `${k}: ${Array.isArray(v) ? v.join(", ") : v}`,
                        )
                        .join(" · ")}
                    </p>
                    <span>Rationale</span>
                    <p>{c.structured.rationale}</p>
                  </div>
                  <div className="claim-provenance">
                    <span className="avatar tiny">
                      {users.find((u) => u.id === c.author)?.initials || "OP"}
                    </span>
                    {users.find((u) => u.id === c.author)?.name || c.author}
                    <span>·</span>
                    <button
                      onClick={() => inspect(c.provenance.source_id || c.id)}
                    >
                      {c.provenance.source_type}:{" "}
                      {c.provenance.source_id || "Interview"}
                    </button>
                  </div>
                  {c.status === "pending_review" ? (
                    <div className="card-actions">
                      <Button
                        variant="default"
                        onClick={() => review(c, "confirm")}
                      >
                        <Check size={13} /> Confirm
                      </Button>
                      <Button onClick={() => review(c, "edit_confirm")}>
                        Edit & confirm
                      </Button>
                      <Button
                        variant="ghost"
                        onClick={() => review(c, "reject")}
                      >
                        <X size={13} /> Reject
                      </Button>
                    </div>
                  ) : (
                    <p className="ok-text meta">
                      Verified by{" "}
                      {c.reviews
                        .map(
                          (r) =>
                            users.find((u) => u.id === r.user)?.name || r.user,
                        )
                        .join(", ")}{" "}
                      · Searchable immediately
                    </p>
                  )}
                </article>
              ))
            ) : (
              <Panel
                title={tab === "review" ? "Review queue" : "Verified knowledge"}
              >
                <Empty
                  title={
                    tab === "review"
                      ? "The review queue is clear"
                      : "No claims verified in this session"
                  }
                >
                  {tab === "review"
                    ? "When an incident resolves, Baton drafts scoped claims for an expert to review."
                    : "Confirm a pending claim to make it available in search."}
                </Empty>
              </Panel>
            )}
          </div>
          <aside className="knowledge-aside">
            <div className="review-summary">
              <div>
                <strong>{pending.length}</strong>
                <small>Awaiting review</small>
              </div>
              <div>
                <strong>{verified.length}</strong>
                <small>Verified claims</small>
              </div>
            </div>
            <h2>Review the scope and the source.</h2>
            <p>
              Check when a claim applies, follow its source, and correct the
              scope before confirming. Your review becomes part of the audit
              trail.
            </p>
            <div className="knowledge-principle">
              <ShieldCheck size={16} />
              <div>
                <strong>Verified before retrieval</strong>
                <p>
                  Drafts stay out of retrieval until reviewed. Every claim
                  carries its source and reviewer.
                </p>
              </div>
            </div>
            <Badge tone="baton">
              Acting as {users.find((u) => u.id === actor)?.name}
            </Badge>
          </aside>
        </div>
      )}
      <Dialog
        open={!!selected}
        onOpenChange={(o) => !o && setSelected(null)}
        title={
          action === "confirm"
            ? "Confirm expert claim"
            : action === "edit_confirm"
              ? "Edit & confirm claim"
              : "Reject claim"
        }
        description="This review becomes part of the audit trail."
      >
        <ActorStamp />
        {action === "edit_confirm" ? (
          <>
            <label>
              Statement
              <textarea
                rows={4}
                value={statement}
                onChange={(e) => setStatement(e.target.value)}
              />
            </label>
            <label>
              Scope / condition
              <textarea
                aria-label="Scope / condition"
                rows={3}
                value={condition}
                onChange={(e) => setCondition(e.target.value)}
              />
            </label>
            <div className="two-fields">
              <label>
                Site scope
                <input
                  value={siteScope}
                  onChange={(e) => setSiteScope(e.target.value)}
                />
              </label>
              <label>
                Calendar scope
                <input
                  value={calendarScope}
                  onChange={(e) => setCalendarScope(e.target.value)}
                  placeholder="Any calendar"
                />
              </label>
            </div>
          </>
        ) : (
          <p>{selected?.statement}</p>
        )}
        {action === "reject" && (
          <label>
            Reason
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </label>
        )}
        {error && (
          <p className="crit-text" role="alert">
            {error}
          </p>
        )}
        <div className="dialog-actions">
          <Button onClick={() => setSelected(null)}>Cancel</Button>
          <Button
            variant={action === "reject" ? "destructive" : "default"}
            disabled={
              busy ||
              !connected ||
              (action === "reject" && !reason.trim()) ||
              (action === "edit_confirm" &&
                (!statement.trim() || !condition.trim()))
            }
            onClick={() => void save()}
          >
            {busy
              ? "Saving…"
              : action === "reject"
                ? "Reject with reason"
                : "Confirm & index claim"}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
