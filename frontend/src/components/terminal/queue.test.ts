import { describe, expect, it } from "vitest";
import { TerminalQueue } from "./queue";
describe("terminal execution ordering", () => {
  it("keeps parallel command outputs under their own ghost-typed command", async () => {
    const seen: string[] = [];
    const q = new TerminalQueue({
      ghost: async (p) => {
        seen.push(p.text!);
      },
      output: (lines) => seen.push(...lines),
      system: (t) => seen.push(t),
      prompt: () => {},
    });
    q.push({
      type: "terminal.ghost",
      seq: 1,
      payload: { exec_id: "a", text: "CHECK A" },
    });
    q.push({
      type: "terminal.ghost",
      seq: 2,
      payload: { exec_id: "b", text: "CHECK B" },
    });
    q.push({
      type: "terminal.output",
      seq: 3,
      payload: { exec_id: "b", lines: ["RESULT B"] },
    });
    q.push({
      type: "terminal.output",
      seq: 4,
      payload: { exec_id: "a", lines: ["RESULT A"] },
    });
    await q.idle();
    expect(seen).toEqual(["CHECK A", "RESULT A", "CHECK B", "RESULT B"]);
    expect(q.busy).toBe(false);
  });
  it("handles an output buffered before its ghost and ignores duplicate executions", async () => {
    const seen: string[] = [];
    const q = new TerminalQueue({
      ghost: async (p) => {
        seen.push(p.text!);
      },
      output: (lines) => seen.push(...lines),
      system: () => {},
      prompt: () => {},
    });
    q.push({
      type: "terminal.output",
      seq: 1,
      payload: { exec_id: "a", lines: ["RESULT A"] },
    });
    q.push({
      type: "terminal.ghost",
      seq: 2,
      payload: { exec_id: "a", text: "CHECK A" },
    });
    q.push({
      type: "terminal.ghost",
      seq: 3,
      payload: { exec_id: "a", text: "CHECK A" },
    });
    await q.idle();
    expect(seen).toEqual(["CHECK A", "RESULT A"]);
  });
});
