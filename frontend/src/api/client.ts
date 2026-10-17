import { QueryClient } from '@tanstack/react-query';
import { resetRuntime, useConsole, type ConsoleState } from '@/realtime/store';
import type { Schema } from './types';

export const MOCK = import.meta.env.VITE_MOCK === '1';
export const queryClient = new QueryClient({defaultOptions: {queries: {retry: 1, staleTime: 10000, refetchOnWindowFocus: false}}});
export async function api<T>(path: string, body?: object): Promise<T> {
  if (MOCK) {
    const { mockRequest } = await import('@/mocks/service');
    return mockRequest(path, body ? {...body, actor: useConsole.getState().actor} : undefined) as Promise<T>;
  }
  const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api${path}`, {
      method: body ? 'POST' : 'GET', signal: controller.signal,
      headers: {'Content-Type': 'application/json'},
      body: body ? JSON.stringify({...body, actor: useConsole.getState().actor}) : undefined,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error?.message || `Request failed (${response.status})`);
    return data as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw new Error('The backend did not respond. Check that it is running on port 8000.');
    throw error;
  } finally { clearTimeout(timer); }
}
export async function mutate(path: string, body: object = {}) {
  try {
    const result = await api<Record<string,unknown>>(path, body);
    if(path==='/system/read-only'&&typeof result.read_only==='boolean')useConsole.setState({readOnly:result.read_only});
    if(path==='/sim/replay'&&typeof result.replay_mode==='string')useConsole.setState({replay:result.replay_mode});
    if(!MOCK&&(path==='/sim/reset'||path==='/sim/start')){resetRuntime();await hydrate();}
    await queryClient.invalidateQueries(); return result;
  }
  catch (e) { useConsole.setState({error: e instanceof Error ? e.message : String(e)}); throw e; }
}
export async function hydrate() {
  const [status, users, health, incidents, claims, ledger, approvals, episodes, audit, metrics] = await Promise.allSettled([
    api<Schema<'SystemStatus'>>('/system/status'), api<Schema<'UsersResponse'>>('/users'), api<Schema<'HealthResponse'>>('/health'),
    api<Schema<'IncidentsResponse'>>('/incidents'), api<Schema<'ClaimsResponse'>>('/claims'),
    api<Schema<'LedgerResponse'>>('/ledger'), api<Schema<'ApprovalsResponse'>>('/approvals'),
    api<Schema<'EpisodesResponse'>>('/episodes?status=open'), api<Schema<'AuditResponse'>>('/audit?limit=200'),
    api<Schema<'MetricsResponse'>>('/metrics?keys=cpu.*.busy,svc.atm.p95_ms,svc.pos.p95_ms&window_s=900'),
  ]);
  const patch:Partial<ConsoleState>={error:null};const errors:string[]=[];
  const accept=<T,>(result:PromiseSettledResult<T>,name:string,apply:(v:T)=>void)=>{if(result.status==='fulfilled')apply(result.value);else errors.push(`${name}: ${result.reason instanceof Error?result.reason.message:String(result.reason)}`);};
  accept(status,'System',v=>{patch.sim=v.sim;patch.readOnly=v.read_only;patch.replay=v.replay_mode;});
  accept(users,'Personas',v=>{patch.users=v.users;});accept(health,'Health',v=>{patch.health=v;});
  accept(incidents,'Incidents',v=>{patch.incidents=v.incidents;});accept(claims,'Claims',v=>{patch.claims=v.claims;});
  accept(ledger,'Ledger',v=>{patch.ledger=v.entries;});accept(approvals,'Approvals',v=>{patch.approvals=v.approvals;});
  accept(episodes,'Episodes',v=>{patch.episodes=v.episodes;});accept(audit,'Audit',v=>{patch.audit=v.rows;});
  accept(metrics,'Metric history',v=>{
    const current=useConsole.getState();patch.series={...current.series};patch.values={...current.values};
    for(const series of v.series){if(series.points.length){patch.series[series.key]=series.points;patch.values[series.key]=series.points.at(-1)![1];}}
  });
  if(errors.length)patch.error=errors.join(' · ');useConsole.setState(patch);
  const incident = useConsole.getState().incidents.at(-1);
  const threadId = incident?.thread_id || useConsole.getState().threadId;
  if (threadId) {
    await refreshThread(threadId);
    if (incident) {
      const timeline = await api<Schema<'TimelineResponse'>>(`/incidents/${incident.id}/timeline`);
      useConsole.setState({timeline: timeline.items});
    }
  }
}
export async function refreshThread(threadId:string) {
  const thread=await api<Schema<'ThreadDetail'>>(`/threads/${threadId}`);
  const current=useConsole.getState();
  const cards=[...thread.cards.filter(c=>!current.cards.some(x=>x.id===c.id)),...current.cards].sort((a,b)=>(a.seq||0)-(b.seq||0));
  const trace=[...thread.trace.filter(t=>!current.trace.some(x=>x.run_id===t.run_id&&(x.step_id||x.node)===(t.step_id||t.node))),...current.trace];
  useConsole.setState({threadId,cards:cards as import('./types').Card[],trace,interrupts:thread.pending_interrupts});
}
