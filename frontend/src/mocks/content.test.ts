import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import content from './content.json';
describe('knowledge content contract',()=>{
  it('contains the complete synthetic seed pack',()=>{
    expect(content.claims).toHaveLength(20);expect(content.claims.filter(c=>c.status==='verified')).toHaveLength(16);
    expect(content.playbooks).toHaveLength(4);expect(content.concepts).toHaveLength(20);expect(content.commands).toHaveLength(21);expect(content.incidents).toHaveLength(8);expect(content.glossary).toHaveLength(60);
    for(const c of content.claims){expect(c.synthetic).toBe(true);expect(c.source).toMatch(/^https:\/\/ftp.hp.com\//);if(c.status==='verified')expect(c.reviews[0].user).not.toBe(c.author);}
  });
  it('keeps synthetic provenance and unique IDs in every JSONL collection',()=>{
    const root=path.resolve('..','data','content');
    for(const name of fs.readdirSync(root).filter(n=>n.endsWith('.jsonl'))){
      const rows=fs.readFileSync(path.join(root,name),'utf8').trim().split('\n').map(line=>JSON.parse(line));
      expect(new Set(rows.map(r=>r.id)).size).toBe(rows.length);
      for(const r of rows){expect(r.synthetic).toBe(true);expect(r.source).toMatch(/^https:\/\//);}
    }
  });
  it('has undo and escalation guidance in the golden path playbook',()=>{
    const playbook=content.playbooks.find(p=>p.id==='PB-CPU-LOSS-PEAK')!;
    expect(playbook.steps.some(s=>s.catalog_id==='tacl.suspend_process'&&'undo' in s&&s.undo)).toBe(true);
    expect(playbook.steps.some(s=>s.kind==='escalate'&&s.text?.includes('hardware support'))).toBe(true);
  });
});
