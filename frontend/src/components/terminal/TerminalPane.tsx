import { useEffect, useRef, useState } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { ArrowUpRight, TerminalSquare, Copy, Check } from 'lucide-react';
import { useConsole } from '@/realtime/store';
import { mutate, MOCK } from '@/api/client';
import type { TerminalEvent } from '@/api/types';
import { Badge } from '../common';
import { Button } from '../ui/button';
import { TerminalQueue } from './queue';

export function TerminalPane() {
  const host=useRef<HTMLDivElement>(null);const term=useRef<Terminal>(); const [copied,setCopied]=useState(false);
  const connected=useConsole(s=>s.connected);
  useEffect(()=>{
    if(!host.current)return;
    const terminal=new Terminal({fontFamily:'"JetBrains Mono", monospace',fontSize:12,fontWeight:'400',lineHeight:1.6,letterSpacing:0,cursorBlink:false,cursorStyle:'bar',scrollback:2000,convertEol:true,allowProposedApi:false,theme:{background:'#05080A',foreground:'#39FF88',cursor:'#C4B5FD',selectionBackground:'#A78BFA44'},screenReaderMode:true});
    term.current=terminal;const fit=new FitAddon(); terminal.loadAddon(fit);terminal.open(host.current);
    let alive=true,buffer='',lastSeq=0; const timeouts=new Set<ReturnType<typeof setTimeout>>();
    const wait=(ms:number)=>new Promise<void>(r=>{const t=setTimeout(()=>{timeouts.delete(t);r();},ms);timeouts.add(t);});
    const safe=(text:string)=>text.replace(/\x1b/g,'').replace(/[\x00-\x08\x0b-\x1f\x7f]/g,'');
    const banner=()=>{
      terminal.writeln('\x1b[38;2;138;151;168mBATON / NONSTOP OPERATIONS');
      terminal.writeln('SESSION 01   \\TORBANK   TACL');
      terminal.writeln('────────────────────────────────────\x1b[0m');
      terminal.writeln('HPE NonStop · L-series');
      terminal.writeln(`${MOCK?'Mock transport':'Simulator adapter'} · catalog commands only`);
      terminal.writeln('');terminal.writeln('Welcome, Priya.');terminal.writeln('All commands are recorded in the audit log.');terminal.writeln('');
      terminal.writeln('System ready. Waiting for commands.');terminal.writeln('');terminal.write('$SYSTEM STARTUP 14> ');
    };
    void document.fonts.ready.then(()=>{if(alive){fit.fit();banner();}});
    const queue=new TerminalQueue({
      ghost:async p=>{
          if(!alive)return;terminal.write('\r\n');terminal.writeln(`\x1b[38;2;196;181;253m▸ ${safe(p.label||'Baton · approved command')}\x1b[0m`);
          terminal.write('$SYSTEM STARTUP 15> \x1b[38;2;196;181;253m');
          const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
          for(const ch of safe(p.text||'')){if(!alive)return;terminal.write(ch);if(!reduced)await wait(p.ms_per_char||25);}
          terminal.write('\x1b[0m\r\n');
      },output:lines=>{for(const line of lines)terminal.writeln(safe(line));},
      system:text=>terminal.writeln('\r\n'+safe(text)),prompt:text=>terminal.write('\r\n'+safe(text)),
    });
    const consume=()=>{for(const e of useConsole.getState().terminal)if(e.seq>lastSeq){queue.push(e);lastSeq=e.seq;}};
    consume();const unsub=useConsole.subscribe(consume);
    const input=terminal.onData(data=>{
      if(queue.busy)return;
      if(data==='\r'){const line=buffer.trim();buffer='';terminal.write('\r\n');if(line)void mutate('/terminal/input',{line}).catch(()=>{});return;}
      if(data==='\x7f'){if(buffer.length){buffer=buffer.slice(0,-1);terminal.write('\b \b');}return;}
      if(data==='\x03'){buffer='';terminal.write('^C\r\n$SYSTEM STARTUP 16> ');return;}
      if(/^[\x20-\x7e]+$/.test(data)){buffer+=data;terminal.write(data);}
    });
    const resize=new ResizeObserver(()=>{if(alive)fit.fit();});resize.observe(host.current);
    return ()=>{alive=false;resize.disconnect();unsub();input.dispose();queue.dispose();timeouts.forEach(clearTimeout);terminal.dispose();term.current=undefined;};
  },[]);
  return <section className="terminal-pane"><div className="pane-title"><span><TerminalSquare size={15}/> Terminal <Badge>01</Badge></span><span className="mono muted">\TORBANK <ArrowUpRight size={13}/></span></div>
    <div className="terminal-toolbar"><span className="connection"><i className={connected?'dot ok':'dot warn'}/>{connected?'Session connected':'Reconnecting'}</span><Button variant="ghost" size="icon" aria-label="Copy terminal output" onClick={async()=>{if(term.current){const text=Array.from({length:term.current.buffer.active.length},(_,i)=>term.current!.buffer.active.getLine(i)?.translateToString(true)||'').join('\n');await navigator.clipboard.writeText(text);setCopied(true);setTimeout(()=>setCopied(false),1800);}}}>{copied?<Check size={13}/>:<Copy size={13}/>}</Button></div>
    <div className="terminal-host" ref={host} aria-label="NonStop terminal"/>
    <div className="terminal-bottom"><LockIcon/> Governed session <span>6530 · conversational</span></div>
  </section>;
}
function LockIcon(){return <span className="dot ok"/>;}
