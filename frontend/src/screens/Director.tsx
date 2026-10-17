import { useState } from "react";
import {
  CirclePause,
  Clapperboard,
  Play,
  RotateCcw,
  SkipForward,
  TriangleAlert,
} from "lucide-react";
import { mutate, MOCK } from "@/api/client";
import { useConsole } from "@/realtime/store";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ActorStamp, Badge } from "@/components/common";

export function Director({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
}) {
  const sim = useConsole((s) => s.sim);
  const replay = useConsole((s) => s.replay);
  const readOnly = useConsole((s) => s.readOnly);
  const [scenario, setScenario] = useState("S1");
  const [profile, setProfile] = useState("demo");
  const [seed, setSeed] = useState(42);
  const [cpu, setCpu] = useState(3);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const run = async (path: string, body: object = {}) => {
    setBusy(true);
    setError("");
    try {
      await mutate(path, body);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="Scenario Director"
      description="Control the simulated environment. Every control is audited."
      drawer
    >
      <div className="director-badge">
        <Clapperboard size={16} />
        <Badge tone="baton">
          {MOCK ? "Mock rehearsal" : "Simulator controls"}
        </Badge>
        <ActorStamp />
      </div>
      <section className="director-section">
        <p className="eyebrow">01 / SET THE STAGE</p>
        <label>
          Scenario
          <select
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
          >
            <option value="S1">S1 · CPU loss at Black Friday peak</option>
            <option value="S0">S0 · Healthy normal day</option>
          </select>
        </label>
        <div className="two-fields">
          <label>
            Profile
            <select
              value={profile}
              onChange={(e) => setProfile(e.target.value)}
            >
              <option value="demo">Demo · manual faults</option>
              <option value="test">Test · scheduled faults</option>
            </select>
          </label>
          <label>
            Seed
            <input
              type="number"
              value={seed}
              onChange={(e) => setSeed(Number(e.target.value))}
            />
          </label>
        </div>
        <div className="inline-gap">
          <Button
            variant="default"
            disabled={busy}
            onClick={() => void run("/sim/start", { scenario, profile, seed })}
          >
            <Play size={13} /> Start scenario
          </Button>
          <Button disabled={busy} onClick={() => void run("/sim/reset")}>
            <RotateCcw size={13} /> Reset
          </Button>
        </div>
      </section>
      <section className="director-section">
        <p className="eyebrow">02 / INTRODUCE A FAULT</p>
        <div className="fault-control">
          <div>
            <strong>Halt a processor</strong>
            <p>CPU 3 is the golden path trigger.</p>
          </div>
          <select
            aria-label="CPU to halt"
            value={cpu}
            onChange={(e) => setCpu(Number(e.target.value))}
          >
            {Array.from({ length: 8 }, (_, n) => (
              <option value={n} key={n}>
                CPU {n}
              </option>
            ))}
          </select>
        </div>
        <Button
          variant="destructive"
          className="full-width"
          disabled={busy || !sim?.running}
          onClick={() =>
            void run("/sim/inject", { fault: "cpu_halt", params: { cpu } })
          }
        >
          <TriangleAlert size={14} /> CPU {cpu} halt
        </Button>
        {!MOCK && (
          <>
            <Button
              disabled={busy}
              onClick={() =>
                void run("/sim/inject", { fault: "audit_pressure", params: {} })
              }
            >
              Inject audit pressure
            </Button>
            <Button
              disabled={busy}
              onClick={() =>
                void run("/sim/inject", {
                  fault: "maxservers_change",
                  params: { server_class: "ATM-AUTH", n: 12 },
                })
              }
            >
              Change MAXSERVERS to 12
            </Button>
          </>
        )}
      </section>
      <section className="director-section">
        <p className="eyebrow">03 / CONTROL TIME</p>
        <div className="speed-buttons">
          {[1, 2, 4, 8, 16].map((speed) => (
            <Button
              key={speed}
              variant={sim?.speed === speed ? "default" : "outline"}
              onClick={() => void run("/sim/clock", { speed })}
            >
              {speed}×
            </Button>
          ))}
        </div>
        <div className="inline-gap">
          <Button
            onClick={() => void run("/sim/clock", { paused: !sim?.paused })}
          >
            {sim?.paused ? <Play size={13} /> : <CirclePause size={13} />}{" "}
            {sim?.paused ? "Resume" : "Pause"}
          </Button>
          <Button
            disabled={!sim?.paused}
            onClick={() => void run("/sim/clock", { step: 1 })}
          >
            <SkipForward size={13} /> Single step
          </Button>
        </div>
        <p className="meta">
          Verification watches 60 simulated seconds, not wall-clock time.
        </p>
      </section>
      <section className="director-section">
        <p className="eyebrow">04 / SAFETY & REPLAY</p>
        <label>
          Model replay
          <select
            value={replay}
            onChange={(e) => void run("/sim/replay", { mode: e.target.value })}
          >
            <option value="replay">Replay · cached responses</option>
            <option value="off">Off · live / fallback</option>
            <option value="record">Record</option>
          </select>
        </label>
        <label className="switch-row">
          <span>
            Read-only mode<small>Disables state-changing approvals</small>
          </span>
          <input
            type="checkbox"
            role="switch"
            checked={readOnly}
            onChange={(e) =>
              void run("/system/read-only", { enabled: e.target.checked })
            }
          />
        </label>
      </section>
      {error && (
        <p className="crit-text" role="alert">
          {error}
        </p>
      )}
      <p className="meta director-hotkey">
        Ctrl + Shift + D · open or close Director
      </p>
    </Dialog>
  );
}
