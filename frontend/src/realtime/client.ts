import { hydrate, MOCK, refreshThread } from "@/api/client";
import { useConsole } from "./store";
import type { Event } from "@/api/types";

const topics = [
  "telemetry",
  "events",
  "situations",
  "health",
  "incidents",
  "approvals",
  "ledger",
  "claims",
  "audit",
  "sim",
  "terminal",
];
export function connectRealtime() {
  let stopped = false,
    socket: WebSocket | undefined,
    retry: ReturnType<typeof setTimeout> | undefined;
  let attempt = 0,
    cleanupMock: (() => void) | undefined;
  const subscribeThread = () => {
    const thread = useConsole.getState().threadId;
    if (thread && socket?.readyState === WebSocket.OPEN) {
      socket.send(
        JSON.stringify({ op: "subscribe", topics: [`thread:${thread}`] }),
      );
      void refreshThread(thread).catch((e) =>
        useConsole.setState({ error: String(e) }),
      );
    }
  };
  const unsub = useConsole.subscribe((s, previous) => {
    if (s.threadId !== previous.threadId) {
      if (previous.threadId && socket?.readyState === WebSocket.OPEN)
        socket.send(
          JSON.stringify({
            op: "unsubscribe",
            topics: [`thread:${previous.threadId}`],
          }),
        );
      subscribeThread();
    }
  });
  async function open() {
    if (stopped) return;
    if (MOCK) {
      const { startMock } = await import("@/mocks/service");
      if (!stopped) cleanupMock = startMock();
      useConsole.setState({ connected: true, stale: false });
      return;
    }
    const base = import.meta.env.VITE_API_URL || location.origin;
    socket = new WebSocket(`${base.replace(/^http/, "ws")}/api/ws`);
    socket.onopen = async () => {
      attempt = 0;
      useConsole.setState({ connected: true, stale: false });
      socket?.send(JSON.stringify({ op: "subscribe", topics }));
      subscribeThread();
      const seq = useConsole.getState().lastSeq;
      if (seq) socket?.send(JSON.stringify({ op: "resume", since_seq: seq }));
      try {
        await hydrate();
      } catch (e) {
        useConsole.setState({ error: String(e) });
      }
    };
    socket.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data) as Event;
        if (event.type) useConsole.getState().ingest(event);
      } catch {
        useConsole.setState({
          error:
            "An unreadable realtime update was received. Reconnect to refresh state.",
        });
      }
    };
    socket.onclose = () => {
      useConsole.setState({ connected: false, stale: true });
      if (!stopped)
        retry = setTimeout(open, Math.min(1000 * 2 ** attempt++, 15000));
    };
    socket.onerror = () => socket?.close();
  }
  void open();
  return () => {
    stopped = true;
    if (retry) clearTimeout(retry);
    cleanupMock?.();
    socket?.close();
    unsub();
  };
}
