'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import MagneticButton from '@/components/shared/MagneticButton';

interface CTASectionProps {
  onNavigate: (view: string) => void;
}

export default function CTASection({ onNavigate }: CTASectionProps) {
  return (
    <section className="relative py-44 overflow-hidden">
      {/* Top divider */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/[0.04] to-transparent" />
      
      {/* Massive ambient glows */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full bg-blue-500/[0.03] blur-[200px] pointer-events-none" />
      <div className="absolute top-1/3 left-1/4 w-[400px] h-[400px] rounded-full bg-purple-500/[0.02] blur-[150px] pointer-events-none" />
      <div className="absolute bottom-1/3 right-1/4 w-[400px] h-[400px] rounded-full bg-cyan-500/[0.02] blur-[150px] pointer-events-none" />
      
      {/* Grid pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.015)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.015)_1px,transparent_1px)] bg-[size:5rem_5rem] [mask-image:radial-gradient(ellipse_60%_60%_at_50%_50%,#000_10%,transparent_80%)] pointer-events-none" />

      <div className="max-w-4xl mx-auto px-6 relative z-10 text-center">
        {/* Massive headline */}
        <motion.h2
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.8, ease: [0.21, 0.45, 0.27, 0.9] }}
          className="text-5xl md:text-7xl lg:text-[5.5rem] font-bold tracking-tight leading-[1.05] font-[family-name:var(--font-display)]"
        >
          <span className="text-white">Take control of</span>
          <br />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-purple-400 to-cyan-400 animate-gradient-x">
            agent flakiness
          </span>
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="mt-8 text-base md:text-lg text-white/35 max-w-xl mx-auto leading-relaxed font-sans"
        >
          Diagnose prompt degradation, check tool performance regressions, and trace complex token loops with the <span className="text-white/80 font-semibold">M²</span> offline developer dashboard.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="mt-12 flex justify-center"
        >
          <MagneticButton onClick={() => onNavigate('dashboard')} variant="primary" size="large">
            <span>Launch App Console</span>
            <ArrowRight className="w-5 h-5" />
          </MagneticButton>
        </motion.div>
      </div>
    </section>
  );
}
