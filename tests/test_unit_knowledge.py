"""RRF arithmetic on controlled ranks, exact pins and BM25-only indexing.

These are implementation unit checks; they never read the held-out retrieval eval.
"""
from pathlib import Path

import pytest

from baton.commands.catalog import Catalog
from baton.db.store import Store
from baton.knowledge.index import KnowledgeBase
from baton.sim.engine import Simulator

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def kb(tmp_path):
    store = Store(tmp_path / "knowledge.db")
    knowledge = KnowledgeBase(store, ROOT / "data", embeddings="none", var_dir=tmp_path)
    yield knowledge
    store.close()


def test_rrf_adds_both_rank_contributions_and_authority(kb, monkeypatch):
    for cid, kind in [("synthetic:a", "operator_message"), ("synthetic:b", "operator_message"), ("synthetic:c", "claim")]:
        kb._insert(kb._chunk(cid, kind, "Synthetic document", "", "synthetic unit fixture", {"synthetic": True}, synthetic=True))
    monkeypatch.setattr(kb, "bm25", lambda *args: ["synthetic:a", "synthetic:b", "synthetic:c"])
    # Inject controlled stage ranks to check fusion, without loading any embedding model.
    monkeypatch.setattr(kb, "vector", lambda *args: ["synthetic:b", "synthetic:c"])
    results = kb.search("fixture", debug=True)["results"]
    assert [r["id"] for r in results] == ["synthetic:c", "synthetic:b", "synthetic:a"]
    by_id = {r["id"]: r["scores"] for r in results}
    assert by_id["synthetic:b"]["fused"] == pytest.approx(1 / 62 + 1 / 61, abs=0.000005)
    assert by_id["synthetic:c"]["final"] == pytest.approx((1 / 63 + 1 / 62) * 1.2, abs=0.000005)
    assert by_id["synthetic:b"]["bm25_rank"] == 2
    assert by_id["synthetic:b"]["vector_rank"] == 1


@pytest.fixture
def indexed(kb):
    sim = Simulator(ROOT / "data", chatter_scale=0)
    kb.build(sim.site, Catalog(ROOT / "data/catalog"))
    return kb


@pytest.mark.parametrize("query,cid", [("1034", "opmsg:PATHWAY:1034"), ("*1034*", "opmsg:PATHWAY:1034"),
                                        ("$STMT1", "site:proc:$STMT1"), ("$stmt1", "site:proc:$STMT1")])
def test_exact_entity_pins(indexed, query, cid):
    result = indexed.search(query, debug=True)["results"]
    assert result[0]["id"] == cid
    assert result[0]["scores"]["pinned"] is True
    assert indexed.embedder.ok is False and indexed.matrix is None
    assert all(r["scores"]["vector_rank"] is None for r in result)


def test_pending_claims_excluded_and_type_filter_applies_to_pins(indexed):
    assert indexed.search("C-017", types=["claim"])["results"] == []
    result = indexed.search("1034", types=["operator_message"])["results"]
    assert result and all(r["doc_type"] == "operator_message" for r in result)
    assert all(c["status"] == "draft" for cid, c in indexed.records.items() if cid in {"claim:C-017", "claim:C-018", "claim:C-019", "claim:C-020"})
