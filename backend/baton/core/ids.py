"""Prefixed ULIDs (evt_, sit_, inc_, thr_, card_, apr_, exe_, clm_, ...)."""
from __future__ import annotations

import os
import threading
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_lock = threading.Lock()
_last_ms = 0
_last_rand = 0


def _encode(value: int, length: int) -> str:
    out = []
    for _ in range(length):
        out.append(_CROCKFORD[value & 31])
        value >>= 5
    return "".join(reversed(out))


def ulid() -> str:
    """Monotonic ULID: 48-bit ms timestamp + 80-bit randomness, incremented within the same ms."""
    global _last_ms, _last_rand
    with _lock:
        ms = int(time.time() * 1000)
        if ms <= _last_ms:
            ms = _last_ms
            _last_rand += 1
        else:
            _last_ms = ms
            _last_rand = int.from_bytes(os.urandom(10), "big") >> 1
        return _encode(ms, 10) + _encode(_last_rand & ((1 << 80) - 1), 16)


def new_id(prefix: str) -> str:
    return f"{prefix}_{ulid()}"
