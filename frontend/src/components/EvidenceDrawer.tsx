import { useQuery } from '@tanstack/react-query';
import { ExternalLink, FileText } from 'lucide-react';
import { api } from '@/api/client';
import { useConsole } from '@/realtime/store';
import { Dialog } from './ui/dialog';
import { Badge, Empty, ErrorState, Loading } from './common';
import { MetricChart } from './charts/MetricChart';
import { human } from '@/lib/utils';
import type { Inspect } from './cards/CardRenderer';

export function EvidenceDrawer({id,close}: {id:string|null;close:()=>void}) {
  const series=useConsole(s=>s.series);const health=useConsole(s=>s.health);const cards=useConsole(s=>s.cards);const episodes=useConsole(s=>s.episodes);const timeline=useConsole(s=>s.timeline);
  const metric=id?.startsWith('metric:')?id.slice(7):null;
  const localCard=cards.find(c=>c.id===id);const localComponent=health?.components.find(c=>c.id===id);const episode=episodes.find(e=>`opmsg:${e.subsystem}:${e.event_number}`===id);const evidence=cards.filter(c=>c.type==='evidence').flatMap(c=>c.body.items).find(e=>e.id===id);const fact=cards.filter(c=>c.type==='command').find(c=>c.body.execution?.exec_id===id);
  const isRemote=!!id&&!metric&&!localCard&&!localComponent&&!evidence&&!fact&&!episode;
  const query=useQuery({queryKey:['evidence',id],queryFn:()=>api<Record<string,unknown>>(`/kb/items/${encodeURIComponent(id!)}`),enabled:isRemote});
  const title=metric?metric.replaceAll('.',' / '):localCard?.title||localComponent?.name||(episode?`${episode.subsystem} ${episode.event_number}`:id)||'Evidence';
  return <Dialog open={!!id} onOpenChange={o=>!o&&close()} title={String(title)} description="Trace the displayed information back to its source." drawer><Badge tone="info"><FileText size={11}/> Source evidence</Badge><code className="evidence-id">{id}</code>
    {metric?<><p className="muted">Source: simulator telemetry · 5 simulated seconds per sample. Values are synthetic.</p><MetricChart points={series[metric]||[]} height={220} axes/><div className="metric-values">{(series[metric]||[]).slice(-8).map(([t,v])=><div key={t}><time>{t.slice(11,19)} SIM</time><strong>{v.toFixed(2)}</strong></div>)}</div>{!series[metric]?.length&&<Empty title="No samples yet">This metric will appear when telemetry arrives.</Empty>}</>:
    localComponent?<><Badge>{localComponent.state}</Badge>{localComponent.reasons.map(r=><div className="confirmation-detail" key={r.rule_id}><code>{r.rule_id}</code><p>{r.text}</p></div>)}<RecordView record={localComponent.metrics}/></>:
    episode?<><Badge tone={episode.quarantined?'warn':'neutral'}>{episode.quarantined?'Quarantined':'Operator message'}</Badge><p>{episode.example_text}</p><RecordView record={episode.manual as Record<string,unknown>}/>{episode.manual?.url&&<a className="source-link" href={episode.manual.url} target="_blank" rel="noreferrer">HPE manual <ExternalLink size={12}/></a>}</>:
    localCard?<RecordView record={localCard.body as unknown as Record<string,unknown>}/>:
    fact?.type==='command'?<><p>{fact.body.execution?.summary}</p><pre>{fact.body.execution?.raw_output}</pre><RecordView record={fact.body.execution?.facts||{}}/></>:
    evidence?<RecordView record={evidence}/>:
    query.isPending?<Loading/>:query.error?<ErrorState message={query.error.message} retry={()=>void query.refetch()}/>:query.data?<RecordView record={query.data}/>:<Empty title="No source detail available"/>}
  </Dialog>;
}
function RecordView({record}: {record:Record<string,unknown>}) {return <dl className="detail-list">{Object.entries(record).filter(([,v])=>v!=null).map(([key,value])=><div key={key}><dt>{human(key)}</dt><dd>{typeof value==='string'&&value.startsWith('https://')?<a href={value} target="_blank" rel="noreferrer">Open source chapter ↗</a>:typeof value==='object'?<pre>{JSON.stringify(value,null,2)}</pre>:String(value)}</dd></div>)}</dl>;}
