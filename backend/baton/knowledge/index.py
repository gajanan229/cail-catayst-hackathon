"""Knowledge ingestion and hybrid retrieval (MVP spec §10.2–10.3).

Chunk = one record. Contextual header "{doc_type} · {title} · {subsystem or component}" is prepended in
both indexes. FTS5 BM25 (title 3, header 2, body 1) + vectors (bge-small-en-v1.5, numpy cosine over an
in-memory matrix; BM25 only when BATON_EMBEDDINGS=none) → reciprocal rank fusion (k = 60) → authority.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from ..db.store import Store, dumps, loads

log = logging.getLogger("baton.knowledge")

AUTHORITY = {"claim": 1.2, "playbook": 1.2, "playbook_step": 1.1, "site_fact": 1.2, "operator_message": 1.0,
             "command_ref": 1.0, "catalog": 1.0, "concept": 0.9, "incident": 0.9, "glossary": 0.8}
PROVENANCE = {"operator_message": "hpe_manual", "claim": "expert_verified", "playbook": "expert_verified",
              "playbook_step": "expert_verified", "site_fact": "site", "incident": "incident",
              "command_ref": "synthetic", "concept": "synthetic", "glossary": "synthetic", "catalog": "synthetic"}
RRF_K = 60
# Query-intent preferences: which document types a question is usually after (multipliers on the final score).
INTENT_BOOSTS = [
    (re.compile(r"(?<![a-z])(which|what) (read-only )?(command|check)|what should i (run|type|use)|how (do|can) i (check|see|inspect|pause|"
                r"suspend|resume|stop|add|raise|lower|find|list|report)(?![a-z])|(?<![a-z])command (to|for|that)(?![a-z])|without changing", re.I),
     {"command_ref": 1.8}, 0.95),
    (re.compile(r"(?<![a-z])(last time|earlier|previous|past|before|history|happened when|did the team|outage where|incident where|"
                r"when did)(?![a-z])", re.I), {"incident": 2.0}, 0.95),
    (re.compile(r"(?<![a-z])(why|how (does|do|can)|what (is|are|does)|explain|difference)(?![a-z])", re.I), {"concept": 1.4}, 0.7),
]
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
CLASSES = ["ATM-AUTH", "POS-AUTH", "BAL-INQ", "CARD-MGMT"]
SUBSYSTEMS = ["OMF", "PATHWAY", "TMF", "EMS", "PATHCOM", "TACL", "SCF", "MEASCOM", "TMFCOM"]
STOP = {"the", "a", "an", "is", "are", "of", "to", "in", "on", "for", "and", "or", "what", "how", "does", "do", "it",
        "this", "that", "with", "be", "me", "show", "tell", "about", "between", "difference", "mean", "means", "s",
        "can", "we", "i", "you", "our", "my", "any", "there", "why", "which", "when", "going", "on?", "up"}


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[\w$*#^\-]+", text.lower()) if t]


class Embedder:
    def __init__(self, mode: str, cache_dir: Path):
        self.mode = mode
        self.cache_dir = cache_dir
        self.model = None
        self.ok = False
        if mode == "local":
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer("BAAI/bge-small-en-v1.5")
                self.ok = True
            except Exception as e:  # download or import failure: BM25 only
                log.warning("embeddings unavailable (%s); falling back to BM25 only", e)

    def encode(self, texts: list[str], query: bool = False) -> np.ndarray | None:
        if not self.ok:
            return None
        if query:
            texts = [QUERY_PREFIX + t for t in texts]
            return np.asarray(self.model.encode(texts, normalize_embeddings=True), dtype=np.float32)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        out: list[np.ndarray | None] = []
        todo = []
        for i, t in enumerate(texts):
            p = self.cache_dir / f"{_hash(t)}.npy"
            if p.exists():
                out.append(np.load(p))
            else:
                out.append(None)
                todo.append(i)
        if todo:
            vecs = self.model.encode([texts[i] for i in todo], normalize_embeddings=True, batch_size=32)
            for i, v in zip(todo, vecs):
                v = np.asarray(v, dtype=np.float32)
                np.save(self.cache_dir / f"{_hash(texts[i])}.npy", v)
                out[i] = v
        return np.stack(out) if out else np.zeros((0, 384), dtype=np.float32)


class KnowledgeBase:
    def __init__(self, store: Store, data_dir: Path, embeddings: str, var_dir: Path, users: dict[str, str] | None = None):
        self.store = store
        self.data_dir = data_dir
        self.content = data_dir / "content"
        self.users = users or {}
        self.embedder = Embedder(embeddings, var_dir / "emb_cache")
        self.ids: list[str] = []
        self.matrix: np.ndarray | None = None
        self.glossary: dict[str, list[str]] = {}
        self.records: dict[str, dict] = {}

    # ------------------------------------------------------------ ingestion

    def _jsonl(self, name: str) -> list[dict]:
        p = self.content / name
        if not p.exists():
            return []
        out = []
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    log.warning("bad line in %s", name)
        return out

    def _yaml_dir(self, name: str) -> list[dict]:
        d = self.content / name
        return [yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted(d.glob("*.yaml"))] if d.exists() else []

    def name(self, uid: str | None) -> str | None:
        return self.users.get(uid, uid) if uid else None

    def chunks_from_content(self, site: dict, catalog) -> list[dict]:
        chunks: list[dict] = []
        for m in self._jsonl("operator_messages.jsonl"):
            title = f"{m['subsystem']} {m['number']}: {m['text_template']}"
            body = f"{m['text_template']}. Cause: {m.get('cause', '')} Effect: {m.get('effect', '')} Recovery: {m.get('recovery', '')}"
            chunks.append(self._chunk(m["id"], "operator_message", title, f"{m['subsystem']} {m['number']}", body, m,
                                      synthetic=bool(m.get("synthetic")), source=m.get("source"),
                                      metadata={"subsystem": m["subsystem"], "number": m["number"]}))
        for c in self._jsonl("command_reference.jsonl"):
            title = c.get("title") or c["id"]
            cid = c.get("catalog_id") or c.get("metadata", {}).get("catalog_id")
            e = catalog.get(cid) if cid else None
            text = c["text"]
            if e is not None:   # contextual enrichment from the catalog entry (what it is for, how operators say it)
                title = f"{e.title} ({cid})"
                text = (f"{e.title}: {e.description} Command: {e.interpreter + '; ' if e.interpreter else ''}{e.template or 'Baton check'}. "
                        f"{'Read-only.' if e.tier == 'T0' else 'Changes the system (' + e.tier + ').'} "
                        f"Also asked as: {', '.join(e.aliases)}; " + "; ".join(x.utterance for x in e.examples) + f". {c['text']}")
            chunks.append(self._chunk(c["id"], "command_ref", f"Command reference: {title}",
                                      c.get("interpreter") or c.get("metadata", {}).get("subsystem", ""), text, c,
                                      synthetic=True, source=c.get("source"), metadata=c.get("metadata", {})))
        for c in self._jsonl("concepts.jsonl"):
            chunks.append(self._chunk(c["id"], "concept", c["title"], ", ".join(c.get("metadata", {}).get("components", [])),
                                      c["text"], c, synthetic=True, source=c.get("source"), metadata=c.get("metadata", {})))
        for g in self._jsonl("glossary.jsonl"):
            term = g.get("term") or g["title"]
            syns = g.get("synonyms") or []
            self._add_glossary(term, syns)
            chunks.append(self._chunk(g["id"], "glossary", term, "glossary", f"{term}: {g.get('definition', g.get('text', ''))} "
                                      f"Synonyms: {', '.join(syns)}", g, synthetic=True, source=g.get("source")))
        for i in self._jsonl("incidents.jsonl"):
            chunks.append(self._chunk(i["id"], "incident", i.get("display_id", i["title"]), "TORBANK",
                                      i.get("summary") or i["text"], i, synthetic=True, source=i.get("source")))
        for pb in self._yaml_dir("playbooks"):
            steps = "; ".join(s.get("read") or s.get("text") or f"{s.get('kind')} {s.get('catalog_id', '')}" for s in pb["steps"])
            pid = f"playbook:{pb['id']}"
            chunks.append(self._chunk(pid, "playbook", f"{pb['id']}: {pb['title']}", pb.get("trigger", {}).get("causal_template", ""),
                                      f"{pb['title']} (v{pb['version']}, by {self.name(pb['author'])}). Steps: {steps}", pb,
                                      synthetic=True, source=pb.get("source"),
                                      status="active" if pb.get("status", "verified") == "verified" else pb["status"]))
        for cl in self._yaml_dir("claims"):
            chunks.append(self.claim_chunk(cl))
        chunks += self.site_facts(site)
        for e in catalog.all():
            text = f"{e.title}. {e.description} Aliases: {', '.join(e.aliases)}. Examples: " + "; ".join(x.utterance for x in e.examples)
            chunks.append(self._chunk(f"catalog:{e.id}", "catalog", e.title, e.utility, text, {"catalog_id": e.id},
                                      synthetic=True, source=None, metadata={"catalog_id": e.id}))
        return chunks

    def claim_chunk(self, cl: dict) -> dict:
        status = {"verified": "active", "pending_review": "draft", "rejected": "rejected", "retired": "retired"}.get(cl["status"], "draft")
        s = cl.get("structured", {})
        body = f"{cl['statement']} Condition: {s.get('condition', '')}. Rationale: {s.get('rationale', '')}"
        return self._chunk(f"claim:{cl['id']}", "claim", f"{cl['id']}: {cl['statement'][:80]}", ", ".join(s.get("subject", [])),
                           body, cl, synthetic=bool(cl.get("synthetic", True)), source=cl.get("source"), status=status)

    def site_facts(self, site: dict) -> list[dict]:
        out = []
        for p in site["processes"]:
            backup = f"backup on CPU {p['backup_cpu']}" if p.get("backup_cpu") is not None else "no backup"
            extra = []
            if p.get("window"):
                extra.append(f"runs {p['window'][0]}–{p['window'][1]}")
            if p.get("protected"):
                extra.append("protected system process")
            if "batch" in (p.get("tags") or []):
                extra.append("batch")
            desc = p.get("description") or p["role"]
            text = f"{p['name']} ({desc}) runs on CPU {p['primary_cpu']}, {backup}" + (f"; {', '.join(extra)}" if extra else "") + "."
            out.append(self._chunk(f"site:proc:{p['name']}", "site_fact", f"{p['name']} on \\TORBANK", f"process {p['name']}", text, p,
                                   synthetic=True, metadata={"entity": p["name"]}))
        for sc in site["server_classes"]:
            text = (f"Server class {sc['name']} ({sc['service']}) under PATHMON $PM1: CPUs {', '.join(map(str, sc['cpus']))}; "
                    f"NUMSTATIC {sc['numstatic']}, MAXSERVERS {sc['maxservers']}, service time {sc['service_ms']} ms; {sc.get('tag', 'normal')}.")
            out.append(self._chunk(f"site:sc:{sc['name']}", "site_fact", f"{sc['name']} configuration", f"server class {sc['name']}",
                                   text, sc, synthetic=True, metadata={"entity": sc["name"]}))
        return out

    def _chunk(self, id_: str, doc_type: str, title: str, comp: str, text: str, record: dict, *, synthetic: bool,
               source: str | None = None, status: str = "active", metadata: dict | None = None) -> dict:
        header = f"{doc_type} · {title} · {comp}".strip(" ·")
        return {"id": id_, "doc_type": doc_type, "title": title, "header": header, "text": text, "record": record,
                "synthetic": synthetic, "source": source, "status": status, "metadata": metadata or {},
                "provenance": PROVENANCE.get(doc_type, "synthetic"), "authority": AUTHORITY.get(doc_type, 1.0),
                "runtime": False}

    def build(self, site: dict, catalog) -> int:
        chunks = self.chunks_from_content(site, catalog)
        with self.store.lock:
            self.store.execute("DELETE FROM chunks")
            self.store.execute("DELETE FROM chunks_fts")
            self.store.execute("DELETE FROM chunk_vectors_blob")
        for c in chunks:
            self._insert(c)
        self._load_vectors()
        return len(chunks)

    def _insert(self, c: dict, embed: bool = False) -> None:
        self.store.put("chunks", c["id"], c, doc_type=c["doc_type"], status=c["status"], content_hash=_hash(c["header"] + c["text"]))
        self.store.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (c["id"],))
        self.store.execute("INSERT INTO chunks_fts (chunk_id, title, header, body) VALUES (?,?,?,?)",
                           (c["id"], c["title"], _fts_text(c["header"]), _fts_text(c["text"])))
        self.records[c["id"]] = c
        if embed and self.embedder.ok:
            v = self.embedder.encode([c["header"] + "\n" + c["text"]])
            if v is not None:
                self.store.execute("INSERT OR REPLACE INTO chunk_vectors_blob (chunk_id, embedding) VALUES (?,?)",
                                   (c["id"], v[0].tobytes()))
                self._append_vector(c["id"], v[0])

    def _add_glossary(self, term: str, synonyms: list[str]) -> None:
        t = term.lower()
        syns = [x.lower() for x in synonyms if x and x.lower() != t]
        cur = self.glossary.setdefault(t, [])
        cur.extend(x for x in syns if x not in cur)
        for x in syns:
            back = self.glossary.setdefault(x, [])
            if t not in back:
                back.append(t)

    def _load_vectors(self) -> None:
        rows = self.store.query("SELECT id, data FROM chunks")
        self.records = {r["id"]: loads(r["data"]) for r in rows}
        for c in self.records.values():
            if c["doc_type"] == "glossary":
                self._add_glossary(c["record"].get("term") or c["title"], c["record"].get("synonyms") or [])
        if not self.embedder.ok:
            self.ids, self.matrix = [], None
            return
        have = {r["chunk_id"]: np.frombuffer(r["embedding"], dtype=np.float32)
                for r in self.store.query("SELECT chunk_id, embedding FROM chunk_vectors_blob")}
        missing = [cid for cid in self.records if cid not in have]
        if missing:
            vecs = self.embedder.encode([self.records[c]["header"] + "\n" + self.records[c]["text"] for c in missing])
            for cid, v in zip(missing, vecs):
                have[cid] = v
                self.store.execute("INSERT OR REPLACE INTO chunk_vectors_blob (chunk_id, embedding) VALUES (?,?)", (cid, v.tobytes()))
        self.ids = list(have)
        self.matrix = np.stack([have[i] for i in self.ids]) if self.ids else None

    def _append_vector(self, cid: str, v: np.ndarray) -> None:
        if cid in self.ids:
            self.matrix[self.ids.index(cid)] = v
            return
        self.ids.append(cid)
        self.matrix = v[None, :] if self.matrix is None else np.vstack([self.matrix, v[None, :]])

    def ensure_loaded(self, site: dict, catalog) -> None:
        n = self.store.query("SELECT COUNT(*) AS n FROM chunks")[0]["n"]
        if n == 0:
            self.build(site, catalog)
        else:
            self._load_vectors()

    # ------------------------------------------------------------ hot updates

    def upsert_claim(self, claim: dict, runtime: bool = True) -> None:
        c = self.claim_chunk(claim)
        c["runtime"] = runtime
        self._insert(c, embed=c["status"] == "active")

    def remove(self, chunk_id: str) -> None:
        self.store.execute("DELETE FROM chunks WHERE id = ?", (chunk_id,))
        self.store.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (chunk_id,))
        self.store.execute("DELETE FROM chunk_vectors_blob WHERE chunk_id = ?", (chunk_id,))
        self.records.pop(chunk_id, None)
        if chunk_id in self.ids:
            i = self.ids.index(chunk_id)
            self.ids.pop(i)
            self.matrix = np.delete(self.matrix, i, axis=0) if self.matrix is not None and len(self.ids) else None

    # ------------------------------------------------------------ query

    def entities(self, q: str) -> tuple[list[str], list[str]]:
        """Return (entity strings, pinned chunk IDs) for exact lookups."""
        ents, pins = [], []
        for num in re.findall(r"\*?(\d{3,4})\*?", q):
            ents.append(num)
            for cid, c in self.records.items():
                if c["doc_type"] == "operator_message" and str(c["metadata"].get("number")) == num:
                    pins.append(cid)
        for name in re.findall(r"\$[A-Za-z][A-Za-z0-9]{0,6}", q):
            ents.append(name.upper())
            if f"site:proc:{name.upper()}" in self.records:
                pins.append(f"site:proc:{name.upper()}")
        up = q.upper()
        for cls in CLASSES:
            if cls in up or cls.replace("-", " ") in up:
                ents.append(cls)
        for sub in SUBSYSTEMS:
            if re.search(rf"\b{sub}\b", up):
                ents.append(sub)
        for m in re.findall(r"\bC-0\d\d\b", up):
            if f"claim:{m}" in self.records:
                pins.append(f"claim:{m}")
        return ents, list(dict.fromkeys(pins))

    def expand(self, q: str) -> list[str]:
        toks = [t.strip("*") for t in tokens(q)]
        toks = [t for t in toks if t and t not in STOP]
        extra = []
        low = q.lower()
        for term, syns in self.glossary.items():
            if term and (re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", low)):
                extra += syns
        for t in toks:
            extra += self.glossary.get(t, [])
        out = list(dict.fromkeys(toks + [w for e in extra for w in tokens(e) if w not in STOP]))
        return out[:24]

    def bm25(self, terms: list[str], types: list[str] | None, limit: int = 30) -> list[str]:
        if not terms:
            return []
        parts = []
        for t in terms:
            t = t.replace('"', "")
            parts.append(f'"{t}"')
            if t.isdigit():
                parts.append(f'"*{t}*"')
        match = " OR ".join(parts)
        try:
            rows = self.store.query("SELECT chunk_id, bm25(chunks_fts, 0.0, 3.0, 2.0, 1.0) AS s FROM chunks_fts "
                                    "WHERE chunks_fts MATCH ? ORDER BY s LIMIT ?", (match, limit * 4))
        except Exception as e:
            log.warning("fts query failed: %s", e)
            return []
        out = []
        for r in rows:
            c = self.records.get(r["chunk_id"])
            if c and self._allowed(c, types):
                out.append(r["chunk_id"])
            if len(out) >= limit:
                break
        return out

    def vector(self, q: str, types: list[str] | None, limit: int = 30) -> list[str]:
        if self.matrix is None or not self.embedder.ok:
            return []
        qv = self.embedder.encode([q], query=True)
        if qv is None:
            return []
        sims = self.matrix @ qv[0]
        order = np.argsort(-sims)
        out = []
        for i in order:
            c = self.records.get(self.ids[i])
            if c and self._allowed(c, types):
                out.append(self.ids[i])
            if len(out) >= limit:
                break
        return out

    @staticmethod
    def _allowed(c: dict, types: list[str] | None) -> bool:
        if c["status"] in ("rejected", "retired", "draft"):
            return False
        if types:
            return c["doc_type"] in types
        return c["doc_type"] != "catalog"

    def search(self, q: str, k: int = 8, types: list[str] | None = None, debug: bool = False,
               boost_ids: list[str] | None = None) -> dict:
        ents, pins = self.entities(q)
        terms = self.expand(q)
        b = self.bm25(terms, types)
        v = self.vector(q, types)
        scores: dict[str, float] = {}
        for rank, cid in enumerate(b):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
        for rank, cid in enumerate(v):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
        boosts: dict[str, float] = {}
        strength: dict[str, float] = {}
        for rx, prefs, pull in INTENT_BOOSTS:
            if rx.search(q):
                for dt, x in prefs.items():
                    boosts[dt] = max(boosts.get(dt, 1.0), x)
                    strength[dt] = max(strength.get(dt, 0.0), pull)
        fused = sorted(scores, key=lambda c: -scores[c])[:12]
        top = max(scores.values(), default=1.0 / (RRF_K + 1))
        for dt in boosts:   # type routing: the document type the question asks for competes with the top hits
            if types and dt not in types:
                continue
            typed = list(dict.fromkeys(self.bm25(terms, [dt], 2) + self.vector(q, [dt], 2)))[:2]
            for rank, cid in enumerate(typed):
                scores[cid] = max(scores.get(cid, 0.0), top * strength[dt] * (1.0 - 0.1 * rank))
                if cid not in fused:
                    fused.append(cid)
        own = [t.strip("*") for t in tokens(q)]
        content_terms = list(dict.fromkeys(t for t in own if len(t) > 3 and t not in STOP))
        for cid, c in self.records.items():
            title = c["title"].lower()
            if not self._allowed(c, types) or c["doc_type"] not in ("concept", "operator_message", "playbook"):
                continue
            if len(content_terms) >= 2 and sum(1 for t in content_terms if t in title) >= 2:
                pins.append(cid)
        for cid in list(pins):
            c = self.records.get(cid)
            if c and c["doc_type"] == "concept":
                for num in re.findall(r"(?<![0-9])([0-9]{4})(?![0-9])", c["text"]):
                    for oid in (f"opmsg:PATHWAY:{num}", f"opmsg:OMF:{num}"):
                        if oid in self.records and oid not in pins:
                            pins.append(oid)
        pins = [p for p in dict.fromkeys(pins) if p in self.records and self._allowed(self.records[p], types)]
        ranked = []
        for cid in dict.fromkeys(pins + fused + list(boost_ids or [])):
            c = self.records.get(cid)
            if not c:
                continue
            base = scores.get(cid, 1.0 / (RRF_K + 1))
            final = base * c["authority"] * (1.5 if cid in pins else 1.0) * (1.3 if boost_ids and cid in boost_ids else 1.0)
            ranked.append((cid, base, final))
        if boosts:
            ranked = [(cid, base, final * boosts.get(self.records[cid]["doc_type"], 1.0)) for cid, base, final in ranked]
        ranked.sort(key=lambda x: -x[2])
        results = []
        for cid, base, final in ranked[:k]:
            c = self.records[cid]
            item = {"id": cid, "doc_type": c["doc_type"], "title": c["title"], "snippet": _snippet(c["text"]),
                    "provenance": c["provenance"], "source_url": c.get("source"), "synthetic": bool(c.get("synthetic"))}
            if debug:
                item["scores"] = {"bm25_rank": b.index(cid) + 1 if cid in b else None,
                                  "vector_rank": v.index(cid) + 1 if cid in v else None,
                                  "fused": round(base, 5), "authority": c["authority"], "final": round(final, 5),
                                  "pinned": cid in pins}
            results.append(item)
        return {"query": q, "expanded_terms": terms, "entities": ents, "results": results}

    def item(self, cid: str) -> dict:
        c = self.records.get(cid)
        if not c:
            from ..api.errors import ApiError
            raise ApiError("NOT_FOUND", f"Knowledge item {cid} not found")
        cites = []
        if c.get("source"):
            cites.append({"id": cid, "label": c["title"], "kind": _kind(c["doc_type"]), "url": c.get("source")})
        return {"id": cid, "doc_type": c["doc_type"], "title": c["title"], "text": c["text"], "header": c["header"],
                "metadata": c.get("metadata", {}), "provenance": c["provenance"], "source_url": c.get("source"),
                "synthetic": bool(c.get("synthetic")), "record": c.get("record", {}), "citations": cites}

    def playbooks(self) -> list[dict]:
        out = []
        for c in self.records.values():
            if c["doc_type"] == "playbook":
                pb = c["record"]
                out.append({"id": pb["id"], "title": pb["title"], "version": int(pb.get("version", 1)), "author": pb["author"],
                            "author_name": self.name(pb["author"]), "verified_by": pb.get("verified_by", []),
                            "synthetic": bool(pb.get("synthetic", True)), "trigger": pb.get("trigger", {}), "steps": pb["steps"]})
        return sorted(out, key=lambda p: p["id"])

    def playbook(self, pid: str) -> dict:
        from ..api.errors import ApiError
        for p in self.playbooks():
            if p["id"] == pid:
                return p
        raise ApiError("NOT_FOUND", f"Playbook {pid} not found")

    def citation(self, cid: str) -> dict | None:
        c = self.records.get(cid)
        if not c:
            return None
        label = c["title"]
        if c["doc_type"] == "operator_message":
            label = f"{c['metadata'].get('subsystem')} {c['metadata'].get('number')}"
        elif c["doc_type"] == "claim":
            label = f"{c['record']['id']} · {self.name(c['record'].get('author'))}"
        elif c["doc_type"] == "command_ref":
            label = "Command reference"
        elif c["doc_type"] == "playbook":
            label = f"{c['record']['id']} v{c['record'].get('version', 1)}"
        elif c["doc_type"] == "concept":
            label = f"Concept: {c['title']}"
        return {"id": cid, "label": label[:60], "kind": _kind(c["doc_type"]), "url": c.get("source")}


def _kind(doc_type: str) -> str:
    return {"operator_message": "hpe_manual", "command_ref": "command_ref", "concept": "concept", "claim": "claim",
            "playbook": "playbook", "playbook_step": "playbook", "incident": "incident", "site_fact": "site",
            "glossary": "glossary", "catalog": "command_ref"}.get(doc_type, "concept")


def _fts_text(text: str) -> str:
    # keep "*1034*" whole and also index the bare number
    return re.sub(r"\*(\d{3,4})\*", r"*\1* \1", text)


def _snippet(text: str, n: int = 220) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"
