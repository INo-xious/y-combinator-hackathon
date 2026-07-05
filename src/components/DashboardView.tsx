'use client';

import React, { useState } from 'react';
import { 
  DollarSign, RefreshCw, Cpu, Zap, ArrowUpRight, 
  Search, ShieldAlert, CheckCircle2, Play, ChevronRight, FileText, Database, ShieldCheck, Download
} from 'lucide-react';
import { Trace } from '@/data/traces';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, 
  Tooltip, ResponsiveContainer, BarChart, Bar, Cell 
} from 'recharts';

interface DashboardViewProps {
  onNavigate: (view: string) => void;
  onSelectTrace: (traceId: string) => void;
  redactionEnabled: boolean;
  onToggleRedaction: () => void;
  traces: Trace[];
}

// Chart Data Mock
const savingsData = [
  { day: 'Mon', original: 8.50, cached: 0.80, saved: 7.70 },
  { day: 'Tue', original: 12.10, cached: 1.10, saved: 11.00 },
  { day: 'Wed', original: 19.80, cached: 1.50, saved: 18.30 },
  { day: 'Thu', original: 15.40, cached: 1.20, saved: 14.20 },
  { day: 'Fri', original: 24.30, cached: 2.10, saved: 22.20 },
  { day: 'Sat', original: 11.20, cached: 0.90, saved: 10.30 },
  { day: 'Sun', original: 28.50, cached: 2.40, saved: 26.10 },
];

const callsData = [
  { name: 'Customer Support', count: 14, saved: 42 },
  { name: 'Travel Planner', count: 8, saved: 32 },
  { name: 'Research Agent', count: 22, saved: 110 },
  { name: 'Coding Assistant', count: 5, saved: 15 },
  { name: 'Sales Agent', count: 19, saved: 57 },
];

