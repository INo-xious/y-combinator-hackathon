'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, Bug, Shuffle, DollarSign } from 'lucide-react';
import SectionHeader from '@/components/shared/SectionHeader';
import GlassCard from '@/components/shared/GlassCard';

const problems = [
  {
    icon: <Shuffle className="w-6 h-6" />,
    title: 'Non-Deterministic Outputs',
    description: 'LLM agents produce different results on every run. The same prompt yields different decisions, making bugs impossible to reproduce consistently.',
    color: 'text-red-400',
    glowColor: 'rgba(239, 68, 68, 0.12)',
    gradient: 'from-red-500/10 to-red-600/5',
  },
  {
    icon: <Bug className="w-6 h-6" />,
    title: 'Invisible Failure Points',
    description: 'Multi-step agent pipelines silently diverge mid-execution. By the time you see wrong output, the root cause is buried 5 steps back in the DAG.',
    color: 'text-amber-400',
    glowColor: 'rgba(245, 158, 11, 0.12)',
    gradient: 'from-amber-500/10 to-amber-600/5',
  },
  {
    icon: <DollarSign className="w-6 h-6" />,
    title: 'Expensive Debugging Cycles',
    description: 'Every debug attempt costs real money. Re-running LLM calls at $0.03/1K tokens burns budget fast when you need 50 iterations to find a prompt regression.',
    color: 'text-orange-400',
    glowColor: 'rgba(249, 115, 22, 0.12)',
    gradient: 'from-orange-500/10 to-orange-600/5',
  },
];

export default function ProblemSection() {
  return (
    <section className="relative py-36 overflow-hidden">
      {/* Red ambient glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] rounded-full bg-red-500/[0.015] blur-[150px] pointer-events-none" />
      
      <div className="max-w-6xl mx-auto px-6 relative z-10">
        <SectionHeader
          badge="The problem"
          badgeIcon={<AlertTriangle className="w-3.5 h-3.5" />}
          badgeColor="amber"
          title="AI agents are impossible to debug"
          subtitle="Traditional debugging tools were built for deterministic code. AI agent pipelines are anything but."
        />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {problems.map((problem, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-50px' }}
              transition={{ 
                duration: 0.7, 
                delay: index * 0.15,
                ease: [0.21, 0.45, 0.27, 0.9],
              }}
              className="h-full"
            >
              <GlassCard glowColor={problem.glowColor} className="h-full">
                <div className="p-8 flex flex-col justify-between h-full relative group">
                  {/* Glowing vertex pulse dot */}
                  <div className="absolute top-6 right-6">
                    <span className="flex h-2.5 w-2.5">
                      <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${problem.color.replace('text-', 'bg-')} opacity-40`} />
                      <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${problem.color.replace('text-', 'bg-')} opacity-60`} />
                    </span>
                  </div>

                  <div>
                    {/* Floating Icon with Gradient Background */}
                    <motion.div 
                      animate={{ y: [0, -3, 0] }}
                      transition={{ duration: 3.5, repeat: Infinity, ease: 'easeInOut', delay: index * 0.2 }}
                      className={`w-12 h-12 rounded-xl bg-gradient-to-br ${problem.gradient} border border-white/[0.04] flex items-center justify-center ${problem.color} mb-6`}
                    >
                      {problem.icon}
                    </motion.div>

                    <h3 className="text-lg font-bold text-white mb-3 font-[family-name:var(--font-display)]">
                      {problem.title}
                    </h3>
                    <p className="text-sm text-white/40 leading-relaxed font-sans">
                      {problem.description}
                    </p>
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
