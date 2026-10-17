"""Execution tokens (MVP spec §8.2, §9): HMAC of the rendered command + approval ID, single use,
expiring after 120 s. Only commands carrying a valid token reach the (simulated) system."""
from __future__ import annotations

import hashlib
import hmac
import os
import time

from ..core.ids import new_id
from ..db.store import Store


def command_hash(rendered: str) -> str:
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


class TokenError(Exception):
    pass


class Tokens:
    def __init__(self, store: Store, ttl_s: int = 120, secret: bytes | None = None):
        self.store = store
        self.ttl_s = ttl_s
        self.secret = secret or os.urandom(32)

    def _mac(self, chash: str, approval_id: str, token_id: str) -> str:
        return hmac.new(self.secret, f"{token_id}|{chash}|{approval_id}".encode(), hashlib.sha256).hexdigest()

    def issue(self, rendered: str, approval_id: str) -> str:
        tid = new_id("tok")
        chash = command_hash(rendered)
        now = time.time()
        self.store.execute("INSERT INTO execution_tokens (id, command_hash, approval_id, issued_at, expires_at, used_at) "
                           "VALUES (?,?,?,?,?,NULL)", (tid, chash, approval_id, now, now + self.ttl_s))
        return f"{tid}.{self._mac(chash, approval_id, tid)}"

    def consume(self, token: str, rendered: str) -> str:
        """Check and burn a token for exactly this rendered text. Returns the approval ID it was issued for."""
        try:
            tid, mac = token.split(".", 1)
        except (AttributeError, ValueError):
            raise TokenError("malformed token")
        rows = self.store.query("SELECT * FROM execution_tokens WHERE id = ?", (tid,))
        if not rows:
            raise TokenError("unknown token")
        row = rows[0]
        chash = command_hash(rendered)
        if row["command_hash"] != chash:
            raise TokenError("token does not match the command")
        if not hmac.compare_digest(mac, self._mac(chash, row["approval_id"], tid)):
            raise TokenError("bad token signature")
        if row["used_at"] is not None:
            raise TokenError("token already used")
        if time.time() > row["expires_at"]:
            raise TokenError("token expired")
        self.store.execute("UPDATE execution_tokens SET used_at = ? WHERE id = ?", (time.time(), tid))
        return row["approval_id"]
