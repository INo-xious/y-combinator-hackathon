'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { 
  ReactFlow, 
  Background, 
  Controls, 
  Handle, 
  Position, 
  NodeTypes,
  Edge,
  MarkerType
} from '@xyflow/react';
import { 
  Play, Pause, SkipBack, SkipForward, Sparkles, Wrench, Database, 
  CheckCircle2, PlayCircle, Zap, ShieldAlert, Copy, RefreshCw, Cpu, Gauge 
} from 'lucide-react';
import { Trace, TraceNode } from '@/data/traces';

// Custom Node Template
const CustomNode = ({ data }: any) => {
  const Icon = useMemo(() => {
    switch (data.type) {
      case 'start': return PlayCircle;
      case 'llm': return Sparkles;
      case 'tool': return Wrench;
      case 'db': return Database;
      case 'finish': return CheckCircle2;
      default: return Cpu;
    }
  }, [data.type]);

  const typeColor = useMemo(() => {
    switch (data.type) {
      case 'start': return 'text-blue-400 border-blue-400/20 bg-blue-400/5';
      case 'llm': return 'text-brand-hash border-brand-hash/20 bg-brand-hash/5';
      case 'tool': return 'text-brand-recording border-brand-recording/20 bg-brand-recording/5';
      case 'db': return 'text-teal-400 border-teal-400/20 bg-teal-400/5';
      case 'finish': return 'text-brand-success border-brand-success/20 bg-brand-success/5';
      default: return 'text-brand-secondary border-brand-border bg-brand-card';
    }
  }, [data.type]);

  const glowClass = useMemo(() => {
    if (!data.isActive) return '';
    switch (data.type) {
      case 'start': return 'animate-glow-blue';
      case 'llm': return 'animate-glow-purple';
      case 'tool': return 'animate-glow-yellow';
      case 'db': return 'animate-glow-green';
      case 'finish': return 'animate-glow-green';
      default: return 'animate-glow-blue';
    }
  }, [data.isActive, data.type]);

  const activePingColor = useMemo(() => {
    switch (data.type) {
      case 'llm': return 'bg-brand-hash';
      case 'tool': return 'bg-brand-recording';
      case 'finish': return 'bg-brand-success';
      default: return 'bg-brand-primary';
    }
  }, [data.type]);

  return (
    <div className={`relative px-4 py-3 rounded-xl border w-60 transition-all duration-300 ${
      data.isActive 
        ? `bg-brand-card scale-103 z-10 ${glowClass}`
        : data.isCompleted
          ? 'border-brand-success/40 bg-[#0e1726]/90 shadow-[0_0_12px_rgba(16,185,129,0.04)] text-white'
          : 'border-brand-border bg-[#090f1a]/85 text-brand-secondary'
    }`}>
      {/* Handles for connections */}
      {data.type !== 'start' && (
        <Handle type="target" position={Position.Top} className="!bg-brand-border !border-brand-card !w-2.5 !h-2.5" />
      )}
      {data.type !== 'finish' && (
        <Handle type="source" position={Position.Bottom} className="!bg-brand-border !border-brand-card !w-2.5 !h-2.5" />
      )}

      {/* Node Info */}
      <div className="flex items-center gap-3">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center border shrink-0 ${typeColor}`}>
          <Icon className="w-4 h-4" />
        </div>
        <div className="grow truncate text-left">
          <span className="text-[10px] text-brand-secondary font-mono uppercase tracking-wider block">
            {data.toolName || data.type}
          </span>
          <span className={`text-xs font-semibold truncate block ${data.isCompleted && !data.isActive ? 'text-slate-100' : 'text-white'}`}>
            {data.label}
          </span>
        </div>
        {data.isActive && (
          <span className="relative flex h-2 w-2">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${activePingColor}`}></span>
            <span className={`relative inline-flex rounded-full h-2 w-2 ${activePingColor}`}></span>
          </span>
        )}
      </div>

      {/* Bottom Node Meta */}
      <div className="flex justify-between items-center mt-2.5 pt-2 border-t border-brand-border/40 text-[9px] font-mono text-brand-secondary">
        <span>SHA-256:{data.hash.substring(0, 6)}</span>
        <span>{data.latency}</span>
      </div>
    </div>
  );
};

// Node Types
const nodeTypes: NodeTypes = {
  customNode: CustomNode,
};

interface ReplayViewerProps {
  trace: Trace;
  selectedNode: TraceNode | null;
  onSelectNode: (node: TraceNode) => void;
  timelineIndex: number;
  setTimelineIndex: (index: number) => void;
  isReplaying: boolean;
  setIsReplaying: (replaying: boolean) => void;
}

