"""In-process event bus and WebSocket fan-out (MVP spec §15). Every envelope gets a global `seq`;
the last 20,000 are kept so a reconnecting client can `resume` from `since_seq`."""
from __future__ import annotations

import asyncio
from collections import deque
from typing import Any, Callable

import orjson

from .timeutil import wall_now


def to_jsonable(payload: Any) -> Any:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json", by_alias=True)
    return payload


class Client:
    def __init__(self, hub: "Hub"):
        self.hub = hub
        self.topics: set[str] = set()
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=50000)

    def matches(self, topic: str) -> bool:
        if not self.topics:
            return False
        if topic in self.topics or "*" in self.topics:
            return True
        return any(t.endswith("*") and topic.startswith(t[:-1]) for t in self.topics)

    def subscribe(self, topics: list[str]) -> None:
        self.topics.update(topics)

    def unsubscribe(self, topics: list[str]) -> None:
        self.topics.difference_update(topics)

    def send_raw(self, obj: dict) -> None:
        self._put(orjson.dumps(obj).decode())

    def _put(self, text: str) -> None:
        try:
            self.queue.put_nowait(text)
        except asyncio.QueueFull:
            pass

    def replay_since(self, since_seq: int) -> None:
        for env, text in list(self.hub.history):
            if env["seq"] > since_seq and self.matches(env["topic"]):
                self._put(text)


class Hub:
    def __init__(self, history: int = 20000):
        self.seq = 0
        self.history: deque[tuple[dict, str]] = deque(maxlen=history)
        self.clients: set[Client] = set()
        self.listeners: list[Callable[[dict], None]] = []
        self.sim_ts_fn: Callable[[], str | None] = lambda: None

    def connect(self) -> Client:
        c = Client(self)
        self.clients.add(c)
        return c

    def disconnect(self, client: Client) -> None:
        self.clients.discard(client)

    def add_listener(self, fn: Callable[[dict], None]) -> None:
        self.listeners.append(fn)

    def remove_listener(self, fn: Callable[[dict], None]) -> None:
        if fn in self.listeners:
            self.listeners.remove(fn)

    def publish(self, topic: str, type_: str, payload: Any, sim_ts: str | None = None) -> dict:
        self.seq += 1
        env = {"topic": topic, "type": type_, "seq": self.seq, "ts": wall_now(),
               "sim_ts": sim_ts if sim_ts is not None else self.sim_ts_fn(), "payload": to_jsonable(payload)}
        text = orjson.dumps(env).decode()
        self.history.append((env, text))
        for c in list(self.clients):
            if c.matches(topic):
                c._put(text)
        for fn in list(self.listeners):
            try:
                fn(env)
            except Exception:  # listeners must never break the bus
                pass
        return env

    def clear_history(self) -> None:
        self.history.clear()
