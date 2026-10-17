-- Baton runtime database (MVP spec §5.5). Most rows keep the full contract shape in `data` (JSON);
-- the other columns exist for filtering and ordering. sim_ts and wall_ts are stored where they differ.
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY, sim_ts TEXT, wall_ts TEXT, subsystem TEXT, event_number INTEGER,
  component_id TEXT, episode_id TEXT, quarantined INTEGER, data TEXT);
CREATE INDEX IF NOT EXISTS events_sim ON events(sim_ts);

CREATE TABLE IF NOT EXISTS episodes (
  id TEXT PRIMARY KEY, fingerprint TEXT, component_id TEXT, status TEXT, first_at TEXT, last_at TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS signals (
  id TEXT PRIMARY KEY, kind TEXT, component_id TEXT, started_at TEXT, ended_at TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS situations (
  id TEXT PRIMARY KEY, status TEXT, template TEXT, first_at TEXT, incident_id TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS situation_members (
  situation_id TEXT, member_type TEXT, member_id TEXT, PRIMARY KEY (situation_id, member_type, member_id));

CREATE TABLE IF NOT EXISTS incidents (
  id TEXT PRIMARY KEY, display_id TEXT, status TEXT, situation_id TEXT, thread_id TEXT, opened_at TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS incident_timeline (
  id TEXT PRIMARY KEY, incident_id TEXT, sim_ts TEXT, wall_ts TEXT, kind TEXT, data TEXT);
CREATE INDEX IF NOT EXISTS timeline_inc ON incident_timeline(incident_id, sim_ts);

CREATE TABLE IF NOT EXISTS threads (id TEXT PRIMARY KEY, mode TEXT, incident_id TEXT, created_at TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, thread_id TEXT, status TEXT, started_at TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS trace_steps (id TEXT PRIMARY KEY, run_id TEXT, thread_id TEXT, seq INTEGER, data TEXT);
CREATE INDEX IF NOT EXISTS trace_thread ON trace_steps(thread_id, seq);
CREATE TABLE IF NOT EXISTS cards (id TEXT PRIMARY KEY, thread_id TEXT, incident_id TEXT, type TEXT, seq INTEGER, data TEXT);
CREATE INDEX IF NOT EXISTS cards_thread ON cards(thread_id, seq);
CREATE TABLE IF NOT EXISTS plan_steps (id TEXT PRIMARY KEY, thread_id TEXT, catalog_id TEXT, data TEXT);

CREATE TABLE IF NOT EXISTS approvals (id TEXT PRIMARY KEY, thread_id TEXT, incident_id TEXT, status TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS executions (id TEXT PRIMARY KEY, catalog_id TEXT, status TEXT, sim_ts TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS execution_tokens (
  id TEXT PRIMARY KEY, command_hash TEXT, approval_id TEXT, issued_at REAL, expires_at REAL, used_at REAL);
CREATE TABLE IF NOT EXISTS undo_entries (id TEXT PRIMARY KEY, incident_id TEXT, execution_id TEXT, status TEXT, data TEXT);

CREATE TABLE IF NOT EXISTS audit_log (
  seq INTEGER PRIMARY KEY, wall_ts TEXT, sim_ts TEXT, actor_type TEXT, actor_id TEXT, action TEXT, target TEXT,
  payload TEXT, policy_rule_ids TEXT, model_id TEXT, prompt_hash TEXT, incident_id TEXT, prev_hash TEXT, hash TEXT);

CREATE TABLE IF NOT EXISTS ledger_entries (key TEXT PRIMARY KEY, data TEXT);
CREATE TABLE IF NOT EXISTS ledger_events (id TEXT PRIMARY KEY, key TEXT, kind TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS catalog_entries (id TEXT PRIMARY KEY, data TEXT);
CREATE TABLE IF NOT EXISTS catalog_requests (id TEXT PRIMARY KEY, data TEXT);
CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, data TEXT);

CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, data TEXT);
CREATE TABLE IF NOT EXISTS chunks (id TEXT PRIMARY KEY, doc_type TEXT, status TEXT, content_hash TEXT, data TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
  chunk_id UNINDEXED, title, header, body, tokenize = "unicode61 tokenchars '$*^#_-'");
CREATE TABLE IF NOT EXISTS chunk_vectors_blob (chunk_id TEXT PRIMARY KEY, embedding BLOB);
CREATE TABLE IF NOT EXISTS claims (id TEXT PRIMARY KEY, status TEXT, runtime INTEGER DEFAULT 0, data TEXT);
CREATE TABLE IF NOT EXISTS claim_reviews (id TEXT PRIMARY KEY, claim_id TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS playbooks (id TEXT PRIMARY KEY, data TEXT);

CREATE TABLE IF NOT EXISTS model_calls (
  id TEXT PRIMARY KEY, run_id TEXT, node TEXT, model TEXT, prompt_hash TEXT, latency_ms INTEGER, cache_hit TEXT,
  wall_ts TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS eval_runs (id TEXT PRIMARY KEY, started_at TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS eval_results (id TEXT PRIMARY KEY, run_id TEXT, data TEXT);
