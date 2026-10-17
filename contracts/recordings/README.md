# Recordings

`golden_s1.json` is a real backend run of Flows B, C and A (S1, test profile, models off), recorded by
`scripts/record_ws.py` (`make record-ws`). It replaces hand-written mock timelines.

```
{ "version": "1.0.0", "scenario": "S1", "profile": "test", "time_scale": 4, "recorded_at": "...", "ok": true,
  "events":   [ { "t_ms": 7219, "sim_ts": "2026-11-27T11:52:11Z", "envelope": { <exact /api/ws envelope> } } ],
  "requests": [ { "t_ms": 7310, "method": "POST", "path": "/api/approvals/apr_.../decide", "status": 200, "body": {...} } ],
  "rest":     { "GET /api/incidents": {...}, "GET /api/threads/thr_...": {...}, ... } }
```

- `t_ms` is wall time since the start of the recording. The run used the test profile (16x) with time scale 4,
  so sim time advances about 64 sim-seconds per wall second; replay by `sim_ts` for demo pacing.
- `requests` lists the mutating calls the scripted operator made (approvals as Priya and Sam, claim reviews omitted).
- `rest` holds final REST snapshots for screens that load state on open.
- Ghost typing ran at 25 ms per character; `terminal.output` arrives after the typing time.
