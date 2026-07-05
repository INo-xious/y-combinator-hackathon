'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, Bug, Shuffle, DollarSign } from 'lucide-react';
import SectionHeader from '@/components/shared/SectionHeader';

/**
 * ProblemSection — Visually explains the pain points of debugging
 * non-deterministic AI agents with animated card reveals.
 */

const problems = [
  {
    icon: <Shuffle className="w-6 h-6" />,
    title: 'Non-Deterministic Outputs',
    description: 'LLM agents produce different results on every run. The same prompt yields different decisions, making bugs impossible to reproduce consistently.',
    color: 'text-red-400',
    borderColor: 'border-red-500/20',
    bgColor: 'bg-red-500/[0.05]',
    glowColor: 'bg-red-500/[0.03]',
  },
  {
    icon: <Bug className="w-6 h-6" />,
    title: 'Invisible Failure Points',
    description: 'Multi-step agent pipelines silently diverge mid-execution. By the time you see wrong output, the root cause is buried 5 steps back in the DAG.',
    color: 'text-amber-400',
    borderColor: 'border-amber-500/20',
    bgColor: 'bg-amber-500/[0.05]',
    glowColor: 'bg-amber-500/[0.03]',
  },
  {
    icon: <DollarSign className="w-6 h-6" />,
    title: 'Expensive Debugging Cycles',
    description: 'Every debug attempt costs real money. Re-running LLM calls at $0.03/1K tokens burns budget fast when you need 50 iterations to find a prompt regression.',
    color: 'text-orange-400',
    borderColor: 'border-orange-500/20',
    bgColor: 'bg-orange-500/[0.05]',
    glowColor: 'bg-orange-500/[0.03]',
  },
];

export default function ProblemSection() {
  return (
    <section className="relative py-32 overflow-hidden">
      {/* Subtle red ambient glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-red-500/[0.02] blur-[150px] pointer-events-none" />
      
      <div className="max-w-6xl mx-auto px-6">
        <SectionHeader
          badge="The problem"
          badgeIcon={<AlertTriangle className="w-3.5 h-3.5" />}
          badgeColor="amber"
          title="AI agents are impossible to debug"
          subtitle="Traditional debugging tools were built for deterministic code. AI agent pipelines are anything but."
        />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {problems.map((problem, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-50px' }}
              transition={{ 
                duration: 0.6, 
                delay: index * 0.15,
                ease: [0.21, 0.45, 0.27, 0.9],
              }}
              className={`relative group rounded-2xl border ${problem.borderColor} ${problem.bgColor} p-8 transition-all duration-500 hover:border-opacity-60`}
            >
              {/* Hover glow */}
              <div className={`absolute -inset-px rounded-2xl ${problem.glowColor} opacity-0 group-hover:opacity-100 blur-xl transition-opacity duration-500 pointer-events-none`} />
              
              <div className="relative">
                {/* Icon */}
                <div className={`${problem.color} mb-5`}>
                  {problem.icon}
                </div>
                
                {/* Pulsing indicator dot */}
                <div className="absolute top-0 right-0">
                  <span className="flex h-2.5 w-2.5">
                    <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${problem.color.replace('text-', 'bg-')} opacity-40`} />
                    <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${problem.color.replace('text-', 'bg-')} opacity-60`} />
                  </span>
                </div>

                <h3 className="text-lg font-semibold text-white mb-3">{problem.title}</h3>
                <p className="text-sm text-white/40 leading-relaxed">{problem.description}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
