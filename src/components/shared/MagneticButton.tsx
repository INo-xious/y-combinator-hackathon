'use client';

import React, { useRef, useState } from 'react';
import { motion } from 'framer-motion';

/**
 * MagneticButton — A button that subtly follows the cursor when hovered,
 * creating a magnetic pull effect. Used for premium CTAs.
 */
interface MagneticButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary';
  className?: string;
  size?: 'default' | 'large';
}

export default function MagneticButton({ 
  children, 
  onClick, 
  variant = 'primary',
  className = '',
  size = 'default',
}: MagneticButtonProps) {
  const ref = useRef<HTMLButtonElement>(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });

  const handleMouseMove = (e: React.MouseEvent<HTMLButtonElement>) => {
    const rect = ref.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;

    // Magnetic pull strength (higher = more pull)
    setPosition({ x: x * 0.3, y: y * 0.3 });
  };

  const handleMouseLeave = () => {
    setPosition({ x: 0, y: 0 });
  };

  const baseClasses = size === 'large'
    ? 'px-10 py-5 text-base'
    : 'px-7 py-3.5 text-sm';

  const variantClasses = variant === 'primary'
    ? 'bg-gradient-to-r from-blue-500 via-blue-600 to-purple-600 text-white shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40'
    : 'bg-white/[0.04] border border-white/[0.08] text-white/90 hover:bg-white/[0.08] hover:border-white/[0.15]';

  return (
    <motion.button
      ref={ref}
      onClick={onClick}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      animate={{ x: position.x, y: position.y }}
      transition={{ type: 'spring', stiffness: 150, damping: 15, mass: 0.1 }}
      className={`
        relative rounded-2xl font-semibold cursor-pointer
        transition-all duration-300 ease-out
        flex items-center justify-center gap-2.5
        overflow-hidden group
        ${baseClasses}
        ${variantClasses}
        ${className}
      `}
    >
      {/* Shimmer overlay on primary buttons */}
      {variant === 'primary' && (
        <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700 ease-in-out" />
      )}
      <span className="relative z-10 flex items-center gap-2.5">{children}</span>
    </motion.button>
  );
}
