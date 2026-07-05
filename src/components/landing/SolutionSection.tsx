'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, Zap, ArrowRight } from 'lucide-react';
import SectionHeader from '@/components/shared/SectionHeader';

/**
 * SolutionSection — Visual storytelling of how Agent-RR solves
 * the debugging problem with a 3-phase animated flow.
 */

const phases = [
  {
    step: '01',
    title: 'Record',
    description: 'Instrument your agent with minimal decorators. Every LLM call, database query, and tool invocation is captured into a cryptographic trace.',
    color: 'from-blue-500 to-blue-600',
    borderColor: 'border-blue-500/30',
    dotColor: 'bg-blue-500',
    iconBg: 'bg-blue-500/10',
  },
  {
    step: '02',
    title: 'Replay',
    description: 'Re-execute the entire agent pipeline offline using cached responses. Zero API calls, zero cost, instant results. Every run is identical.',
    color: 'from-purple-500 to-purple-600',
    borderColor: 'border-purple-500/30',
    dotColor: 'bg-purple-500',
    iconBg: 'bg-purple-500/10',
  },
  {
    step: '03',
    title: 'Debug',
    description: 'Step forward and backward through execution. Compare runs side-by-side. Pinpoint the exact node where LLM decisions diverged.',
    color: 'from-emerald-500 to-emerald-600',
    borderColor: 'border-emerald-500/30',
    dotColor: 'bg-emerald-500',
    iconBg: 'bg-emerald-500/10',
  },
];

export default function SolutionSection() {
  return (
    <section className="relative py-32 overflow-hidden">
      {/* Background gradient */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />
      <div className="absolute top-1/2 left-1/4 w-[500px] h-[500px] rounded-full bg-blue-500/[0.02] blur-[120px] pointer-events-none" />
      
      <div className="max-w-6xl mx-auto px-6">
        <SectionHeader
          badge="The solution"
          badgeIcon={<CheckCircle2 className="w-3.5 h-3.5" />}
          badgeColor="green"
          title="Time-travel debugging for the AI era"
          subtitle="Agent-RR captures every execution step as a verifiable DAG, enabling deterministic replay and surgical debugging."
        />

        {/* Three-phase flow with connecting line */}
        <div className="relative">
          {/* Connecting line */}
          <div className="hidden md:block absolute top-1/2 left-0 right-0 h-px bg-gradient-to-r from-blue-500/20 via-purple-500/20 to-emerald-500/20 -translate-y-1/2" />
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
            {phases.map((phase, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 40 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-50px' }}
                transition={{
                  duration: 0.7,
                  delay: index * 0.2,
                  ease: [0.21, 0.45, 0.27, 0.9],
                }}
                className="relative"
              >
                {/* Step number dot */}
                <div className="hidden md:flex absolute -top-4 left-1/2 -translate-x-1/2 z-10">
                  <div className={`w-8 h-8 rounded-full ${phase.dotColor} flex items-center justify-center text-white text-xs font-bold shadow-lg`}>
                    {phase.step}
                  </div>
                </div>

                <div className={`rounded-2xl border ${phase.borderColor} bg-white/[0.02] p-8 pt-10 md:pt-12 h-full backdrop-blur-sm group hover:bg-white/[0.04] transition-all duration-500`}>
                  {/* Step label (mobile) */}
                  <div className={`md:hidden inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gradient-to-r ${phase.color} text-white text-xs font-bold mb-4`}>
                    Step {phase.step}
                  </div>

                  <h3 className="text-2xl font-bold text-white mb-3 font-[family-name:var(--font-display)]">
                    {phase.title}
                  </h3>
                  
                  <p className="text-sm text-white/40 leading-relaxed mb-6">
                    {phase.description}
                  </p>

                  {/* Animated check items */}
                  <div className="space-y-2.5">
                    {index === 0 && (
                      <>
                        <FeatureCheck text="Automatic LLM call interception" />
                        <FeatureCheck text="SHA-256 hash per node" />
                        <FeatureCheck text="PII auto-redaction" />
                      </>
                    )}
                    {index === 1 && (
                      <>
                        <FeatureCheck text="Zero external API calls" />
                        <FeatureCheck text="Instant cached responses" />
                        <FeatureCheck text="100% cost elimination" />
                      </>
                    )}
                    {index === 2 && (
                      <>
                        <FeatureCheck text="Step-by-step execution scrubbing" />
                        <FeatureCheck text="Side-by-side run comparison" />
                        <FeatureCheck text="Divergence auto-detection" />
                      </>
                    )}
                  </div>
                </div>

                {/* Arrow connector (between cards) */}
                {index < phases.length - 1 && (
                  <div className="hidden md:flex absolute top-1/2 -right-4 -translate-y-1/2 z-20">
                    <ArrowRight className="w-4 h-4 text-white/20" />
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function FeatureCheck({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-2.5 text-xs text-white/50">
      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
      <span>{text}</span>
    </div>
  );
}
