import { useEffect, useRef, useState } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";
import {
  ArrowUpRight,
  TerminalSquare,
  Copy,
  Check,
  ChevronRight,
} from "lucide-react";
import { useConsole } from "@/realtime/store";
import { mutate, MOCK } from "@/api/client";
import type { TerminalEvent } from "@/api/types";
import { Badge } from "../common";
import { Button } from "../ui/button";
import { TerminalQueue } from "./queue";

export function TerminalPane() {
  const host = useRef<HTMLDivElement>(null);
  const term = useRef<Terminal>();
  const [copied, setCopied] = useState(false);
  const [line, setLine] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const connected = useConsole((s) => s.connected);
  const epoch = useConsole((s) => s.terminalEpoch);
  useEffect(() => {
    if (!host.current) return;
    const terminal = new Terminal({
      fontFamily: '"JetBrains Mono", monospace',
      fontSize: 12,
      fontWeight: "400",
      lineHeight: 1.45,
      letterSpacing: 0,
      cursorBlink: false,
      cursorStyle: "bar",
      scrollback: 2000,
      convertEol: true,
      allowProposedApi: false,
      theme: {
        background: "#f7f8fb",
        foreground: "#344155",
        cursor: "#6750c4",
        selectionBackground: "#ded6ef",
      },
      screenReaderMode: true,
    });
    term.current = terminal;
    const fit = new FitAddon();
    terminal.loadAddon(fit);
    terminal.open(host.current);
    let alive = true,
      ready = false,
      buffer = "",
      lastSeq = 0;
    const timeouts = new Set<ReturnType<typeof setTimeout>>();
    const wait = (ms: number) =>
      new Promise<void>((r) => {
        const t = setTimeout(() => {
          timeouts.delete(t);
          r();
        }, ms);
        timeouts.add(t);
      });
    const safe = (text: string) =>
      text.replace(/\x1b/g, "").replace(/[\x00-\x08\x0b-\x1f\x7f]/g, "");
    const banner = () => {
      terminal.writeln("\\TORBANK · NonStop command workspace");
      terminal.writeln(
        `${MOCK ? "Recorded rehearsal" : "Simulator session"} · Catalog commands · All executions audited`,
      );
      terminal.writeln(
        "Ready. Enter a command below or ask Baton for a check.",
      );
    };
    void document.fonts.ready.then(() => {
      if (alive) {
        if (host.current?.clientWidth && host.current?.clientHeight) fit.fit();
        banner();
        ready = true;
        consume();
      }
    });
    const queue = new TerminalQueue({
      ghost: async (p) => {
        if (!alive) return;
        terminal.write("\r\n");
        terminal.writeln(
          `\x1b[38;2;103;80;196m${safe(p.label || "Baton · approved command")}\x1b[0m`,
        );
        terminal.write("> \x1b[38;2;103;80;196m");
        const reduced = window.matchMedia(
          "(prefers-reduced-motion: reduce)",
        ).matches;
        for (const ch of safe(p.text || "")) {
          if (!alive) return;
          terminal.write(ch);
          if (!reduced) await wait(p.ms_per_char || 25);
        }
        terminal.write("\x1b[0m\r\n");
      },
      output: (lines) => {
        for (const line of lines) terminal.writeln(safe(line));
      },
      system: (text) => terminal.writeln("\r\n" + safe(text)),
      prompt: (text) => terminal.write("\r\n" + safe(text)),
    });
    const consume = () => {
      if (!ready) return;
      for (const e of useConsole.getState().terminal)
        if (e.seq > lastSeq) {
          queue.push(e);
          lastSeq = e.seq;
        }
    };
    const unsub = useConsole.subscribe(consume);
    const input = terminal.onData((data) => {
      if (queue.busy) return;
      if (data === "\r") {
        const line = buffer.trim();
        buffer = "";
        terminal.write("\r\n");
        if (line) void mutate("/terminal/input", { line }).catch(() => {});
        return;
      }
      if (data === "\x7f") {
        if (buffer.length) {
          buffer = buffer.slice(0, -1);
          terminal.write("\b \b");
        }
        return;
      }
      if (data === "\x03") {
        buffer = "";
        terminal.write("^C\r\n> ");
        return;
      }
      if (/^[\x20-\x7e]+$/.test(data)) {
        buffer += data;
        terminal.write(data);
      }
    });
    const resize = new ResizeObserver(() => {
      if (alive && host.current?.clientWidth && host.current?.clientHeight)
        fit.fit();
    });
    resize.observe(host.current);
    return () => {
      alive = false;
      resize.disconnect();
      unsub();
      input.dispose();
      queue.dispose();
      timeouts.forEach(clearTimeout);
      terminal.dispose();
      term.current = undefined;
    };
  }, [epoch]);
  return (
    <section className="terminal-pane">
      <div className="pane-title">
        <span>
          <TerminalSquare size={15} /> Terminal <Badge>01</Badge>
        </span>
        <span className="mono muted">
          \TORBANK <ArrowUpRight size={13} />
        </span>
      </div>
      <div className="terminal-toolbar">
        <span className="connection">
          <i className={connected ? "dot ok" : "dot warn"} />
          {connected ? "Session connected" : "Reconnecting"}
        </span>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Copy terminal output"
          onClick={async () => {
            if (term.current) {
              const text = Array.from(
                { length: term.current.buffer.active.length },
                (_, i) =>
                  term
                    .current!.buffer.active.getLine(i)
                    ?.translateToString(true) || "",
              ).join("\n");
              await navigator.clipboard.writeText(text);
              setCopied(true);
              setTimeout(() => setCopied(false), 1800);
            }
          }}
        >
          {copied ? <Check size={13} /> : <Copy size={13} />}
        </Button>
      </div>
      <div className="terminal-host" ref={host} aria-label="NonStop terminal" />
      <form
        className="manual-command"
        onSubmit={async (e) => {
          e.preventDefault();
          if (!line.trim() || submitting || !connected) return;
          setSubmitting(true);
          try {
            await mutate("/terminal/input", { line: line.trim() });
            setLine("");
          } catch {
            /* The shared request handler displays the backend error. */
          } finally {
            setSubmitting(false);
          }
        }}
      >
        <ChevronRight size={15} />
        <input
          aria-label="Catalog command"
          placeholder="Enter a catalog command…"
          value={line}
          onChange={(e) => setLine(e.target.value)}
          autoComplete="off"
          spellCheck={false}
        />
        <Button
          type="submit"
          size="sm"
          disabled={!connected || !line.trim() || submitting}
        >
          {submitting ? "Sending…" : "Enter ↵"}
        </Button>
      </form>
      <div className="terminal-bottom">
        <LockIcon /> Governed session <span>6530 · conversational</span>
      </div>
    </section>
  );
}
function LockIcon() {
  return <span className="dot ok" />;
}
