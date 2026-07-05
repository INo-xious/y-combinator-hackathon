'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Terminal, Layers, Play, ArrowRight, Code2 } from 'lucide-react';
import SectionHeader from '@/components/shared/SectionHeader';

/**
 * ArchitectureSection — Shows the 3-step developer workflow
 * with animated sequential reveal and code snippets.
 * Preserves existing "How It Works" content.
 */

const steps = [
  {
    number: '01',
    icon: <Terminal className="w-5 h-5" />,
    title: 'Instrument your Agent',
    description: 'Add simple decorators to your LLM call loops and external tool integrations. Specify which fields are inputs, outputs, or state dependencies to build the dependency tree.',
    code: `from agent_rr import record_run

@record_run(name="classification")
def intent_classifier(query):
    # Wrapped prompt loop
    return model.call(query)`,
    color: 'blue',
    gradient: 'from-blue-500 to-blue-600',
    borderColor: 'border-blue-500/20',
  },
  {
    number: '02',
    icon: <Layers className="w-5 h-5" />,
    title: 'Record Traces to DAGs',
    description: 'As your agent runs in production or testing, Agent-RR monitors the execution graph, generating cryptographic SHA-256 validation IDs for every node. Redacts sensitive credentials locally.',
    code: `# Traces compiled as JSON DAGs
{
  "traceId": "customer-support",
  "hash": "8B5CF622C55E3B82F6",
  "nodesCount": 7,
  "nodes": [...]
}`,
    color: 'purple',
    gradient: 'from-purple-500 to-purple-600',
    borderColor: 'border-purple-500/20',
  },
  {
    number: '03',
    icon: <Play className="w-5 h-5 fill-current" />,
    title: 'Time-Travel & Debug',
    description: 'Import JSON traces into the console. Step forward and backward through tool queries, compare test runs side-by-side, analyze prompt changes, and resolve bugs locally with zero external API calls.',
    code: null,
    color: 'emerald',
    gradient: 'from-emerald-500 to-emerald-600',
    borderColor: 'border-emerald-500/20',
  },
];

interface ArchitectureSectionProps {
  onNavigate: (view: string) => void;
}

export default function ArchitectureSection({ onNavigate }: ArchitectureSectionProps) {
  return (
    <section className="relative py-32 overflow-hidden">
      {/* Top divider */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />
      
      {/* Ambient glow */}
      <div className="absolute top-1/2 right-0 w-[500px] h-[500px] rounded-full bg-purple-500/[0.02] blur-[150px] pointer-events-none" />

      <div className="max-w-6xl mx-auto px-6">
        <SectionHeader
          badge="How it works"
          badgeIcon={<Code2 className="w-3.5 h-3.5" />}
          badgeColor="purple"
          title="Three steps to deterministic debugging"
          subtitle="A developer-first workflow to record agent executions and replay them cleanly under controlled conditions."
        />

        <div className="space-y-6">
          {steps.map((step, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: '-50px' }}
              transition={{
                duration: 0.7,
                delay: index * 0.15,
                ease: [0.21, 0.45, 0.27, 0.9],
              }}
              className={`relative rounded-2xl border ${step.borderColor} bg-white/[0.02] backdrop-blur-sm overflow-hidden group hover:bg-white/[0.03] transition-all duration-500`}
            >
              <div className="flex flex-col lg:flex-row">
                {/* Left content */}
                <div className="flex-1 p-8 lg:p-10">
                  <div className="flex items-center gap-4 mb-5">
                    {/* Step number */}
                    <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${step.gradient} flex items-center justify-center text-white shadow-lg`}>
                      {step.icon}
                    </div>
                    
                    <div>
                      <span className="text-xs font-mono text-white/30 uppercase tracking-widest">Step {step.number}</span>
                      <h3 className="text-xl font-semibold text-white font-[family-name:var(--font-display)]">
                        {step.title}
                      </h3>
                    </div>
                  </div>

                  <p className="text-sm text-white/40 leading-relaxed max-w-lg">
                    {step.description}
                  </p>

                  {/* CTA for last step */}
                  {index === steps.length - 1 && (
                    <button
                      onClick={() => onNavigate('dashboard')}
                      className="mt-6 inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 text-white text-sm font-semibold hover:opacity-90 transition cursor-pointer shadow-lg shadow-emerald-500/20"
                    >
                      <span>Launch Replayer</span>
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  )}
                </div>

                {/* Right code block */}
                {step.code && (
                  <div className="lg:w-[400px] border-t lg:border-t-0 lg:border-l border-white/[0.04] bg-black/20">
                    <div className="px-4 py-2.5 border-b border-white/[0.04] flex items-center gap-2">
                      <div className="flex gap-1.5">
                        <div className="w-2.5 h-2.5 rounded-full bg-white/[0.06]" />
                        <div className="w-2.5 h-2.5 rounded-full bg-white/[0.06]" />
                        <div className="w-2.5 h-2.5 rounded-full bg-white/[0.06]" />
                      </div>
                      <span className="text-[10px] font-mono text-white/20 ml-2">
                        {index === 0 ? 'agent.py' : 'trace.json'}
                      </span>
                    </div>
                    <pre className="p-5 text-[11px] font-mono text-white/50 leading-relaxed overflow-x-auto">
                      {step.code}
                    </pre>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
