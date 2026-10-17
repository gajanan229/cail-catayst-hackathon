import { useState } from "react";
import { CircleHelp, Send } from "lucide-react";
import { mutate } from "@/api/client";
import { useConsole } from "@/realtime/store";
import { ActorStamp } from "./common";
import { Button } from "./ui/button";
export function InterruptPrompt() {
  const interrupt = useConsole((s) =>
    s.interrupts.find((i) => !i.resolved && i.kind !== "approval"),
  );
  const connected = useConsole((s) => s.connected);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  if (!interrupt) return null;
  return (
    <form
      className="interrupt-prompt"
      onSubmit={(e) => {
        e.preventDefault();
        setBusy(true);
        void mutate(`/threads/${interrupt.thread_id}/resume`, {
          interrupt_id: interrupt.id,
          response: text,
        })
          .then(() => setText(""))
          .catch(() => {})
          .finally(() => setBusy(false));
      }}
    >
      <div className="inline-gap">
        <CircleHelp size={15} />
        <strong>Baton needs your input</strong>
      </div>
      <p>{interrupt.prompt}</p>
      <label>
        Your answer
        <input value={text} onChange={(e) => setText(e.target.value)} />
      </label>
      <div className="card-actions">
        <Button
          variant="default"
          type="submit"
          disabled={!connected || !text.trim() || busy}
        >
          <Send size={12} />
          {busy ? "Sending…" : "Continue"}
        </Button>
        <ActorStamp />
      </div>
    </form>
  );
}