export default function ReplayViewer({
  trace,
  selectedNode,
  onSelectNode,
  timelineIndex,
  setTimelineIndex,
  isReplaying,
  setIsReplaying,
}: ReplayViewerProps) {
  const [speed, setSpeed] = useState<number>(1); // ms multiplier

  // Flow nodes list mapped with active / completed statuses
  const flowNodes = useMemo(() => {
    return trace.nodes.map((node, index) => ({
      ...node,
      data: {
        ...node.data,
        isActive: index === timelineIndex,
        isCompleted: index <= timelineIndex,
      },
    }));
  }, [trace.nodes, timelineIndex]);

  // Edges list
  const flowEdges = useMemo(() => {
    return trace.edges.map((edge) => {
      const sourceIndex = trace.nodes.findIndex(n => n.id === edge.source);
      const targetIndex = trace.nodes.findIndex(n => n.id === edge.target);
      
      const isAnimated = sourceIndex <= timelineIndex && targetIndex <= timelineIndex;
      
      return {
        ...edge,
        animated: isAnimated,
        style: isAnimated ? { stroke: '#3B82F6', strokeWidth: 2 } : { stroke: '#1F2937' },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isAnimated ? '#3B82F6' : '#1F2937',
        },
      };
    });
  }, [trace.edges, trace.nodes, timelineIndex]);

  // Handle Playback Interval Loop
  useEffect(() => {
    let intervalId: NodeJS.Timeout;
    if (isReplaying) {
      intervalId = setInterval(() => {
        setTimelineIndex(timelineIndex === trace.nodes.length - 1 ? 0 : timelineIndex + 1);
      }, 1000 / speed);
    }
    return () => clearInterval(intervalId);
  }, [isReplaying, timelineIndex, trace.nodes.length, speed, setTimelineIndex]);

  // Sync selectedNode with timelineIndex if changes
  useEffect(() => {
    if (trace.nodes[timelineIndex]) {
      onSelectNode(trace.nodes[timelineIndex]);
    }
  }, [timelineIndex, trace.nodes, onSelectNode]);

  const progressPercent = ((timelineIndex) / (trace.nodes.length - 1)) * 100;

  return (
    <div className="flex-1 flex flex-col h-[calc(100vh-4rem)] bg-[#0B1220] overflow-hidden relative">
      {/* Top Replay Run Info Ribbon */}
      <div className="h-12 border-b border-brand-border bg-[#090F1B]/95 px-6 flex items-center justify-between z-10 shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-brand-success animate-pulse" />
            <span className="text-xs font-semibold text-white">Replay Engine Loaded</span>
          </div>
          <span className="text-xs text-brand-secondary border-l border-brand-border pl-4 font-mono">
            TRACE ID: {trace.hash.substring(0, 12)}
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1 text-brand-success font-semibold">
            <Zap className="w-3.5 h-3.5 fill-current" />
            <span>Replay Latency: {trace.replayTime}</span>
          </div>
          <span className="text-brand-secondary font-mono">
            Saved API Cost: <b className="text-white">{trace.moneySaved}</b>
          </span>
        </div>
      </div>

      {/* Main React Flow DAG Area */}
      <div className="grow w-full relative">
        <ReactFlow
          nodes={flowNodes}
          edges={flowEdges}
          nodeTypes={nodeTypes}
          onNodeClick={(e, node) => {
            const index = trace.nodes.findIndex(n => n.id === node.id);
            if (index !== -1) setTimelineIndex(index);
          }}
          fitView
          fitViewOptions={{ padding: 0.4 }}
          minZoom={0.5}
          maxZoom={1.5}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#1F2937" gap={16} size={1} />
          <Controls className="!bg-brand-card !border-brand-border !text-white" />
        </ReactFlow>
      </div>

      {/* Bottom Timeline Controls */}
      <div className="h-28 border-t border-brand-border bg-[#090F1B]/95 p-4 flex flex-col justify-between shrink-0 z-10">
        {/* Slider Controls */}
        <div className="flex items-center gap-4">
          <span className="text-[10px] font-semibold text-brand-secondary uppercase font-mono">Start (0.0s)</span>
          <div className="grow relative py-2 flex items-center">
            {/* Custom Track */}
            <div className="absolute left-0 right-0 h-1 rounded-full bg-brand-border" />
            {/* Custom Filled Track */}
            <div 
              className="absolute left-0 h-1 rounded-full bg-brand-primary" 
              style={{ width: `${progressPercent}%` }}
            />
            {/* Custom Range Slider */}
            <input
              type="range"
              min={0}
              max={trace.nodes.length - 1}
              value={timelineIndex}
              onChange={(e) => setTimelineIndex(parseInt(e.target.value))}
              className="w-full h-1 opacity-0 cursor-pointer z-10"
            />
            {/* Custom Handle Thumb */}
            <div 
              className="absolute w-3.5 h-3.5 rounded-full bg-white border-2 border-brand-primary shadow-[0_0_8px_rgba(59,130,246,0.8)] pointer-events-none"
              style={{ left: `calc(${progressPercent}% - 7px)` }}
            />
          </div>
          <span className="text-[10px] font-semibold text-brand-secondary uppercase font-mono">Finish ({trace.runtime})</span>
        </div>

        {/* Buttons Controls */}
        <div className="flex items-center justify-between">
          {/* Timeline Slider ticks helper */}
          <div className="flex items-center gap-4">
            <span className="text-xs text-brand-secondary">
              Step <b className="text-white font-mono">{timelineIndex + 1}</b> of <b className="text-white font-mono">{trace.nodes.length}</b>
            </span>
            <div className="flex items-center gap-1.5">
              {trace.nodes.map((node, i) => (
                <div 
                  key={node.id} 
                  onClick={() => setTimelineIndex(i)}
                  className={`h-1.5 rounded-full cursor-pointer transition ${
                    i === timelineIndex 
                      ? 'w-6 bg-brand-primary' 
                      : i < timelineIndex 
                        ? 'w-2.5 bg-brand-success/60' 
                        : 'w-1.5 bg-brand-border hover:bg-brand-secondary'
                  }`}
                  title={node.data.label}
                />
              ))}
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-3">
            <button 
              onClick={() => setTimelineIndex(0)}
              className="p-2 text-brand-secondary hover:text-white rounded-lg hover:bg-brand-card transition border border-transparent hover:border-brand-border"
              title="Rewind"
            >
              <SkipBack className="w-4 h-4" />
            </button>
            <button 
              onClick={() => setTimelineIndex(timelineIndex === 0 ? 0 : timelineIndex - 1)}
              disabled={timelineIndex === 0}
              className="p-2 text-brand-secondary hover:text-white rounded-lg hover:bg-brand-card transition disabled:opacity-30 border border-transparent hover:border-brand-border"
              title="Prev Step"
            >
              <SkipBack className="w-4 h-4 rotate-180" />
            </button>
            
            {/* Play/Pause Main Replay */}
            <button 
              onClick={() => setIsReplaying(!isReplaying)}
              className="px-5 py-2 rounded-xl bg-brand-primary text-white font-semibold text-xs flex items-center gap-2 hover:bg-brand-primary/80 transition shadow-lg shadow-brand-primary/20"
            >
              {isReplaying ? (
                <>
                  <Pause className="w-4 h-4 fill-current" />
                  <span>Pause</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>▶ Replay Trace</span>
                </>
              )}
            </button>

            <button 
              onClick={() => setTimelineIndex(timelineIndex === trace.nodes.length - 1 ? timelineIndex : timelineIndex + 1)}
              disabled={timelineIndex === trace.nodes.length - 1}
              className="p-2 text-brand-secondary hover:text-white rounded-lg hover:bg-brand-card transition disabled:opacity-30 border border-transparent hover:border-brand-border"
              title="Next Step"
            >
              <SkipForward className="w-4 h-4" />
            </button>
            <button 
              onClick={() => setTimelineIndex(trace.nodes.length - 1)}
              className="p-2 text-brand-secondary hover:text-white rounded-lg hover:bg-brand-card transition border border-transparent hover:border-brand-border"
              title="Fast Forward"
            >
              <SkipForward className="w-4 h-4 rotate-180" />
            </button>
          </div>

          {/* Speed settings */}
          <div className="flex items-center gap-2 border border-brand-border bg-brand-card px-2.5 py-1.5 rounded-xl text-xs text-brand-secondary font-mono">
            <Gauge className="w-3.5 h-3.5" />
            <span>Speed:</span>
            <select 
              value={speed} 
              onChange={(e) => setSpeed(parseFloat(e.target.value))}
              className="bg-transparent border-none outline-none text-white font-semibold cursor-pointer"
            >
              <option value={0.5} className="bg-brand-card text-white">0.5x</option>
              <option value={1} className="bg-brand-card text-white">1.0x</option>
              <option value={2} className="bg-brand-card text-white">2.0x</option>
              <option value={4} className="bg-brand-card text-white">4.0x</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}
