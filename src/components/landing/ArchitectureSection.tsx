'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Terminal, Layers, Play, ArrowRight, Code2 } from 'lucide-react';
import SectionHeader from '@/components/shared/SectionHeader';

const steps = [
  {
    number: '01',
    icon: <Terminal className="w-5 h-5" />,
    title: 'Instrument your Agent',
    description: 'Add simple decorators to your LLM call loops and external tool integrations. Specify which fields are inputs, outputs, or state dependencies to build the dependency tree.',
    code: `from m2_replayer import record_run

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
    description: 'As your agent runs in production or testing, M² monitors the execution graph, generating cryptographic SHA-256 validation IDs for every node. Redacts sensitive credentials locally.',
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
    <section className="relative py-36 overflow-hidden">
      {/* Top divider */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/[0.04] to-transparent" />
      
      {/* Ambient glow */}
      <div className="absolute top-1/2 right-0 w-[500px] h-[500px] rounded-full bg-purple-500/[0.01] blur-[150px] pointer-events-none" />

      <div className="max-w-6xl mx-auto px-6 relative z-10">
        <SectionHeader
          badge="How it works"
          badgeIcon={<Code2 className="w-3.5 h-3.5" />}
          badgeColor="purple"
          title="Three steps to deterministic debugging"
          subtitle="A developer-first workflow to record agent executions and replay them cleanly under controlled conditions."
        />

        <div className="space-y-8 mt-12">
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
              className={`relative rounded-3xl border ${step.borderColor} bg-white/[0.015] backdrop-blur-md overflow-hidden group hover:bg-white/[0.03] transition-all duration-500 shadow-xl`}
            >
              <div className="flex flex-col lg:flex-row">
                {/* Left content */}
                <div className="flex-1 p-8 lg:p-12 text-left">
                  <div className="flex items-center gap-4 mb-6">
                    {/* Step number */}
                    <div className={`w-10 h-10 rounded-2xl bg-gradient-to-br ${step.gradient} flex items-center justify-center text-white shadow-lg`}>
                      {step.icon}
                    </div>
                    
                    <div>
                      <span className="text-[10px] font-mono text-white/30 uppercase tracking-widest font-bold">Step {step.number}</span>
                      <h3 className="text-xl font-bold text-white font-[family-name:var(--font-display)] mt-0.5">
                        {step.title}
                      </h3>
                    </div>
                  </div>

                  <p className="text-sm text-white/40 leading-relaxed max-w-lg font-sans">
                    {step.description}
                  </p>

                  {/* CTA for last step */}
                  {index === steps.length - 1 && (
                    <button
                      onClick={() => onNavigate('dashboard')}
                      className="mt-8 inline-flex items-center gap-2 px-6 py-3 rounded-2xl bg-gradient-to-r from-emerald-500 to-emerald-600 text-white text-xs font-bold hover:opacity-90 hover:shadow-emerald-500/25 shadow-lg shadow-emerald-500/10 transition cursor-pointer"
                    >
                      <span>Launch Replayer</span>
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  )}
                </div>

                {/* Right code block */}
                {step.code && (
                  <div className="lg:w-[420px] border-t lg:border-t-0 lg:border-l border-white/[0.04] bg-black/30">
                    <div className="px-5 py-3 border-b border-white/[0.04] flex items-center gap-2">
                      <div className="flex gap-1.5">
                        <div className="w-2 h-2 rounded-full bg-white/[0.06]" />
                        <div className="w-2 h-2 rounded-full bg-white/[0.06]" />
                        <div className="w-2 h-2 rounded-full bg-white/[0.06]" />
                      </div>
                      <span className="text-[10px] font-mono text-white/30 ml-2 font-bold">
                        {index === 0 ? 'agent.py' : 'trace.json'}
                      </span>
                    </div>
                    <pre className="p-6 text-[11px] font-mono text-white/45 leading-relaxed overflow-x-auto text-left">
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
