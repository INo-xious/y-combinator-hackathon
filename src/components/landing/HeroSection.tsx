'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Sparkles } from 'lucide-react';
import MagneticButton from '@/components/shared/MagneticButton';
import Logo from '@/components/shared/Logo';

interface HeroSectionProps {
  onNavigate: (view: string) => void;
  onScrollToTour: () => void;
}

export default function HeroSection({ onNavigate, onScrollToTour }: HeroSectionProps) {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-20">
      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:5rem_5rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_20%,transparent_100%)] pointer-events-none" />

      {/* Content overlay */}
      <div className="relative z-10 max-w-6xl mx-auto px-6 text-center">
        {/* Animated Brand Logo Centerpiece */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
          className="flex justify-center mb-8"
        >
          <div className="relative p-2.5 rounded-3xl bg-white/[0.01] border border-white/[0.04] backdrop-blur-xl shadow-2xl">
            <Logo size="xl" animate={true} />
          </div>
        </motion.div>

        {/* Glowing pill badge */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="inline-flex items-center gap-2.5 px-4 py-2 rounded-full bg-blue-500/[0.08] border border-blue-500/20 text-blue-400 text-xs font-semibold tracking-wider uppercase mb-8 backdrop-blur-sm"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Deterministic Replay for AI Agents</span>
        </motion.div>

        {/* Main headline — massive, bold, gradient */}
        <motion.h1
          initial={{ opacity: 0, y: 25 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.5, ease: [0.21, 0.45, 0.27, 0.9] }}
          className="text-5xl md:text-7xl lg:text-[6rem] font-bold tracking-tight leading-[1.02] font-[family-name:var(--font-display)]"
        >
          <span className="text-white">Record once.</span>
          <br />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-purple-400 to-cyan-400">
            Replay forever.
          </span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.7 }}
          className="mt-8 text-base md:text-lg text-white/40 max-w-2xl mx-auto leading-relaxed"
        >
          Stop debugging non-deterministic AI agents in production. Capture every LLM call, database query, and tool state transition into cryptographic, verifiable causal DAGs with <span className="text-white/80 font-bold">M²</span>.
        </motion.p>

        {/* CTA buttons */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.9 }}
          className="mt-12 flex flex-col sm:flex-row justify-center items-center gap-4"
        >
          <MagneticButton onClick={() => onNavigate('dashboard')} variant="primary" size="large">
            <span>Launch Developer Console</span>
            <ArrowRight className="w-5 h-5" />
          </MagneticButton>
          
          <MagneticButton onClick={onScrollToTour} variant="secondary" size="large">
            <span>See it in action</span>
          </MagneticButton>
        </motion.div>

        {/* Scroll indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.3, duration: 0.8 }}
          className="absolute bottom-12 left-1/2 -translate-x-1/2"
        >
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            className="w-5 h-8 rounded-full border border-white/10 flex items-start justify-center p-1.5 cursor-pointer backdrop-blur-sm hover:border-white/30 transition-colors"
            onClick={onScrollToTour}
          >
            <div className="w-1 h-2 rounded-full bg-white/30" />
          </motion.div>
        </motion.div>
      </div>

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 left-0 right-0 h-40 bg-gradient-to-t from-[#030306] to-transparent pointer-events-none z-10" />
    </section>
  );
}