export default function DashboardView({
  onNavigate,
  onSelectTrace,
  redactionEnabled,
  onToggleRedaction,
  traces,
}: DashboardViewProps) {
  const [searchQuery, setSearchQuery] = useState('');

  // Calculate totals
  const totalTraces = traces.length;
  const successTraces = traces.filter(t => t.replayStatus === 'success').length;
  const successRate = totalTraces > 0 ? ((successTraces / totalTraces) * 100).toFixed(0) : '0';
  
  // Accumulated metric highlights
  const totalMoneySaved = "$110.15";
  const apiCallsAvoided = 256;
  const avgReplaySpeedup = "98.2%";

  const filteredTraces = traces.filter(t => 
    t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-6 space-y-6">
      {/* Top Welcome Title */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Deterministic Replay for AI Agents</h2>
          <p className="text-sm text-brand-secondary">Record once. Replay forever. Secure cryptographic DAG tracking.</p>
        </div>
        <div className="flex gap-3">
          <button 
            onClick={() => onNavigate('explorer')} 
            className="flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-xl border border-brand-border bg-brand-card hover:border-brand-primary transition text-brand-text"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Import Trace</span>
          </button>
          <button 
            onClick={() => {
              onSelectTrace('customer-support');
              onNavigate('replay');
            }} 
            className="flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-xl bg-brand-primary hover:bg-brand-primary/80 transition text-white shadow-lg shadow-brand-primary/20"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>New Recording</span>
          </button>
        </div>
      </div>

      {/* KPI Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Money Saved */}
        <div className="bg-brand-card border border-brand-border p-4 rounded-xl relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-brand-secondary uppercase tracking-wider">Money Saved</span>
            <div className="w-8 h-8 rounded-lg bg-brand-success/15 flex items-center justify-center">
              <DollarSign className="w-4 h-4 text-brand-success" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-extrabold text-white">{totalMoneySaved}</span>
            <span className="text-[10px] text-brand-success ml-2 font-mono font-semibold">+ $18.40 today</span>
          </div>
          <p className="text-[10px] text-brand-secondary mt-1">LLM token costs avoided by local cache</p>
        </div>

        {/* Replay Success Rate */}
        <div className="bg-brand-card border border-brand-border p-4 rounded-xl relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-brand-secondary uppercase tracking-wider">Replay Success Rate</span>
            <div className="w-8 h-8 rounded-lg bg-brand-primary/15 flex items-center justify-center">
              <RefreshCw className="w-4 h-4 text-brand-primary animate-spin-slow" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-extrabold text-white">{successRate}%</span>
            <span className="text-[10px] text-brand-secondary ml-2 font-mono">({successTraces}/{totalTraces} runs)</span>
          </div>
          <p className="text-[10px] text-brand-secondary mt-1">No divergences detected in past replays</p>
        </div>

        {/* API Calls Avoided */}
        <div className="bg-brand-card border border-brand-border p-4 rounded-xl relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-brand-secondary uppercase tracking-wider">API Calls Avoided</span>
            <div className="w-8 h-8 rounded-lg bg-brand-recording/15 flex items-center justify-center">
              <Cpu className="w-4 h-4 text-brand-recording" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-extrabold text-white">{apiCallsAvoided}</span>
            <span className="text-[10px] text-brand-success ml-2 font-mono font-semibold">100% hits</span>
          </div>
          <p className="text-[10px] text-brand-secondary mt-1">Repeat requests skipped and cached</p>
        </div>

        {/* Avg Replay Latency */}
        <div className="bg-brand-card border border-brand-border p-4 rounded-xl relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-brand-secondary uppercase tracking-wider">Avg Latency Savings</span>
            <div className="w-8 h-8 rounded-lg bg-brand-hash/15 flex items-center justify-center">
              <Zap className="w-4 h-4 text-brand-hash animate-pulse" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-extrabold text-white">{avgReplaySpeedup}</span>
            <span className="text-[10px] text-brand-secondary ml-2 font-mono">0.12s avg replay</span>
          </div>
          <p className="text-[10px] text-brand-secondary mt-1">Dramatically faster than live LLM call cycles</p>
        </div>
      </div>

      {/* Recharts Graphical Visuals */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Money Saved Over Time Chart */}
        <div className="md:col-span-2 bg-brand-card border border-brand-border p-4 rounded-xl flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">Money Saved Over Time</h3>
              <p className="text-xs text-brand-secondary">Comparing total token costs vs cached replay savings</p>
            </div>
            <div className="flex gap-4 text-[10px] font-mono">
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-brand-primary" />
                <span className="text-white">API Saved ($)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-[#1F2937]" />
                <span className="text-brand-secondary">API Cost ($)</span>
              </div>
            </div>
          </div>

          <div className="h-60 w-full font-mono text-[10px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={savingsData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorSaved" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" vertical={false} />
                <XAxis dataKey="day" stroke="#4B5563" />
                <YAxis stroke="#4B5563" />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#1F2937', color: '#FFFFFF' }}
                  labelStyle={{ color: '#94A3B8' }}
                />
                <Area type="monotone" dataKey="saved" stroke="#3B82F6" strokeWidth={2} fillOpacity={1} fill="url(#colorSaved)" />
                <Area type="monotone" dataKey="cached" stroke="#1F2937" strokeWidth={1} fill="none" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* API Avoided chart */}
        <div className="bg-brand-card border border-brand-border p-4 rounded-xl flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white">API Calls Avoided per Agent</h3>
            <p className="text-xs text-brand-secondary">Mock data summary of hits cached</p>
          </div>

          <div className="h-60 w-full mt-4 font-mono text-[9px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={callsData} layout="vertical" margin={{ top: 5, right: 5, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" horizontal={false} />
                <XAxis type="number" stroke="#4B5563" />
                <YAxis dataKey="name" type="category" stroke="#4B5563" width={65} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#1F2937', color: '#FFFFFF' }}
                  labelStyle={{ color: '#94A3B8' }}
                />
                <Bar dataKey="saved" fill="#3B82F6" radius={[0, 4, 4, 0]}>
                  {callsData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={index === 2 ? '#EF4444' : '#3B82F6'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Privacy Guard Summary Row */}
      <div className="bg-brand-card border border-brand-border rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-success/15 flex items-center justify-center shrink-0">
            <ShieldCheck className="w-5 h-5 text-brand-success" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white">Automated Privacy Guard</h4>
            <p className="text-xs text-brand-secondary">
              Redacted: <b>API Keys</b>, <b>Emails</b>, <b>PII data</b>, and <b>Phone Numbers</b> before storage. Toggled to active.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <input 
              type="checkbox" 
              id="redact-check" 
              checked={redactionEnabled} 
              onChange={onToggleRedaction}
              className="w-4 h-4 text-brand-primary bg-brand-bg rounded border-brand-border focus:ring-brand-primary"
            />
            <label htmlFor="redact-check" className="text-xs font-semibold text-white cursor-pointer select-none">
              Auto-redact active traces
            </label>
          </div>
          <button 
            onClick={() => onNavigate('settings')} 
            className="text-xs font-semibold text-brand-primary hover:underline"
          >
            Configure Rules
          </button>
        </div>
      </div>

      {/* Recent Traces Table */}
      <div className="bg-brand-card border border-brand-border rounded-xl">
        <div className="p-4 border-b border-brand-border flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
          <div>
            <h3 className="text-sm font-semibold text-white">Recent Agent Executions</h3>
            <p className="text-xs text-brand-secondary">Select an execution from the list to trigger deterministic replay</p>
          </div>
          
          {/* Table Search Input */}
          <div className="relative w-full md:w-64">
            <Search className="w-4 h-4 text-brand-secondary absolute left-3 top-2.5" />
            <input 
              type="text" 
              placeholder="Search traces..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full text-xs bg-brand-bg text-brand-text pl-9 pr-4 py-2 rounded-lg border border-brand-border focus:outline-none focus:border-brand-primary"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-brand-border text-brand-secondary font-semibold font-mono bg-[#090F1B]/50">
                <th className="p-4">Trace Name</th>
                <th className="p-4">Live Runtime</th>
                <th className="p-4">Replay Time</th>
                <th className="p-4 text-center">Nodes</th>
                <th className="p-4">DAG Hash Verification</th>
                <th className="p-4 text-center">Replay Status</th>
                <th className="p-4">Last Modified</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-border">
              {filteredTraces.map((trace) => (
                <tr 
                  key={trace.id} 
                  className="hover:bg-brand-border/40 transition group cursor-pointer"
                  onClick={() => {
                    onSelectTrace(trace.id);
                    onNavigate('replay');
                  }}
                >
                  <td className="p-4">
                    <div className="flex flex-col">
                      <span className="font-semibold text-white group-hover:text-brand-primary transition">{trace.name}</span>
                      <span className="text-[11px] text-brand-secondary line-clamp-1">{trace.description}</span>
                    </div>
                  </td>
                  <td className="p-4 font-mono text-white">{trace.runtime}</td>
                  <td className="p-4 font-mono text-brand-success font-semibold">{trace.replayTime}</td>
                  <td className="p-4 text-center font-mono text-white">{trace.nodesCount}</td>
                  <td className="p-4">
                    <span className="font-mono text-brand-hash bg-brand-hash/10 border border-brand-hash/20 px-2 py-0.5 rounded text-[10px]">
                      SHA-256:{trace.hash.substring(0, 8)}...
                    </span>
                  </td>
                  <td className="p-4 text-center">
                    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider font-mono ${
                      trace.replayStatus === 'success'
                        ? 'bg-brand-success/15 text-brand-success border border-brand-success/20'
                        : 'bg-brand-divergence/15 text-brand-divergence border border-brand-divergence/20'
                    }`}>
                      {trace.replayStatus === 'success' ? (
                        <>
                          <CheckCircle2 className="w-3 h-3 text-brand-success" />
                          <span>Identical</span>
                        </>
                      ) : (
                        <>
                          <ShieldAlert className="w-3 h-3 text-brand-divergence" />
                          <span>Diverged</span>
                        </>
                      )}
                    </span>
                  </td>
                  <td className="p-4 text-brand-secondary font-mono">{trace.lastModified}</td>
                  <td className="p-4 text-right">
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectTrace(trace.id);
                        onNavigate('replay');
                      }}
                      className="px-2.5 py-1 bg-brand-primary/10 border border-brand-primary/20 text-brand-primary rounded hover:bg-brand-primary hover:text-white transition font-semibold"
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
              {filteredTraces.length === 0 && (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-brand-secondary">
                    No active runs found. Clear query or upload a JSON log.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
