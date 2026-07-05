'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, Gauge, Shield, Coins } from 'lucide-react';
import SectionHeader from '@/components/shared/SectionHeader';
import AnimatedCounter from '@/components/shared/AnimatedCounter';

/**
 * PerformanceSection — Showcases key metrics with animated counters
 * and elegant stat cards. Scroll-triggered animations.
 */

const metrics = [
  {
    icon: <Coins className="w-5 h-5" />,
    label: 'Cost Reduction',
    target: 98,
    suffix: '%',
    description: 'Average savings per debug cycle by eliminating LLM API calls during replay',
    color: 'text-blue-400',
    borderColor: 'border-blue-500/20',
    bgGradient: 'from-blue-500/10 to-transparent',
  },
  {
    icon: <Gauge className="w-5 h-5" />,
    label: 'Replay Latency',
    target: 50,
    suffix: 'ms',
    description: 'Average time to replay a full agent execution from cached traces',
    color: 'text-purple-400',
    borderColor: 'border-purple-500/20',
    bgGradient: 'from-purple-500/10 to-transparent',
  },
  {
    icon: <Shield className="w-5 h-5" />,
    label: 'Deterministic',
    target: 100,
    suffix: '%',
    description: 'Identical outputs on every replay run guaranteed by cryptographic hash verification',
    color: 'text-emerald-400',
    borderColor: 'border-emerald-500/20',
    bgGradient: 'from-emerald-500/10 to-transparent',
  },
  {
    icon: <TrendingUp className="w-5 h-5" />,
    label: 'API Calls Saved',
    target: 100,
    suffix: '%',
    description: 'Zero external API requests during offline replay — everything served from local cache',
    color: 'text-cyan-400',
    borderColor: 'border-cyan-500/20',
    bgGradient: 'from-cyan-500/10 to-transparent',
  },
];

export default function PerformanceSection() {
  return (
    <section className="relative py-32 overflow-hidden">
      {/* Top divider */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />
      
      {/* Subtle grid background */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.01)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.01)_1px,transparent_1px)] bg-[size:6rem_6rem] [mask-image:radial-gradient(ellipse_50%_50%_at_50%_50%,#000_30%,transparent_100%)] pointer-events-none" />

      <div className="max-w-6xl mx-auto px-6">
        <SectionHeader
          badge="Performance"
          badgeIcon={<TrendingUp className="w-3.5 h-3.5" />}
          badgeColor="blue"
          title="Numbers that matter"
          subtitle="Agent-RR is engineered for speed, reliability, and cost efficiency at every layer of the debugging stack."
        />

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {metrics.map((metric, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-50px' }}
              transition={{
                duration: 0.6,
                delay: index * 0.1,
                ease: [0.21, 0.45, 0.27, 0.9],
              }}
              className={`relative rounded-2xl border ${metric.borderColor} bg-white/[0.02] p-8 text-center group hover:bg-white/[0.04] transition-all duration-500 overflow-hidden`}
            >
              {/* Background gradient */}
              <div className={`absolute inset-0 bg-gradient-to-b ${metric.bgGradient} opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none`} />
              
              <div className="relative">
                {/* Icon */}
                <div className={`${metric.color} mx-auto mb-4`}>
                  {metric.icon}
                </div>

                {/* Animated number */}
                <div className={`text-5xl font-bold font-[family-name:var(--font-display)] ${metric.color} mb-2`}>
                  <AnimatedCounter
                    target={metric.target}
                    suffix={metric.suffix}
                    duration={2000}
                  />
                </div>

                {/* Label */}
                <div className="text-sm font-semibold text-white mb-2">
                  {metric.label}
                </div>

                <p className="text-xs text-white/30 leading-relaxed">
                  {metric.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
