import { describe, expect, it, beforeEach } from 'vitest';
import { useConsole } from './store';
import type { Card, Event } from '@/api/types';
import command from '@/mocks/fixtures/cards/command.json';
import promotion from '@/mocks/fixtures/ws/ledger.promotion_candidate.json';
const event=(type:Event['type'],payload:unknown,seq:number):Event=>({type,payload,seq,topic:'thread:test',ts:'2026-10-17T00:00:00Z',sim_ts:'2026-11-27T11:52:04Z'});
describe('realtime continuity',()=>{
  beforeEach(()=>useConsole.setState({cards:[],lastSeq:0,series:{},values:{},terminal:[]}));
  it('replaces complete cards and ignores duplicate replay frames',()=>{
    const c=command as Card;useConsole.getState().ingest(event('card.upsert',c,1));
    useConsole.getState().ingest(event('card.upsert',{...c,status:'done'},2));
    useConsole.getState().ingest(event('card.upsert',{...c,status:'failed'},1));
    expect(useConsole.getState().cards).toHaveLength(1);expect(useConsole.getState().cards[0].status).toBe('done');
  });
  it('keeps contract order when cards arrive out of order',()=>{
    useConsole.getState().ingest(event('card.upsert',{...command,id:'later',seq:9},1));
    useConsole.getState().ingest(event('card.upsert',{...command,id:'earlier',seq:2},2));
    expect(useConsole.getState().cards.map(c=>c.id)).toEqual(['earlier','later']);
  });
  it('bounds telemetry history while preserving latest values',()=>{
    for(let n=1;n<=400;n++)useConsole.getState().ingest(event('telemetry.tick',{sim_ts:`2026-11-27T11:${String(Math.floor(n/60)).padStart(2,'0')}:${String(n%60).padStart(2,'0')}Z`,values:{'cpu.5.busy':n}},n));
    expect(useConsole.getState().series['cpu.5.busy']).toHaveLength(360);expect(useConsole.getState().values['cpu.5.busy']).toBe(400);
  });
  it('uses the frozen removal and promotion event envelopes',()=>{
    useConsole.getState().ingest(event('card.upsert',command,1));
    useConsole.getState().ingest(event('card.remove',{card_id:command.id,thread_id:command.thread_id},2));
    expect(useConsole.getState().cards).toHaveLength(0);
    useConsole.getState().ingest(event('ledger.promotion_candidate',promotion.payload,3));
    expect(useConsole.getState().ledger.find(e=>e.key===promotion.payload.entry.key)?.eligible_for).toBe('L2');
  });
});
