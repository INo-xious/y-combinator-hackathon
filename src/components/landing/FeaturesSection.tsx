'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Zap, GitCompare, ShieldCheck, Layers } from 'lucide-react';
import SectionHeader from '@/components/shared/SectionHeader';
import GlassCard from '@/components/shared/GlassCard';

const features = [
  {
    icon: <Zap className="w-6 h-6" />,
    title: 'Zero-Cost Offline Replay',
    description: 'We cache every external dependency, database state, and LLM query during live runs. Replays run completely locally, eliminating API fees and letting you retry logic tweaks at lightning speed.',
    stat: '98% cost reduction',
    statLabel: 'Average savings per debug cycle',
    color: 'text-blue-400',
    glowColor: 'rgba(59, 130, 246, 0.12)',
    gradient: 'from-blue-500/20 to-blue-600/5',
  },
  {
    icon: <GitCompare className="w-6 h-6" />,
    title: 'Causal DAG & Hash Integrity',
    description: 'Traces are compiled into Directed Acyclic Graphs. Each node carries a cryptographic SHA-256 hash representing code state, prompt contents, and dependencies. Automatically flag the exact step where executions diverge.',
    stat: 'SHA-256 verified',
    statLabel: 'Cryptographic validation',
    color: 'text-purple-400',
    glowColor: 'rgba(139, 92, 246, 0.12)',
    gradient: 'from-purple-500/20 to-purple-600/5',
  },
  {
    icon: <ShieldCheck className="w-6 h-6" />,
    title: 'Automated Privacy Guard',
    description: 'Integrate production logging without leaking secrets. M² parses all tracing output and redacts API tokens, database passwords, user emails, and phone numbers before writing logs to disk.',
    stat: 'PII-safe by default',
    statLabel: 'Automatic redaction engine',
    color: 'text-emerald-400',
    glowColor: 'rgba(16, 185, 129, 0.12)',
    gradient: 'from-emerald-500/20 to-emerald-600/5',
  },
];

export default function FeaturesSection() {
  return (
    <section className="relative py-36 overflow-hidden">
      {/* Divider line */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/[0.04] to-transparent" />
      
      <div className="max-w-6xl mx-auto px-6 relative z-10">
        <SectionHeader
          badge="Core capabilities"
          badgeIcon={<Layers className="w-3.5 h-3.5" />}
          badgeColor="blue"
          title="Built for high-fidelity agent development"
          subtitle="Resolve flakiness, debug output regression, and log agent states in safe, production-grade sandbox runs."
        />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-12">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-50px' }}
              transition={{
                duration: 0.7,
                delay: index * 0.12,
                ease: [0.21, 0.45, 0.27, 0.9],
              }}
            >
              <GlassCard glowColor={feature.glowColor} className="h-full">
                <div className="p-8 flex flex-col justify-between h-full min-h-[360px]">
                  <div>
                    {/* Icon with floating animation */}
                    <motion.div
                      animate={{ y: [0, -4, 0] }}
                      transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut', delay: index * 0.1 }}
                      className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.gradient} border border-white/[0.06] flex items-center justify-center ${feature.color} mb-6`}
                    >
                      {feature.icon}
                    </motion.div>

                    <h3 className="text-xl font-bold text-white mb-3 font-[family-name:var(--font-display)]">
                      {feature.title}
                    </h3>
                    <p className="text-sm text-white/40 leading-relaxed font-sans">
                      {feature.description}
                    </p>
                  </div>

                  {/* Bottom stat bar */}
                  <div className="mt-8 pt-5 border-t border-white/[0.06]">
                    <div className={`text-sm font-mono font-bold ${feature.color}`}>
                      {feature.stat}
                    </div>
                    <div className="text-[11px] text-white/35 mt-0.5 font-medium">
                      {feature.statLabel}
                    </div>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
