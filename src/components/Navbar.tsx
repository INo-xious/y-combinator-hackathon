import React from 'react';
import { Search, Bell, ChevronRight, CornerDownRight, ShieldCheck } from 'lucide-react';
import { Trace } from '@/data/traces';

interface NavbarProps {
  activeView: string;
  activeTrace: Trace | null;
  onOpenCommandPalette: () => void;
  redactionEnabled: boolean;
}

export default function Navbar({
  activeView,
  activeTrace,
  onOpenCommandPalette,
  redactionEnabled,
}: NavbarProps) {
  // Translate view ID to display string
  const getViewName = () => {
    switch (activeView) {
      case 'landing': return 'Product Tour';
      case 'dashboard': return 'Dashboard';
      case 'explorer': return 'Trace Explorer';
      case 'replay': return 'Replay Viewer';
      case 'compare': return 'Compare Runs';
      case 'settings': return 'Settings';
      default: return 'Dashboard';
    }
  };

  return (
    <header className="h-16 border-b border-brand-border bg-[#090F1B] px-6 flex items-center justify-between sticky top-0 z-40">
      {/* Breadcrumbs */}
      <div className="flex items-center gap-2 text-sm">
        <span className="text-brand-secondary">agent-rr</span>
        <ChevronRight className="w-3.5 h-3.5 text-brand-secondary shrink-0" />
        <span className="font-semibold text-white">{getViewName()}</span>

        {activeTrace && activeView === 'replay' && (
          <>
            <ChevronRight className="w-3.5 h-3.5 text-brand-secondary shrink-0" />
            <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-brand-primary/10 border border-brand-primary/20 text-brand-primary text-xs font-mono">
              <CornerDownRight className="w-3 h-3 text-brand-primary" />
              <span>{activeTrace.name}</span>
            </div>
          </>
        )}
      </div>

      {/* Global Interactions */}
      <div className="flex items-center gap-4">
        {/* Search Command Input Trigger */}
        <button
          onClick={onOpenCommandPalette}
          className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg border border-brand-border bg-brand-card text-brand-secondary hover:border-brand-primary/40 hover:text-white transition duration-200 text-xs w-64 text-left"
        >
          <Search className="w-3.5 h-3.5 text-brand-secondary" />
          <span className="grow">Search traces or actions...</span>
          <kbd className="text-[10px] bg-brand-bg px-1.5 py-0.5 rounded border border-brand-border font-mono text-brand-secondary">
            ⌘K
          </kbd>
        </button>

        {/* Redaction Shield Badge */}
        {redactionEnabled && (
          <div className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-brand-success/10 border border-brand-success/20 text-brand-success text-[11px] font-medium font-mono cursor-help" title="PII Redaction Active">
            <ShieldCheck className="w-3.5 h-3.5 text-brand-success" />
            <span>Redaction On</span>
          </div>
        )}

        {/* Notifications Indicator */}
        <button className="p-2 rounded-lg hover:bg-brand-card border border-transparent hover:border-brand-border text-brand-secondary hover:text-white transition relative">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-brand-primary rounded-full"></span>
        </button>

        {/* Divider */}
        <div className="w-px h-6 bg-brand-border" />

        {/* Workspace Profile Avatar */}
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-brand-hash flex items-center justify-center font-bold text-xs text-white border border-brand-border">
            YC
          </div>
          <div className="hidden md:flex flex-col">
            <span className="text-xs font-semibold text-white leading-none">YC Demo Workspace</span>
            <span className="text-[10px] text-brand-secondary mt-0.5">Developer Team</span>
          </div>
        </div>
      </div>
    </header>
  );
}
