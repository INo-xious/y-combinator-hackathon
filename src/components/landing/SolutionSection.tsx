'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, ArrowRight } from 'lucide-react';
import SectionHeader from '@/components/shared/SectionHeader';
import GlassCard from '@/components/shared/GlassCard';

const phases = [
  {
    step: '01',
    title: 'Record',
    description: 'Instrument your agent with minimal decorators. Every LLM call, database query, and tool invocation is captured into a cryptographic trace.',
    color: 'text-blue-400',
    glowColor: 'rgba(59, 130, 246, 0.12)',
    gradient: 'from-blue-500/20 to-blue-600/5',
    bullets: ["Automatic LLM call interception", "SHA-256 hash per node", "PII auto-redaction"]
  },
  {
    step: '02',
    title: 'Replay',
    description: 'Re-execute the entire agent pipeline offline using cached responses. Zero API calls, zero cost, instant results. Every run is identical.',
    color: 'text-purple-400',
    glowColor: 'rgba(139, 92, 246, 0.12)',
    gradient: 'from-purple-500/20 to-purple-600/5',
    bullets: ["Zero external API calls", "Instant cached responses", "100% cost elimination"]
  },
  {
    step: '03',
    title: 'Debug',
    description: 'Step forward and backward through execution. Compare runs side-by-side. Pinpoint the exact node where LLM decisions diverged.',
    color: 'text-emerald-400',
    glowColor: 'rgba(16, 185, 129, 0.12)',
    gradient: 'from-emerald-500/20 to-emerald-600/5',
    bullets: ["Step-by-step scrubbing", "Side-by-side run comparison", "Divergence auto-detection"]
  },
];

export default function SolutionSection() {
  return (
    <section className="relative py-36 overflow-hidden">
      {/* Background divider and glows */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/[0.04] to-transparent" />
      <div className="absolute top-1/2 left-1/3 w-[600px] h-[600px] rounded-full bg-purple-500/[0.015] blur-[150px] pointer-events-none" />
      
      <div className="max-w-6xl mx-auto px-6 relative z-10">
        <SectionHeader
          badge="The solution"
          badgeIcon={<CheckCircle2 className="w-3.5 h-3.5" />}
          badgeColor="green"
          title="Time-travel debugging for the AI era"
          subtitle="M² captures every execution step as a cryptographic DAG, enabling deterministic replay and surgical debugging."
        />

        {/* Three-phase flow */}
        <div className="relative mt-16">
          {/* Subtle connecting line in background */}
          <div className="hidden md:block absolute top-[4.5rem] left-[15%] right-[15%] h-0.5 bg-gradient-to-r from-blue-500/20 via-purple-500/20 to-emerald-500/20 pointer-events-none" />
          
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
                {/* Step number dot positioned over the connecting line */}
                <div className="hidden md:flex absolute top-12 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20">
                  <div className={`w-8 h-8 rounded-full bg-[#030306] border-2 border-white/[0.08] flex items-center justify-center text-xs font-bold font-mono text-white/50 group-hover:border-white/30 transition-colors`}>
                    {phase.step}
                  </div>
                </div>

                <GlassCard glowColor={phase.glowColor} className="h-full">
                  <div className="p-8 pt-16 flex flex-col justify-between h-full group">
                    <div>
                      {/* Step label (mobile only) */}
                      <div className={`md:hidden inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-white/60 text-[10px] font-mono mb-4`}>
                        Step {phase.step}
                      </div>

                      <h3 className="text-2xl font-bold text-white mb-4 font-[family-name:var(--font-display)]">
                        {phase.title}
                      </h3>
                      
                      <p className="text-sm text-white/40 leading-relaxed mb-8 font-sans">
                        {phase.description}
                      </p>

                      {/* Animated check items */}
                      <div className="space-y-3.5 border-t border-white/[0.06] pt-6">
                        {phase.bullets.map((bullet, bulletIdx) => (
                          <div key={bulletIdx} className="flex items-center gap-3 text-xs text-white/50 font-medium">
                            <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                            <span>{bullet}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </GlassCard>

                {/* Arrow connector for desktop */}
                {index < phases.length - 1 && (
                  <div className="hidden lg:flex absolute top-[4.5rem] -right-5 -translate-y-1/2 z-30">
                    <ArrowRight className="w-5 h-5 text-white/10" />
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
