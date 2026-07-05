'use client';

import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

/**
 * LandingNavbar — Glassmorphism sticky navigation bar.
 * Uses sticky positioning (not fixed) because the scroll container
 * is an inner div with overflow-y-auto, not the window.
 * Detects scroll via IntersectionObserver on a sentinel element.
 */

interface LandingNavbarProps {
  onNavigate: (view: string) => void;
  onScrollTo: (section: string) => void;
}

export default function LandingNavbar({ onNavigate, onScrollTo }: LandingNavbarProps) {
  const [hasScrolled, setHasScrolled] = useState(false);
  const sentinelRef = useRef<HTMLDivElement>(null);

  // Use IntersectionObserver on a sentinel div to detect scroll position
  // This works regardless of which element is the scroll container
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setHasScrolled(!entry.isIntersecting);
      },
      { threshold: 0 }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, []);

  return (
    <>
      {/* Invisible sentinel at the very top — when it scrolls out of view, navbar gets background */}
      <div ref={sentinelRef} className="absolute top-0 left-0 w-full h-1 pointer-events-none" />
      
      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.1 }}
        className={`sticky top-0 z-50 transition-all duration-500 ${
          hasScrolled
            ? 'bg-[#030306]/80 backdrop-blur-xl border-b border-white/[0.04]'
            : 'bg-transparent border-b border-transparent'
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 h-[4.5rem] flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <span className="text-white font-bold text-xs tracking-tighter">AR</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold tracking-tight text-white">Agent-RR</span>
              <span className="text-[9px] text-white/25 font-mono border border-white/[0.06] bg-white/[0.02] px-1.5 py-0.5 rounded-md">
                v0.1.0
              </span>
            </div>
          </div>

          {/* Anchor Links */}
          <nav className="hidden md:flex items-center gap-8">
            {[
              { label: 'Features', section: 'features' },
              { label: 'Demo', section: 'demo' },
              { label: 'Architecture', section: 'architecture' },
              { label: 'Performance', section: 'performance' },
            ].map((item) => (
              <button
                key={item.section}
                onClick={() => onScrollTo(item.section)}
                className="text-xs font-medium text-white/35 hover:text-white/80 transition-colors duration-300 cursor-pointer"
              >
                {item.label}
              </button>
            ))}
          </nav>

          {/* CTA */}
          <button
            onClick={() => onNavigate('dashboard')}
            className="relative group px-5 py-2 rounded-xl bg-white/[0.05] border border-white/[0.08] hover:bg-white/[0.1] hover:border-white/[0.15] transition-all duration-300 text-white text-xs font-semibold flex items-center gap-2 cursor-pointer"
          >
            <span>Launch Console</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </button>
        </div>
      </motion.header>
    </>
  );
}
