'use client';

import React, { Suspense } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Sparkles } from 'lucide-react';
import { useMousePosition } from '@/hooks/useMousePosition';
import MagneticButton from '@/components/shared/MagneticButton';

// Lazy load the heavy 3D scene
const NeuralScene = React.lazy(() => import('./NeuralScene'));

interface HeroSectionProps {
  onNavigate: (view: string) => void;
  onScrollToTour: () => void;
}

export default function HeroSection({ onNavigate, onScrollToTour }: HeroSectionProps) {
  const mouse = useMousePosition();

  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Deep background gradients */}
      <div className="absolute inset-0 bg-[#030306]" />
      <div className="absolute top-0 left-1/4 w-[800px] h-[800px] rounded-full bg-blue-500/[0.04] blur-[150px] pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-[600px] h-[600px] rounded-full bg-purple-500/[0.04] blur-[130px] pointer-events-none" />
      <div className="absolute top-1/3 right-1/3 w-[400px] h-[400px] rounded-full bg-cyan-500/[0.03] blur-[100px] pointer-events-none" />
      
      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_70%_50%_at_50%_50%,#000_30%,transparent_100%)] pointer-events-none" />

      {/* 3D Neural Network Scene */}
      <Suspense fallback={null}>
        <NeuralScene mouseX={mouse.x} mouseY={mouse.y} />
      </Suspense>

      {/* Content overlay */}
      <div className="relative z-10 max-w-6xl mx-auto px-6 text-center">
        {/* Glowing pill badge */}
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/[0.08] border border-blue-500/20 text-blue-400 text-xs font-semibold tracking-wider uppercase mb-8"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Deterministic Replay for AI Agents</span>
        </motion.div>

        {/* Main headline — massive, bold, gradient */}
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4, ease: [0.21, 0.45, 0.27, 0.9] }}
          className="text-5xl md:text-7xl lg:text-[5.5rem] font-bold tracking-tight leading-[1.05] font-[family-name:var(--font-display)]"
        >
          <span className="text-white">Record once.</span>
          <br />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-purple-400 to-cyan-400">
            Replay forever.
          </span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.7 }}
          className="mt-7 text-lg md:text-xl text-white/40 max-w-2xl mx-auto leading-relaxed"
        >
          Stop debugging non-deterministic AI agents in production. Capture every LLM call, tool invocation, and state transition into verifiable causal DAGs. Replay offline. Debug with surgical precision.
        </motion.p>

        {/* CTA buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 1.0 }}
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
          transition={{ delay: 1.5, duration: 1 }}
          className="absolute bottom-12 left-1/2 -translate-x-1/2"
        >
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            className="w-5 h-8 rounded-full border border-white/10 flex items-start justify-center p-1.5"
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
