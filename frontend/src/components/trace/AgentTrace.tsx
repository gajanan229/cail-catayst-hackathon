import { useState } from 'react';
import { Check, ChevronDown, CirclePause, GitBranch, LoaderCircle, X } from 'lucide-react';
import { useConsole } from '@/realtime/store';
import type { Trace } from '@/api/types';
import { Dialog } from '../ui/dialog';
import { Badge, Empty } from '../common';

export function AgentTrace({full=false}: {full?:boolean}) {
  const trace=useConsole(s=>s.trace); const [expanded,setExpanded]=useState(full);const [selected,setSelected]=useState<Trace|null>(null);
  const completed=trace.filter(t=>t.status==='done'||t.status==='fallback').length;const latest=trace.at(-1);
  return <div className="agent-trace"><button className="trace-toggle" onClick={()=>setExpanded(!expanded)} aria-expanded={expanded}><GitBranch size={14}/><span><strong>Agent trace</strong><small>{latest?.label||'Ready to help'}</small></span><Badge tone="baton">{completed}/{trace.length||'—'}</Badge><ChevronDown size={13} className={expanded?'rotated':''}/></button>
    {expanded&&<div className="trace-steps">{trace.length?trace.map((t,i)=><button key={`${t.run_id}:${t.step_id||t.node}:${i}`} onClick={()=>setSelected(t)} className={`trace-step status-${t.status}`}>{t.status==='waiting'?<CirclePause size={13}/>:t.status==='running'?<LoaderCircle size={13} className="spin"/>:t.status==='failed'?<X size={13}/>:<Check size={13}/>}<span>{t.label}<small>{t.summary}</small></span><small>{t.duration_ms!=null?`${t.duration_ms} ms`:'waiting'}</small></button>):<Empty title="No active run">Steps appear here as Baton investigates.</Empty>}</div>}
    <Dialog open={!!selected} onOpenChange={o=>!o&&setSelected(null)} title={selected?.label||'Trace step'} description="Inputs, tools, evidence and output for this step." drawer>
      {selected&&<><Badge>{selected.status}</Badge><p>{selected.summary}</p><dl className="detail-list"><dt>Model source</dt><dd>{selected.detail?.model||'Deterministic'}</dd><dt>Tools</dt><dd>{selected.detail?.tools.join(', ')||'None'}</dd><dt>Evidence IDs</dt><dd>{selected.detail?.evidence_ids.join(', ')||'None'}</dd><dt>Prompt hash</dt><dd><code>{selected.detail?.prompt_hash||'Not applicable'}</code></dd><dt>Inputs</dt><dd><pre>{JSON.stringify(selected.detail?.inputs,null,2)||'No inputs recorded'}</pre></dd><dt>Output</dt><dd><pre>{JSON.stringify(selected.detail?.output,null,2)||selected.summary}</pre></dd></dl></>}
    </Dialog>
  </div>;
}
