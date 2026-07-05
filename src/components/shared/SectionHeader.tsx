'use client';

import React from 'react';
import { motion } from 'framer-motion';

/**
 * SectionHeader — Consistent section heading with animated pill badge,
 * title, and subtitle. Used across all landing page sections.
 */
interface SectionHeaderProps {
  badge?: string;
  badgeIcon?: React.ReactNode;
  title: string;
  subtitle?: string;
  badgeColor?: 'blue' | 'purple' | 'green' | 'amber';
  align?: 'center' | 'left';
}

const badgeColors = {
  blue: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
  purple: 'bg-purple-500/10 border-purple-500/20 text-purple-400',
  green: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
  amber: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
};

export default function SectionHeader({
  badge,
  badgeIcon,
  title,
  subtitle,
  badgeColor = 'blue',
  align = 'center',
}: SectionHeaderProps) {
  const alignClass = align === 'center' ? 'text-center mx-auto' : 'text-left';

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.7, ease: [0.21, 0.45, 0.27, 0.9] }}
      className={`max-w-3xl mb-20 ${alignClass}`}
    >
      {badge && (
        <div className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full border text-xs font-semibold tracking-wide uppercase mb-6 ${badgeColors[badgeColor]}`}>
          {badgeIcon}
          <span>{badge}</span>
        </div>
      )}
      
      <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-white leading-[1.1] font-[family-name:var(--font-display)]">
        {title}
      </h2>
      
      {subtitle && (
        <p className="mt-5 text-base md:text-lg text-white/50 leading-relaxed max-w-2xl" style={{ marginLeft: align === 'center' ? 'auto' : undefined, marginRight: align === 'center' ? 'auto' : undefined }}>
          {subtitle}
        </p>
      )}
    </motion.div>
  );
}
