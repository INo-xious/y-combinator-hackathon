'use client';

import React, { useState } from 'react';
import { 
  Folder, FolderOpen, FileCode, Search, Pin, 
  Trash2, Filter, Info, Play, Calendar, Database, ShieldAlert, CheckCircle2 
} from 'lucide-react';
import { Trace } from '@/data/traces';
import { useEffect } from 'react';

interface TraceExplorerViewProps {
  onSelectTrace: (traceId: string) => void;
  onNavigate: (view: string) => void;
  traces: Trace[];
}

export default function TraceExplorerView({
  onSelectTrace,
  onNavigate,
  traces,
}: TraceExplorerViewProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFolder, setActiveFolder] = useState<string | null>('production');
  const [pinnedTraces, setPinnedTraces] = useState<string[]>(['customer-support']);
  const [selectedExplorerTraceState, setSelectedExplorerTraceState] = useState<Trace | null>(null);
  const [fullTraceDetails, setFullTraceDetails] = useState<Trace | null>(null);

  const selectedExplorerTrace = fullTraceDetails || selectedExplorerTraceState || traces[0] || null;

  useEffect(() => {
    if (!selectedExplorerTraceState && traces.length > 0) {
      setSelectedExplorerTraceState(traces[0]);
    }
  }, [traces, selectedExplorerTraceState]);

  useEffect(() => {
    const activeId = selectedExplorerTraceState?.id || traces[0]?.id;
    if (activeId) {
      fetch(`/api/traces/${activeId}`)
        .then(res => res.json())
        .then(data => {
          if (data && !data.error) {
            setFullTraceDetails(data);
          }
        })
        .catch(err => console.error('Failed to load explorer trace details:', err));
    }
  }, [selectedExplorerTraceState, traces]);

  const togglePin = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setPinnedTraces(prev => 
      prev.includes(id) ? prev.filter(t => t !== id) : [...prev, id]
    );
  };

  const filteredTraces = traces.filter(t => 
    t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (traces.length === 0 || !selectedExplorerTrace) {
    return (
      <div className="flex h-[calc(100vh-4rem)] items-center justify-center bg-[#0B1220] text-brand-secondary text-sm">
        <Info className="w-5 h-5 text-brand-primary animate-pulse mr-2" />
        <span>Loading workspace traces from filesystem...</span>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] border-b border-brand-border bg-[#0B1220] overflow-hidden">
      {/* VS Code like Left Sidebar Directory */}
      <div className="w-80 border-r border-brand-border bg-[#090F1B] flex flex-col shrink-0">
        {/* Sidebar Search */}
        <div className="p-4 border-b border-brand-border">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-brand-secondary absolute left-3 top-2.5" />
            <input 
              type="text" 
              placeholder="Search traces..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full text-xs bg-brand-bg text-brand-text pl-9 pr-4 py-2 rounded-lg border border-brand-border focus:outline-none focus:border-brand-primary"
            />
          </div>
        </div>

        {/* Directory Structure */}
        <div className="flex-1 overflow-y-auto p-2.5 space-y-4">
          {/* Pinned Traces */}
          {pinnedTraces.length > 0 && (
            <div>
              <h4 className="px-2 py-1 text-[10px] font-bold text-brand-secondary uppercase tracking-wider flex items-center gap-1.5">
                <Pin className="w-3 h-3 text-brand-primary" /> Pinned
              </h4>
              <div className="mt-1.5 space-y-0.5">
                {traces.filter(t => pinnedTraces.includes(t.id)).map(trace => (
                  <button
                    key={trace.id}
                    onClick={() => setSelectedExplorerTraceState(trace)}
                    className={`w-full flex items-center justify-between text-left px-2 py-1.5 rounded-lg text-xs transition ${
                      selectedExplorerTrace.id === trace.id 
                        ? 'bg-brand-card text-white border border-brand-border' 
                        : 'text-brand-secondary hover:text-white hover:bg-brand-card/40'
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <FileCode className="w-3.5 h-3.5 text-brand-primary shrink-0" />
                      <span className="truncate font-mono">{trace.name}.json</span>
                    </div>
                    <Pin className="w-3 h-3 text-brand-primary cursor-pointer shrink-0" onClick={(e) => togglePin(trace.id, e)} />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Folder - Production Runs */}
          <div>
            <button 
              onClick={() => setActiveFolder(activeFolder === 'production' ? null : 'production')}
              className="w-full flex items-center gap-2 px-2 py-1 text-xs font-semibold text-white hover:bg-brand-card/50 rounded-lg text-left"
            >
              {activeFolder === 'production' ? <FolderOpen className="w-4 h-4 text-brand-recording" /> : <Folder className="w-4 h-4 text-brand-secondary" />}
              <span>production-runs</span>
            </button>
            {activeFolder === 'production' && (
              <div className="pl-4 mt-1 space-y-0.5 border-l border-brand-border ml-3">
                {filteredTraces.map(trace => (
                  <button
                    key={trace.id}
                    onClick={() => setSelectedExplorerTraceState(trace)}
                    className={`w-full flex items-center justify-between text-left px-2 py-1.5 rounded-lg text-xs transition ${
                      selectedExplorerTrace.id === trace.id 
                        ? 'bg-brand-card text-white border border-brand-border' 
                        : 'text-brand-secondary hover:text-white hover:bg-brand-card/40'
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <FileCode className={`w-3.5 h-3.5 shrink-0 ${trace.replayStatus === 'success' ? 'text-brand-success' : 'text-brand-divergence'}`} />
                      <span className="truncate font-mono">{trace.name.replace(/\s+/g, '-').toLowerCase()}.json</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Dummy Empty Folders for aesthetics */}
          <div>
            <button className="w-full flex items-center gap-2 px-2 py-1 text-xs font-semibold text-brand-secondary hover:text-white hover:bg-brand-card/50 rounded-lg text-left">
              <Folder className="w-4 h-4 text-brand-secondary" />
              <span>staging-tests</span>
            </button>
          </div>
          <div>
            <button className="w-full flex items-center gap-2 px-2 py-1 text-xs font-semibold text-brand-secondary hover:text-white hover:bg-brand-card/50 rounded-lg text-left">
              <Folder className="w-4 h-4 text-brand-secondary" />
              <span>local-debug</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Column Details Area */}
      <div className="flex-1 overflow-y-auto p-6 bg-[#0B1220] flex flex-col justify-between">
        <div className="space-y-6">
          {/* File Meta Header */}
          <div className="flex justify-between items-start border-b border-brand-border pb-4">
            <div>
              <div className="flex items-center gap-2">
                <FileCode className="w-5 h-5 text-brand-primary" />
                <h3 className="text-lg font-bold text-white font-mono">{selectedExplorerTrace.name.replace(/\s+/g, '-').toLowerCase()}.json</h3>
                <span className="text-[10px] bg-brand-border px-2 py-0.5 rounded font-mono text-brand-secondary">
                  SIZE: {(selectedExplorerTrace.nodesCount * 1.2 + 0.8).toFixed(1)} KB
                </span>
              </div>
              <p className="text-xs text-brand-secondary mt-1">{selectedExplorerTrace.description}</p>
            </div>
            <button
              onClick={() => togglePin(selectedExplorerTrace.id, {} as React.MouseEvent)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-brand-border transition ${
                pinnedTraces.includes(selectedExplorerTrace.id) 
                  ? 'bg-brand-primary/10 border-brand-primary/20 text-brand-primary' 
                  : 'text-brand-secondary hover:text-white hover:bg-brand-card'
              }`}
            >
              <Pin className="w-3.5 h-3.5" />
              <span>{pinnedTraces.includes(selectedExplorerTrace.id) ? 'Pinned' : 'Pin Trace'}</span>
            </button>
          </div>

          {/* Trace Attributes Details Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-brand-card border border-brand-border p-4 rounded-xl space-y-3">
              <h4 className="text-xs font-semibold text-brand-secondary uppercase tracking-wider">Storage & Metadata</h4>
              
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-brand-border">
                  <span className="text-brand-secondary flex items-center gap-1.5"><Calendar className="w-3.5 h-3.5" /> Created Date</span>
                  <span className="text-white font-mono">2026-07-04 15:42:00</span>
                </div>
                <div className="flex justify-between py-1 border-b border-brand-border">
                  <span className="text-brand-secondary flex items-center gap-1.5"><Database className="w-3.5 h-3.5" /> Total Nodes</span>
                  <span className="text-white font-mono">{selectedExplorerTrace.nodesCount} DAG Nodes</span>
                </div>
                <div className="flex justify-between py-1 border-b border-brand-border">
                  <span className="text-brand-secondary">Cryptographic Hash</span>
                  <span className="text-brand-hash font-mono text-[11px] truncate w-40 text-right">{selectedExplorerTrace.hash}</span>
                </div>
              </div>
            </div>

            <div className="bg-brand-card border border-brand-border p-4 rounded-xl space-y-3">
              <h4 className="text-xs font-semibold text-brand-secondary uppercase tracking-wider">Replay Metrics</h4>
              
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-brand-border">
                  <span className="text-brand-secondary">Run Status</span>
                  <span className={`inline-flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider font-mono ${
                    selectedExplorerTrace.replayStatus === 'success' ? 'text-brand-success' : 'text-brand-divergence'
                  }`}>
                    {selectedExplorerTrace.replayStatus === 'success' ? (
                      <>
                        <CheckCircle2 className="w-3 h-3" />
                        <span>Replay Success</span>
                      </>
                    ) : (
                      <>
                        <ShieldAlert className="w-3 h-3" />
                        <span>Divergence Detected</span>
                      </>
                    )}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-brand-border">
                  <span className="text-brand-secondary">Average Latency Saved</span>
                  <span className="text-brand-success font-mono font-semibold">{selectedExplorerTrace.runtime} Saved (instant)</span>
                </div>
                <div className="flex justify-between py-1 border-b border-brand-border">
                  <span className="text-brand-secondary">Replay Invocations Count</span>
                  <span className="text-white font-mono">{selectedExplorerTrace.replayCount} Replays</span>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Node Preview List */}
          <div className="bg-brand-card border border-brand-border rounded-xl">
            <div className="p-3.5 border-b border-brand-border">
              <h4 className="text-xs font-semibold text-brand-secondary uppercase tracking-wider">DAG Nodes Path Preview</h4>
            </div>
            <div className="divide-y divide-brand-border">
              {selectedExplorerTrace.nodes && selectedExplorerTrace.nodes.map((node, index) => (
                <div key={node.id} className="p-3 text-xs flex items-center justify-between hover:bg-brand-border/20 transition">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-brand-secondary w-4">{index + 1}</span>
                    <span className={`w-2 h-2 rounded-full ${
                      node.data.type === 'start' ? 'bg-blue-400' :
                      node.data.type === 'llm' ? 'bg-brand-hash' :
                      node.data.type === 'tool' ? 'bg-brand-recording' :
                      node.data.type === 'db' ? 'bg-teal-400' : 'bg-brand-success'
                    }`} />
                    <span className="text-white font-medium">{node.data.label}</span>
                    {node.data.toolName && (
                      <span className="text-[10px] text-brand-secondary font-mono">({node.data.toolName})</span>
                    )}
                  </div>
                  <div className="flex items-center gap-4 text-brand-secondary font-mono text-[11px]">
                    {node.data.tokens && (
                      <span>{node.data.tokens.total} tkn</span>
                    )}
                    <span>{node.data.latency}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Bottom CTA Block */}
        <div className="flex items-center justify-between border-t border-brand-border pt-4 mt-6">
          <div className="flex items-center gap-2 text-xs text-brand-secondary">
            <Info className="w-4 h-4 text-brand-primary" />
            <span>Load this trace into the debugger main workspace.</span>
          </div>
          <button
            onClick={() => {
              onSelectTrace(selectedExplorerTrace.id);
              onNavigate('replay');
            }}
            className="flex items-center gap-2 px-4 py-2 bg-brand-primary hover:bg-brand-primary/80 transition text-xs font-semibold text-white rounded-xl shadow-lg shadow-brand-primary/20"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Open in Debugger</span>
          </button>
        </div>
      </div>
    </div>
  );
}
