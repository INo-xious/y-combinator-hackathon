'use client';

import React from 'react';
import { motion } from 'framer-motion';

/**
 * FooterSection — Clean minimal footer with gradient top border.
 * Preserves original footer links.
 */

export default function FooterSection() {
  return (
    <footer className="relative py-12 overflow-hidden">
      {/* Top gradient border */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />

      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8 }}
        className="max-w-6xl mx-auto px-6"
      >
        <div className="flex flex-col sm:flex-row justify-between items-center gap-6">
          {/* Logo & copyright */}
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <span className="text-white font-bold text-[10px] tracking-tighter">AR</span>
            </div>
            <span className="text-xs text-white/25">
              © 2026 Agent-RR Developer Platform. All rights reserved.
            </span>
          </div>

          {/* Links */}
          <div className="flex gap-8 text-xs text-white/25">
            <a href="#" className="hover:text-white/60 transition-colors duration-300">Documentation</a>
            <a href="#" className="hover:text-white/60 transition-colors duration-300">Github</a>
            <a href="#" className="hover:text-white/60 transition-colors duration-300">Privacy Policy</a>
          </div>
        </div>
      </motion.div>
    </footer>
  );
}
