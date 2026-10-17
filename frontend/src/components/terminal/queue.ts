import type { TerminalEvent } from "@/api/types";
type Ghost = TerminalEvent["payload"];

/** A command and its output remain together even when parallel executions interleave. */
export class TerminalQueue {
  private work = Promise.resolve();
  private outputs = new Map<string, string[]>();
  private waiting = new Map<string, (lines: string[]) => void>();
  private seen = new Set<string>();
  private disposed = false;
  private pending = 0;
  get busy() {
    return this.pending > 0;
  }
  constructor(
    private handlers: {
      ghost: (p: Ghost) => Promise<void>;
      output: (lines: string[]) => void;
      system: (text: string) => void;
      prompt: (text: string) => void;
    },
  ) {}
  push(event: TerminalEvent) {
    const p = event.payload;
    if (event.type === "terminal.output" && p.exec_id) {
      const resolve = this.waiting.get(p.exec_id);
      if (resolve) {
        this.waiting.delete(p.exec_id);
        resolve(p.lines || []);
      } else this.outputs.set(p.exec_id, p.lines || []);
    } else if (
      event.type === "terminal.ghost" &&
      p.exec_id &&
      !this.seen.has(p.exec_id)
    ) {
      const id = p.exec_id;
      this.seen.add(id);
      this.pending++;
      const output = new Promise<string[]>((resolve) => {
        const buffered = this.outputs.get(id);
        if (buffered) {
          this.outputs.delete(id);
          resolve(buffered);
        } else this.waiting.set(id, resolve);
      });
      this.work = this.work
        .then(async () => {
          if (this.disposed) return;
          await this.handlers.ghost(p);
          const lines = await output;
          if (!this.disposed) {
            this.handlers.output(lines);
            this.handlers.prompt("$SYSTEM STARTUP 16> ");
          }
        })
        .finally(() => {
          this.pending--;
        });
    } else if (event.type === "terminal.system") {
      this.work = this.work.then(() => {
        if (!this.disposed) this.handlers.system(p.text || "");
      });
    } else if (event.type === "terminal.prompt" && !this.busy) {
      this.work = this.work.then(() => {
        if (!this.disposed) this.handlers.prompt(p.text || "");
      });
    }
  }
  async idle() {
    await this.work;
  }
  dispose() {
    this.disposed = true;
    for (const resolve of this.waiting.values()) resolve([]);
    this.waiting.clear();
    this.outputs.clear();
  }
}
