import React, { useEffect, useState, useRef } from 'react';
import { Search, Play, FileText, Settings, ShieldAlert, ArrowRight, X } from 'lucide-react';
import { motion } from 'framer-motion';
import { Trace } from '@/data/traces';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (view: string) => void;
  onSelectTrace: (traceId: string) => void;
  onTriggerReplay: () => void;
  traces: Trace[];
}

export default function CommandPalette({
  isOpen,
  onClose,
  onNavigate,
  onSelectTrace,
  onTriggerReplay,
  traces,
}: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
        else onClose(); // wait, toggle
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const filteredTraces = traces.filter(t =>
    t.name.toLowerCase().includes(query.toLowerCase()) ||
    t.description.toLowerCase().includes(query.toLowerCase())
  );

  const actions = [
    { name: 'Run Active Replay', icon: Play, shortcut: '▶', action: () => { onTriggerReplay(); onClose(); } },
    { name: 'Go to Dashboard', icon: FileText, action: () => { onNavigate('dashboard'); onClose(); } },
    { name: 'Go to Trace Explorer', icon: Search, action: () => { onNavigate('explorer'); onClose(); } },
    { name: 'Go to Compare Runs', icon: ShieldAlert, action: () => { onNavigate('compare'); onClose(); } },
    { name: 'Go to Settings', icon: Settings, action: () => { onNavigate('settings'); onClose(); } },
  ].filter(a => a.name.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] px-4">
      {/* Backdrop */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15 }}
        className="fixed inset-0 bg-[#070B13]/85 backdrop-blur-md" 
        onClick={onClose}
      />

      {/* Palette Body */}
      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: -10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: -10 }}
        transition={{ type: 'spring', duration: 0.25 }}
        className="relative w-full max-w-lg overflow-hidden border border-brand-border bg-brand-card rounded-xl shadow-2xl z-10"
      >
        {/* Search Input */}
        <div className="flex items-center border-b border-brand-border px-4 py-3">
          <Search className="w-5 h-5 text-brand-secondary mr-3 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Type a command or search traces..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-transparent text-sm text-brand-text placeholder-brand-secondary outline-none border-none"
          />
          <button 
            onClick={onClose}
            className="p-1 text-brand-secondary hover:text-brand-text rounded-md hover:bg-brand-border"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="max-h-[350px] overflow-y-auto p-2 space-y-4">
          {/* Action Commands */}
          {actions.length > 0 && (
            <div>
              <h4 className="px-3 py-1 text-xs font-semibold text-brand-secondary uppercase tracking-wider">
                System Commands
              </h4>
              <div className="mt-1 space-y-0.5">
                {actions.map((act, idx) => (
                  <button
                    key={idx}
                    onClick={act.action}
                    className="flex items-center justify-between w-full text-left px-3 py-2 text-sm text-brand-text hover:bg-brand-border rounded-lg transition"
                  >
                    <div className="flex items-center gap-3">
                      <act.icon className="w-4 h-4 text-brand-primary" />
                      <span>{act.name}</span>
                    </div>
                    {act.shortcut && (
                      <kbd className="text-[10px] bg-brand-bg px-1.5 py-0.5 rounded border border-brand-border font-mono text-brand-secondary">
                        {act.shortcut}
                      </kbd>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Traces */}
          {filteredTraces.length > 0 && (
            <div>
              <h4 className="px-3 py-1 text-xs font-semibold text-brand-secondary uppercase tracking-wider">
                Select Executions
              </h4>
              <div className="mt-1 space-y-0.5">
                {filteredTraces.map((trace) => (
                  <button
                    key={trace.id}
                    onClick={() => {
                      onSelectTrace(trace.id);
                      onNavigate('replay');
                      onClose();
                    }}
                    className="flex items-center justify-between w-full text-left px-3 py-2 text-sm text-brand-text hover:bg-brand-border rounded-lg transition"
                  >
                    <div className="flex flex-col">
                      <span className="font-medium">{trace.name}</span>
                      <span className="text-xs text-brand-secondary line-clamp-1">{trace.description}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono uppercase font-bold ${
                        trace.replayStatus === 'success' 
                          ? 'bg-brand-success/10 text-brand-success'
                          : 'bg-brand-divergence/10 text-brand-divergence'
                      }`}>
                        {trace.replayStatus}
                      </span>
                      <ArrowRight className="w-3.5 h-3.5 text-brand-secondary" />
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {actions.length === 0 && filteredTraces.length === 0 && (
            <div className="py-6 text-center text-sm text-brand-secondary">
              No commands or traces found for "{query}"
            </div>
          )}
        </div>

        {/* Footer info */}
        <div className="flex items-center justify-between border-t border-brand-border bg-brand-bg/50 px-4 py-2 text-[10px] text-brand-secondary">
          <span>Search or select trace to inspect</span>
          <div className="flex gap-2">
            <span><kbd className="bg-brand-card px-1 rounded border border-brand-border font-mono">⏎</kbd> select</span>
            <span><kbd className="bg-brand-card px-1 rounded border border-brand-border font-mono">esc</kbd> close</span>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
