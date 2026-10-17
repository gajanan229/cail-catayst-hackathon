"""Wire the services that sit on top of the core runtime (governance, commands, knowledge, agents)."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .agents.gateway import Gateway
from .agents.service import AgentService
from .commands.catalog import Catalog
from .commands.executor import Executor
from .commands.service import CommandService
from .diagnosis.engine import Diagnosis
from .governance.approvals import Approvals
from .governance.ledger import Ledger
from .governance.policy import Policy
from .governance.tokens import Tokens
from .knowledge.claims import Claims
from .knowledge.index import KnowledgeBase

if TYPE_CHECKING:
    from .runtime import Runtime

log = logging.getLogger("baton")


async def install_services(rt: "Runtime") -> None:
    d = rt.data_dir
    rt.catalog = Catalog(d / "catalog")
    rt.policy = Policy(d / "policies" / "policy.yaml")
    rt.tokens = Tokens(rt.store, rt.policy.token_ttl_s)
    rt.ledger = Ledger(rt.store, d / "policies" / "ledger_seed.yaml", rt.hub.publish, rt.users.name,
                       lambda cid: rt.catalog.get(cid).tier if rt.catalog.get(cid) else None)
    if not rt.store.query("SELECT 1 FROM ledger_entries LIMIT 1"):
        rt.ledger.seed()
    rt.approvals = Approvals(rt.store, rt.hub.publish, rt.users, lambda: rt.sim.now, rt.policy.approval_expiry_sim_s)
    rt.executor = Executor(rt)
    rt.commands = CommandService(rt)
    rt.diagnosis = Diagnosis(d / "rules")
    rt.kb = KnowledgeBase(rt.store, d, rt.config.embeddings, rt.config.var_dir, {u["id"]: u["name"] for u in rt.users.list()})
    rt.kb.ensure_loaded(rt.sim.site, rt.catalog)
    rt.claims = Claims(rt.store, d / "content", rt.kb, rt.hub.publish, rt.users)
    if not rt.store.query("SELECT 1 FROM claims LIMIT 1"):
        rt.claims.seed()
    rt.gateway = Gateway(rt.config, rt.store, d / "replay")
    rt.agents = AgentService(rt)
    await rt.agents.open()

    def after_reset() -> None:
        rt.ledger.seed()
        for cid in [c for c, rec in list(rt.kb.records.items()) if rec.get("runtime")]:
            rt.kb.remove(cid)
        rt.claims.seed()
        rt.executor.prompt_n = 12

    rt.after_reset = after_reset
