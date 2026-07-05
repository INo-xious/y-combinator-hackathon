'use client';

import React, { useState } from 'react';
import { Trace } from '@/data/traces';
import { 
  GitCompare, ArrowRight, ShieldAlert, CheckCircle2, 
  RefreshCw, FileText, Info, Code, Hash, Copy, Download 
} from 'lucide-react';

interface CompareRunsViewProps {
  onSelectTrace: (traceId: string) => void;
  onNavigate: (view: string) => void;
  traces: Trace[];
}

export default function CompareRunsView({
  onSelectTrace,
  onNavigate,
  traces,
}: CompareRunsViewProps) {
  const [selectedTraceId, setSelectedTraceId] = useState<string>('research-agent');

  const trace = traces.find(t => t.id === selectedTraceId) || traces[0];
  const isDiverged = trace ? trace.replayStatus === 'diverged' : false;

  return (
    <div className="p-6 space-y-6">
      {/* View Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Compare Trace Replays</h2>
          <p className="text-sm text-brand-secondary">
            Cross-examine current execution DAG block outputs against saved cryptographic baselines.
          </p>
        </div>

        {/* Trace Selection Selector */}
        <div className="flex items-center gap-3">
          <span className="text-xs text-brand-secondary">Compare Execution:</span>
          <select 
            value={selectedTraceId} 
            onChange={(e) => setSelectedTraceId(e.target.value)}
            className="bg-brand-card border border-brand-border text-white text-xs rounded-xl px-3 py-2 font-semibold outline-none focus:border-brand-primary cursor-pointer"
          >
            {traces.map(t => (
              <option key={t.id} value={t.id} className="bg-brand-card text-white">
                {t.name} ({t.replayStatus})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Divergence Status Banner */}
      {isDiverged ? (
        <div className="bg-brand-divergence/10 border border-brand-divergence/30 rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 animate-shake">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-divergence/20 flex items-center justify-center shrink-0">
              <ShieldAlert className="w-5 h-5 text-brand-divergence" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-wide">Replay Divergence Detected</h3>
              <p className="text-xs text-brand-secondary mt-1">
                The output generated at step 4 (<span className="text-white font-semibold">Synthesize Report</span>) does not match the baseline hash. A source code edit or model parameter modification occurred.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[10px] bg-brand-divergence/25 border border-brand-divergence/35 text-white font-mono px-2.5 py-1 rounded font-semibold">
              HASH MISMATCH
            </span>
          </div>
        </div>
      ) : (
        <div className="bg-brand-success/10 border border-brand-success/30 rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-success/20 flex items-center justify-center shrink-0">
              <CheckCircle2 className="w-5 h-5 text-brand-success" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-wide">Replay Identical</h3>
              <p className="text-xs text-brand-secondary mt-1">
                All {trace.nodesCount} DAG block execution hashes match the baseline perfectly. Replay was executed locally in {trace.replayTime} without calling external APIs.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[10px] bg-brand-success/25 border border-brand-success/35 text-white font-mono px-2.5 py-1 rounded font-semibold">
              ✓ VERIFIED MATCH
            </span>
          </div>
        </div>
      )}

      {/* Hash Metadata comparison */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-brand-card border border-brand-border p-4 rounded-xl space-y-1">
          <span className="text-[10px] font-semibold text-brand-secondary uppercase tracking-wider block">Target Node</span>
          <span className="text-sm font-bold text-white block">
            {isDiverged ? 'Synthesize Report (r4)' : 'All Nodes Matched'}
          </span>
        </div>
        <div className="bg-brand-card border border-brand-border p-4 rounded-xl space-y-1">
          <span className="text-[10px] font-semibold text-brand-secondary uppercase tracking-wider block">Baseline Hash (Expected)</span>
          <span className="text-sm font-mono text-brand-success font-semibold flex items-center gap-1.5">
            <Hash className="w-3.5 h-3.5 text-brand-success" />
            <span>{isDiverged ? '3f4b5c6d7e8f9012' : trace.hash.substring(0, 16)}</span>
          </span>
        </div>
        <div className="bg-brand-card border border-brand-border p-4 rounded-xl space-y-1">
          <span className="text-[10px] font-semibold text-brand-secondary uppercase tracking-wider block">Replay Hash (Actual)</span>
          <span className={`text-sm font-mono font-semibold flex items-center gap-1.5 ${
            isDiverged ? 'text-brand-divergence' : 'text-brand-success'
          }`}>
            <Hash className="w-3.5 h-3.5" />
            <span>{isDiverged ? '98d7e6c5b4a3f210' : trace.hash.substring(0, 16)}</span>
          </span>
        </div>
      </div>

      {/* Split Screen Panel Comparison */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Expected Run Left */}
        <div className="bg-brand-card border border-brand-border rounded-xl flex flex-col h-[420px]">
          <div className="p-3.5 border-b border-brand-border bg-[#090F1B]/50 flex justify-between items-center shrink-0">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-brand-success" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-brand-secondary">Baseline Run (Expected)</h3>
            </div>
            <span className="text-[10px] font-mono text-brand-secondary">gpt-4o / sonnet</span>
          </div>

          <div className="flex-1 p-3 overflow-y-auto font-mono text-xs text-brand-secondary bg-[#080d19]/60 rounded-b-xl">
            {isDiverged ? (
              <div className="space-y-3">
                <div className="bg-brand-bg/80 p-2.5 rounded-lg border border-brand-border/60">
                  <span className="text-[9px] uppercase font-bold text-brand-success block mb-1">PROMPT CONFIG</span>
                  <div className="flex items-center gap-2 text-slate-300 font-mono text-[11px]">
                    <span className="text-slate-500">1</span>
                    <span className="text-emerald-500 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/15">&quot;temperature&quot;: 0.2</span>
                  </div>
                </div>
                
                <div className="bg-brand-bg/85 rounded-lg border border-brand-border/80 overflow-hidden">
                  <div className="bg-brand-bg/40 px-3 py-1.5 border-b border-brand-border text-[9px] font-bold text-slate-500 uppercase tracking-wider select-none">
                    Report Text Output (Expected Baseline)
                  </div>
                  <div className="py-2 divide-y divide-brand-border/10">
                    {[
                      { num: 1, type: 'equal', text: '## Analysis of LLM Context Caching Benefits' },
                      { num: 2, type: 'equal', text: '' },
                      { num: 3, type: 'equal', text: '### 1. Cost Savings' },
                      { num: 4, type: 'delete', text: 'By reusing KV caches, prompt caching cuts input token expenses significantly. For Claude 3.5 Sonnet, developers save 90% on prompt tokens for cached segments, yielding substantial cost reductions.' },
                      { num: 5, type: 'equal', text: '' },
                      { num: 6, type: 'equal', text: '### 2. Latency Optimization' },
                      { num: 7, type: 'delete', text: 'Benchmarks verify a massive reduction in Time-to-First-Token (TTFT). In verified tests, execution latency dropped from 4.8 seconds to 1.2 seconds, resulting in a 75% speedup.' },
                      { num: 8, type: 'equal', text: '' },
                      { num: 9, type: 'equal', text: '### 3. Conclusion' },
                      { num: 10, type: 'delete', text: 'Context caching is essential for RAG pipelines and long-context applications.' }
                    ].map((line, idx) => (
                      <div 
                        key={idx} 
                        className={`flex items-start py-1 px-3 font-mono text-[11px] leading-relaxed transition ${
                          line.type === 'delete' 
                            ? 'bg-red-950/20 text-red-300 border-l-2 border-red-500' 
                            : 'text-slate-400 hover:bg-brand-bg/30'
                        }`}
                      >
                        <span className="w-6 shrink-0 text-slate-600 text-right pr-2 select-none font-mono text-[10px]">{line.num}</span>
                        <span className="w-4 shrink-0 select-none text-center font-bold text-red-500/70">{line.type === 'delete' ? '-' : ' '}</span>
                        <span className="whitespace-pre-wrap">{line.text || ' '}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-24 text-center space-y-3">
                <CheckCircle2 className="w-12 h-12 text-brand-success mx-auto opacity-80 animate-pulse" />
                <h4 className="font-bold text-white text-sm">Baseline Intact</h4>
                <p className="text-brand-secondary text-xs max-w-xs mx-auto">
                  Run matches the original baseline signature. Select a diverged trace like &quot;Research Agent&quot; from the dropdown to view code/output differences.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Actual Run Right */}
        <div className="bg-brand-card border border-brand-border rounded-xl flex flex-col h-[420px]">
          <div className="p-3.5 border-b border-brand-border bg-[#090F1B]/50 flex justify-between items-center shrink-0">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${isDiverged ? 'bg-brand-divergence animate-pulse' : 'bg-brand-success'}`} />
              <h3 className="text-xs font-bold uppercase tracking-wider text-brand-secondary">Current Replay Run (Actual)</h3>
            </div>
            <span className="text-[10px] font-mono text-brand-secondary">gpt-4o / sonnet</span>
          </div>

          <div className="flex-1 p-3 overflow-y-auto font-mono text-xs text-brand-secondary bg-[#080d19]/60 rounded-b-xl">
            {isDiverged ? (
              <div className="space-y-3">
                <div className="bg-brand-bg/80 p-2.5 rounded-lg border border-brand-divergence/20">
                  <span className="text-[9px] uppercase font-bold text-brand-divergence block mb-1">PROMPT CONFIG (MODIFIED)</span>
                  <div className="flex items-center gap-2 text-slate-300 font-mono text-[11px]">
                    <span className="text-slate-500">1</span>
                    <span className="text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded border border-red-500/15">&quot;temperature&quot;: 0.7</span>
                  </div>
                </div>
                
                <div className="bg-brand-bg/85 rounded-lg border border-brand-border/80 overflow-hidden">
                  <div className="bg-brand-bg/40 px-3 py-1.5 border-b border-brand-border text-[9px] font-bold text-slate-500 uppercase tracking-wider select-none">
                    Report Text Output (Current Replay)
                  </div>
                  <div className="py-2 divide-y divide-brand-border/10">
                    {[
                      { num: 1, type: 'equal', text: '## Analysis of LLM Context Caching Benefits' },
                      { num: 2, type: 'equal', text: '' },
                      { num: 3, type: 'equal', text: '### 1. Cost Savings' },
                      { num: 4, type: 'add', text: 'By reusing KV caches, prompt caching cuts input token expenses significantly. For Claude 3.5 Sonnet, developers save 50% on prompt tokens for cached segments, which is lower than expected.' },
                      { num: 5, type: 'equal', text: '' },
                      { num: 6, type: 'equal', text: '### 2. Latency Optimization' },
                      { num: 7, type: 'add', text: 'Benchmarks verify a minor reduction in Time-to-First-Token (TTFT). In verified tests, execution latency dropped from 4.8 seconds to 3.6 seconds, resulting in a 25% speedup only.' },
                      { num: 8, type: 'equal', text: '' },
                      { num: 9, type: 'equal', text: '### 3. Conclusion' },
                      { num: 10, type: 'add', text: 'Context caching shows marginal performance improvements with the new model configuration.' }
                    ].map((line, idx) => (
                      <div 
                        key={idx} 
                        className={`flex items-start py-1 px-3 font-mono text-[11px] leading-relaxed transition ${
                          line.type === 'add' 
                            ? 'bg-emerald-950/20 text-emerald-300 border-l-2 border-emerald-500' 
                            : 'text-slate-400 hover:bg-brand-bg/30'
                        }`}
                      >
                        <span className="w-6 shrink-0 text-slate-600 text-right pr-2 select-none font-mono text-[10px]">{line.num}</span>
                        <span className="w-4 shrink-0 select-none text-center font-bold text-emerald-500/70">{line.type === 'add' ? '+' : ' '}</span>
                        <span className="whitespace-pre-wrap">{line.text || ' '}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-24 text-center space-y-3">
                <CheckCircle2 className="w-12 h-12 text-brand-success mx-auto opacity-80" />
                <h4 className="font-bold text-white text-sm">Replay Run Matches</h4>
                <p className="text-brand-secondary text-xs max-w-xs mx-auto">
                  All cached model response strings, prompt parameters, and token sizes are 100% verified.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Diff Actions Ribbon */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center p-4 border border-brand-border bg-brand-card rounded-xl gap-4">
        <div className="flex items-center gap-2.5 text-xs text-brand-secondary">
          <Info className="w-4 h-4 text-brand-primary" />
          <span>
            {isDiverged 
              ? 'Divergence was caused by changes in temperature (0.2 -> 0.7) causing the model to summarize differently.' 
              : 'This trace matches baseline perfectly.'}
          </span>
        </div>
        <div className="flex gap-3">
          <button className="px-3.5 py-1.5 bg-brand-card hover:bg-brand-border border border-brand-border text-brand-secondary hover:text-white rounded-lg text-xs font-semibold transition">
            Export Diff Log
          </button>
          <button 
            onClick={() => {
              onSelectTrace(selectedTraceId);
              onNavigate('replay');
            }}
            className="px-3.5 py-1.5 bg-brand-primary hover:bg-brand-primary/80 text-white rounded-lg text-xs font-semibold transition"
          >
            Replay Again
          </button>
        </div>
      </div>
    </div>
  );
}
