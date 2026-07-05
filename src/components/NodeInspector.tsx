'use client';

import React, { useState } from 'react';
import { 
  Sparkles, Wrench, Database, PlayCircle, CheckCircle2, Cpu, 
  Copy, Check, FileDown, Play, ExternalLink, Hash, Info 
} from 'lucide-react';
import { TraceNode } from '@/data/traces';

interface NodeInspectorProps {
  node: TraceNode | null;
  onReplayFromHere?: (nodeId: string) => void;
}

export default function NodeInspector({ node, onReplayFromHere }: NodeInspectorProps) {
  const [copiedPrompt, setCopiedPrompt] = useState(false);
  const [copiedResponse, setCopiedResponse] = useState(false);

  if (!node) {
    return (
      <aside className="w-80 border-l border-brand-border bg-[#090F1B] p-6 flex flex-col items-center justify-center text-center shrink-0">
        <Info className="w-8 h-8 text-brand-secondary mb-3 animate-pulse" />
        <h4 className="text-sm font-semibold text-white">No Node Selected</h4>
        <p className="text-xs text-brand-secondary mt-1">
          Select any node in the DAG visualization or scrub the timeline slider to view execution details.
        </p>
      </aside>
    );
  }

  const { data } = node;

  const handleCopy = (text: string, type: 'prompt' | 'response') => {
    navigator.clipboard.writeText(text);
    if (type === 'prompt') {
      setCopiedPrompt(true);
      setTimeout(() => setCopiedPrompt(false), 2000);
    } else {
      setCopiedResponse(true);
      setTimeout(() => setCopiedResponse(false), 2000);
    }
  };

  const getBadgeStyle = () => {
    switch (data.type) {
      case 'start': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      case 'llm': return 'bg-brand-hash/10 text-brand-hash border-brand-hash/20';
      case 'tool': return 'bg-brand-recording/10 text-brand-recording border-brand-recording/20';
      case 'db': return 'bg-teal-500/10 text-teal-400 border-teal-500/20';
      case 'finish': return 'bg-brand-success/10 text-brand-success border-brand-success/20';
      default: return 'bg-brand-border text-brand-secondary border-brand-border';
    }
  };

  const getNodeIcon = () => {
    switch (data.type) {
      case 'start': return PlayCircle;
      case 'llm': return Sparkles;
      case 'tool': return Wrench;
      case 'db': return Database;
      case 'finish': return CheckCircle2;
      default: return Cpu;
    }
  };

  const IconNode = getNodeIcon();

  return (
    <aside className="w-96 border-l border-brand-border bg-[#090F1B] flex flex-col justify-between shrink-0 h-[calc(100vh-4rem)] overflow-y-auto">
      {/* Node Header Info */}
      <div className="p-4 border-b border-brand-border space-y-3 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full border text-[10px] font-mono uppercase font-bold tracking-wider ${getBadgeStyle()}`}>
              <IconNode className="w-3 h-3" />
              <span>{data.type}</span>
            </span>
            {data.toolName && (
              <span className="text-[10px] text-brand-secondary font-mono">({data.toolName})</span>
            )}
          </div>
          <span className="text-[10px] text-brand-secondary font-mono">ID: {node.id}</span>
        </div>
        
        <div>
          <h3 className="text-sm font-bold text-white leading-tight">{data.label}</h3>
          <div className="flex items-center gap-2 mt-2 font-mono text-[10px] text-brand-secondary">
            <Hash className="w-3 h-3 text-brand-hash" />
            <span className="text-brand-hash">SHA-256: {data.hash}</span>
          </div>
        </div>
      </div>

      {/* Latency & Cost Details Cards */}
      <div className="p-4 border-b border-brand-border grid grid-cols-3 gap-2 text-center shrink-0">
        <div className="bg-brand-card border border-brand-border p-2 rounded-xl">
          <span className="text-[9px] font-semibold text-brand-secondary uppercase block">Latency</span>
          <span className="text-xs font-bold text-white block mt-1">{data.latency}</span>
        </div>
        <div className="bg-brand-card border border-brand-border p-2 rounded-xl">
          <span className="text-[9px] font-semibold text-brand-secondary uppercase block">Token Count</span>
          <span className="text-xs font-bold text-white block mt-1">
            {data.tokens ? data.tokens.total : 'N/A'}
          </span>
        </div>
        <div className="bg-brand-card border border-brand-border p-2 rounded-xl">
          <span className="text-[9px] font-semibold text-brand-secondary uppercase block">Est. Cost</span>
          <span className="text-xs font-bold text-white block mt-1">
            {data.cost > 0 ? `$${data.cost.toFixed(4)}` : '$0.00'}
          </span>
        </div>
      </div>

      {/* Node Inputs / Outputs Console */}
      <div className="flex-1 p-4 space-y-4 overflow-y-auto">
        {/* Prompts container */}
        {data.prompt && (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[10px] uppercase font-bold tracking-wider text-brand-secondary">
              <span>System / Input Prompt</span>
              <button 
                onClick={() => handleCopy(data.prompt || '', 'prompt')}
                className="flex items-center gap-1 text-[10px] text-brand-primary hover:underline font-mono"
              >
                {copiedPrompt ? <Check className="w-3 h-3 text-brand-success" /> : <Copy className="w-3 h-3" />}
                <span>{copiedPrompt ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <div className="bg-brand-card border border-brand-border p-2.5 rounded-xl max-h-36 overflow-y-auto font-mono text-[11px] text-brand-secondary whitespace-pre-wrap leading-relaxed">
              {data.prompt}
            </div>
          </div>
        )}

        {/* Responses container */}
        {data.response && (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[10px] uppercase font-bold tracking-wider text-brand-secondary">
              <span>Raw Response Output</span>
              <button 
                onClick={() => handleCopy(data.response || '', 'response')}
                className="flex items-center gap-1 text-[10px] text-brand-primary hover:underline font-mono"
              >
                {copiedResponse ? <Check className="w-3 h-3 text-brand-success" /> : <Copy className="w-3 h-3" />}
                <span>{copiedResponse ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <div className="bg-brand-card border border-brand-border p-2.5 rounded-xl max-h-36 overflow-y-auto font-mono text-[11px] text-brand-secondary whitespace-pre-wrap leading-relaxed">
              {data.response}
            </div>
          </div>
        )}

        {/* Input JSON */}
        {data.inputJson && (
          <div className="space-y-1.5">
            <span className="text-[10px] uppercase font-bold tracking-wider text-brand-secondary block">
              Input Parameters (JSON)
            </span>
            <pre className="bg-brand-card border border-brand-border p-2.5 rounded-xl overflow-x-auto font-mono text-[10px] text-brand-secondary leading-relaxed max-h-40">
              {data.inputJson}
            </pre>
          </div>
        )}

        {/* Output JSON */}
        {data.outputJson && (
          <div className="space-y-1.5">
            <span className="text-[10px] uppercase font-bold tracking-wider text-brand-secondary block">
              Output Payload (JSON)
            </span>
            <pre className="bg-brand-card border border-brand-border p-2.5 rounded-xl overflow-x-auto font-mono text-[10px] text-brand-secondary leading-relaxed max-h-40">
              {data.outputJson}
            </pre>
          </div>
        )}
      </div>

      {/* Node Actions Footer */}
      <div className="p-4 border-t border-brand-border bg-[#090F1B] shrink-0 space-y-2">
        {onReplayFromHere && (
          <button 
            onClick={() => onReplayFromHere(node.id)}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-brand-primary hover:bg-brand-primary/80 transition text-xs font-semibold text-white shadow-lg shadow-brand-primary/20"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Replay From Here</span>
          </button>
        )}
        <div className="grid grid-cols-2 gap-2">
          <button className="flex items-center justify-center gap-1.5 py-2 border border-brand-border bg-brand-card hover:bg-brand-border text-brand-secondary hover:text-white rounded-lg text-[11px] font-semibold transition">
            <FileDown className="w-3.5 h-3.5" />
            <span>Export Node</span>
          </button>
          <button className="flex items-center justify-center gap-1.5 py-2 border border-brand-border bg-brand-card hover:bg-brand-border text-brand-secondary hover:text-white rounded-lg text-[11px] font-semibold transition">
            <ExternalLink className="w-3.5 h-3.5" />
            <span>View Source</span>
          </button>
        </div>
      </div>
    </aside>
  );
}
