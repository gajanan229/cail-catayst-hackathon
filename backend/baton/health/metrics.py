"""In-memory metric ring buffers: one point per series every 5 sim-seconds, 30 sim-minutes kept (MVP spec §5)."""
from __future__ import annotations

import fnmatch
from collections import deque

from ..core.timeutil import iso_sim

POINTS = 360  # 30 min at 5 s


class MetricsStore:
    def __init__(self):
        self.series: dict[str, deque] = {}

    def reset(self) -> None:
        self.series.clear()

    def record(self, at, values: dict[str, float]) -> None:
        ts = iso_sim(at)
        for k, v in values.items():
            buf = self.series.get(k)
            if buf is None:
                buf = self.series[k] = deque(maxlen=POINTS)
            buf.append((ts, round(float(v), 3)))

    def keys(self) -> list[str]:
        return sorted(self.series)

    def query(self, patterns: list[str], window_s: int = 900) -> list[dict]:
        n = max(1, window_s // 5)
        out = []
        for key in self.keys():
            if any(fnmatch.fnmatchcase(key, p) for p in patterns):
                out.append({"key": key, "points": list(self.series[key])[-n:]})
        return out

    def last(self, key: str) -> float | None:
        buf = self.series.get(key)
        return buf[-1][1] if buf else None

    def window(self, key: str, n: int) -> list[float]:
        buf = self.series.get(key)
        return [v for _, v in list(buf)[-n:]] if buf else []
