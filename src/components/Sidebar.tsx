import React from 'react';
import { LayoutDashboard, Compass, Play, Split, Settings, Radio, Info } from 'lucide-react';
import { motion } from 'framer-motion';

interface SidebarProps {
  activeView: string;
  onNavigate: (view: string) => void;
  isRecording?: boolean;
}

export default function Sidebar({ activeView, onNavigate, isRecording = false }: SidebarProps) {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'explorer', label: 'Trace Explorer', icon: Compass },
    { id: 'replay', label: 'Replay Viewer', icon: Play },
    { id: 'compare', label: 'Compare Runs', icon: Split },
    { id: 'settings', label: 'Settings', icon: Settings },
    { id: 'landing', label: 'Product Tour & About', icon: Info },
  ];

  return (
    <aside className="w-64 shrink-0 border-r border-brand-border bg-[#090F1B] flex flex-col justify-between h-screen sticky top-0">
      <div>
        {/* App Title Logo Section */}
        <div className="h-16 flex items-center px-6 border-b border-brand-border gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-brand-primary flex items-center justify-center shadow-lg shadow-brand-primary/20">
            <span className="text-white font-extrabold text-sm tracking-tighter">AR</span>
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight text-white flex items-center gap-1.5">
              Agent-RR
            </h1>
            <p className="text-[10px] text-brand-secondary font-mono tracking-wider">v0.1.0-beta</p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-4 space-y-1.5">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition duration-200 group relative ${
                  isActive
                    ? 'text-white'
                    : 'text-brand-secondary hover:text-white'
                }`}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute inset-0 bg-brand-card border border-brand-border rounded-xl"
                    transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                  />
                )}
                <span className="relative z-10 flex items-center gap-3 w-full">
                  <Icon className={`w-4 h-4 transition duration-200 shrink-0 ${
                    isActive ? 'text-brand-primary' : 'text-brand-secondary group-hover:text-white'
                  }`} />
                  <span>{item.label}</span>
                </span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Recording Indicator & Footer */}
      <div className="p-4 border-t border-brand-border">
        {isRecording ? (
          <div className="flex items-center gap-3 p-3 bg-brand-recording/10 border border-brand-recording/20 rounded-xl">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-recording opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-brand-recording"></span>
            </span>
            <div className="flex flex-col">
              <span className="text-xs font-semibold text-brand-recording uppercase tracking-wider">Recording Live</span>
              <span className="text-[10px] text-brand-secondary">Capturing LLM & tool calls</span>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 px-2.5 py-2.5 rounded-xl bg-brand-card border border-brand-border text-xs text-brand-secondary">
            <Radio className="w-3.5 h-3.5 text-brand-success" />
            <span>Replay engine ready</span>
          </div>
        )}
      </div>
    </aside>
  );
}
