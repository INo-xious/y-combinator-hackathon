'use client';

import React from 'react';
import { 
  Settings, Key, ShieldCheck, Database, HardDrive, 
  HelpCircle, Monitor, Info, Check, EyeOff, Sparkles, Sliders 
} from 'lucide-react';

interface SettingsViewProps {
  redactionEnabled: boolean;
  onToggleRedaction: () => void;
}

export default function SettingsView({
  redactionEnabled,
  onToggleRedaction,
}: SettingsViewProps) {
  return (
    <div className="p-6 space-y-6 max-w-4xl">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">System Settings</h2>
        <p className="text-sm text-brand-secondary">
          Configure deterministic caching protocols, hash algorithms, redaction schemas, and visual themes.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Navigation / Shortcut Links */}
        <div className="space-y-1.5 md:col-span-1">
          <button className="w-full text-left px-3 py-2 bg-brand-card text-white border border-brand-border rounded-xl text-xs font-semibold flex items-center gap-2">
            <Sliders className="w-4 h-4 text-brand-primary" />
            <span>General Replay Settings</span>
          </button>
          <button className="w-full text-left px-3 py-2 text-brand-secondary hover:text-white hover:bg-brand-card/40 rounded-xl text-xs transition flex items-center gap-2">
            <ShieldCheck className="w-4 h-4" />
            <span>PII Redaction Rules</span>
          </button>
          <button className="w-full text-left px-3 py-2 text-brand-secondary hover:text-white hover:bg-brand-card/40 rounded-xl text-xs transition flex items-center gap-2">
            <Database className="w-4 h-4" />
            <span>Storage & Sync</span>
          </button>
          <button className="w-full text-left px-3 py-2 text-brand-secondary hover:text-white hover:bg-brand-card/40 rounded-xl text-xs transition flex items-center gap-2">
            <Monitor className="w-4 h-4" />
            <span>Developer Shortcuts</span>
          </button>
        </div>

        {/* Configurations Fields Area */}
        <div className="md:col-span-2 space-y-6">
          {/* Caching & Hashes */}
          <div className="bg-brand-card border border-brand-border p-4 rounded-xl space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Key className="w-4 h-4 text-brand-primary" />
              <span>DAG Verification & Hashes</span>
            </h3>
            
            <div className="space-y-3 text-xs">
              <div className="flex flex-col gap-1.5">
                <label className="text-brand-secondary font-medium">DAG Hashing Algorithm</label>
                <select className="bg-brand-bg border border-brand-border rounded-lg text-white px-3 py-2 outline-none focus:border-brand-primary cursor-pointer font-mono">
                  <option value="sha256">SHA-256 (Recommended, high collision resistance)</option>
                  <option value="sha512">SHA-512 (Extended payload encryption)</option>
                  <option value="md5">MD5 (Legacy, fast execution testing only)</option>
                </select>
              </div>

              <div className="flex items-center justify-between py-2">
                <div>
                  <span className="text-white font-medium block">Enforce Deterministic Signatures</span>
                  <span className="text-[10px] text-brand-secondary">Fail execution instantly if input code hash changes.</span>
                </div>
                <input 
                  type="checkbox" 
                  defaultChecked 
                  className="w-4 h-4 text-brand-primary bg-brand-bg rounded border-brand-border focus:ring-brand-primary"
                />
              </div>
            </div>
          </div>

          {/* Privacy Rules */}
          <div className="bg-brand-card border border-brand-border p-4 rounded-xl space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-brand-success" />
              <span>PII Ingest Redaction</span>
            </h3>
            
            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-white font-medium block">Automatic Payload Redaction</span>
                  <span className="text-[10px] text-brand-secondary">Scans prompts and responses for keys, cards, and phone numbers.</span>
                </div>
                <input 
                  type="checkbox" 
                  checked={redactionEnabled} 
                  onChange={onToggleRedaction}
                  className="w-4 h-4 text-brand-primary bg-brand-bg rounded border-brand-border focus:ring-brand-primary cursor-pointer"
                />
              </div>

              <div className="pl-4 border-l border-brand-border/60 ml-1 space-y-2 mt-2">
                <div className="flex items-center gap-2.5">
                  <input type="checkbox" defaultChecked disabled className="w-3.5 h-3.5 opacity-60" />
                  <span className="text-brand-secondary">API Keys and Secrets (`sk-...`, `Bearer ...`)</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <input type="checkbox" defaultChecked disabled className="w-3.5 h-3.5 opacity-60" />
                  <span className="text-brand-secondary">Emails and Phone Numbers</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <input type="checkbox" defaultChecked disabled className="w-3.5 h-3.5 opacity-60" />
                  <span className="text-brand-secondary">Stripe / Credit Card Account Tokens</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <input type="checkbox" defaultChecked disabled className="w-3.5 h-3.5 opacity-60" />
                  <span className="text-brand-secondary">Physical street addresses & zip codes</span>
                </div>
              </div>
            </div>
          </div>

          {/* Storage Caps */}
          <div className="bg-brand-card border border-brand-border p-4 rounded-xl space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <HardDrive className="w-4 h-4 text-brand-recording" />
              <span>Local Trace Storage</span>
            </h3>
            
            <div className="space-y-2 text-xs">
              <div className="flex justify-between items-center text-xs text-brand-secondary">
                <span>Quota Usage: <b>42 KB</b> used / <b>500 MB</b> limit</span>
                <span className="font-mono text-white">0.01% used</span>
              </div>
              <div className="w-full bg-brand-border h-2 rounded-full overflow-hidden">
                <div className="bg-brand-primary w-[0.01%] h-full" />
              </div>
              <div className="flex items-center gap-2 pt-2">
                <button className="px-3 py-1.5 bg-brand-bg hover:bg-brand-border border border-brand-border text-brand-secondary hover:text-white rounded-lg text-[10px] font-semibold transition">
                  Flush Local Cache
                </button>
                <button className="px-3 py-1.5 bg-brand-bg hover:bg-brand-border border border-brand-border text-brand-secondary hover:text-white rounded-lg text-[10px] font-semibold transition">
                  Export Database JSON
                </button>
              </div>
            </div>
          </div>

          {/* Keyboard Shortcuts */}
          <div className="bg-brand-card border border-brand-border p-4 rounded-xl space-y-3">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Monitor className="w-4 h-4 text-brand-hash" />
              <span>Keyboard Shortcuts</span>
            </h3>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="flex justify-between border-b border-brand-border py-1">
                <span className="text-brand-secondary">Global Search / Commands</span>
                <kbd className="bg-brand-bg border border-brand-border px-1.5 py-0.5 rounded text-[10px] font-mono text-white">⌘K</kbd>
              </div>
              <div className="flex justify-between border-b border-brand-border py-1">
                <span className="text-brand-secondary">Toggle Replay Playback</span>
                <kbd className="bg-brand-bg border border-brand-border px-1.5 py-0.5 rounded text-[10px] font-mono text-white">Space</kbd>
              </div>
              <div className="flex justify-between border-b border-brand-border py-1">
                <span className="text-brand-secondary">Next Node Step</span>
                <kbd className="bg-brand-bg border border-brand-border px-1.5 py-0.5 rounded text-[10px] font-mono text-white">→</kbd>
              </div>
              <div className="flex justify-between border-b border-brand-border py-1">
                <span className="text-brand-secondary">Prev Node Step</span>
                <kbd className="bg-brand-bg border border-brand-border px-1.5 py-0.5 rounded text-[10px] font-mono text-white">←</kbd>
              </div>
            </div>
          </div>

          {/* About Agent-RR */}
          <div className="bg-brand-card/40 border border-brand-border/80 p-4 rounded-xl space-y-2 text-xs">
            <h4 className="font-bold text-white flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-brand-primary" />
              <span>About Agent-RR</span>
            </h4>
            <p className="text-brand-secondary leading-relaxed">
              Agent-RR is a deterministic replay engine and time-travel debugger for AI agents built for the Y Combinator Summer Hackathon 2026. Designed to capture model invocations, tool logs, and state changes into cryptographic DAG architectures. Saves API charges by replaying runs locally.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
