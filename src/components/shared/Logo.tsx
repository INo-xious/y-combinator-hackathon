'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface LogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  animate?: boolean;
}

export default function Logo({ className = '', size = 'md', animate = true }: LogoProps) {
  // Dimension mapping for sizing
  const dimensions = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-16 h-16',
    xl: 'w-24 h-24',
  };

  // Outer interlocking "M" coordinates
  const outerMPath = "M 18 75 L 18 30 L 50 58 L 82 30 L 82 75";
  // Inner interlocking "M" coordinates (Founder 2)
  const innerMPath = "M 30 75 L 30 42 L 50 58 L 70 42 L 70 75";
  // Super-script ² coordinate
  const exponentPath = "M 86,18 C 86,14 89,12 91.5,12 C 94,12 96,14 96,16.5 C 96,19.5 93,22 91,23.5 L 86,27 L 96,27";

  // Animation variants
  const pathVariants: any = {
    hidden: { pathLength: 0, opacity: 0 },
    visible: (customDelay: number) => ({
      pathLength: 1,
      opacity: 1,
      transition: {
        pathLength: { delay: customDelay, duration: 1.2, ease: [0.16, 1, 0.3, 1] },
        opacity: { delay: customDelay, duration: 0.3 }
      }
    })
  };

  const dotVariants: any = {
    hidden: { scale: 0, opacity: 0 },
    visible: (customDelay: number) => ({
      scale: 1,
      opacity: 1,
      transition: {
        delay: customDelay,
        type: 'spring',
        stiffness: 260,
        damping: 20
      }
    })
  };

  return (
    <motion.div
      className={`relative inline-block ${dimensions[size]} ${className}`}
      whileHover={animate ? "hover" : undefined}
      initial="hidden"
      animate="visible"
    >
      <svg
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full drop-shadow-[0_0_12px_rgba(59,130,246,0.25)]"
      >
        <defs>
          {/* Gradient for Outer M */}
          <linearGradient id="outerGrad" x1="18" y1="30" x2="82" y2="75" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#3b82f6" /> {/* Electric Blue */}
            <stop offset="50%" stopColor="#8b5cf6" /> {/* Indigo */}
            <stop offset="100%" stopColor="#06b6d4" /> {/* Cyan */}
          </linearGradient>

          {/* Gradient for Inner M */}
          <linearGradient id="innerGrad" x1="30" y1="42" x2="70" y2="75" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#8b5cf6" />
            <stop offset="100%" stopColor="#ec4899" /> {/* Purple-Pink */}
          </linearGradient>

          {/* Glow Filter */}
          <filter id="neonGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Outer interlocking M */}
        <motion.path
          d={outerMPath}
          stroke="url(#outerGrad)"
          strokeWidth="6"
          strokeLinecap="round"
          strokeLinejoin="round"
          custom={0.1}
          variants={pathVariants}
          animate="visible"
          variants-hover={{ strokeWidth: 7 }}
          transition={{ duration: 0.3 }}
        />

        {/* Inner interlocking M */}
        <motion.path
          d={innerMPath}
          stroke="url(#innerGrad)"
          strokeWidth="5"
          strokeLinecap="round"
          strokeLinejoin="round"
          custom={0.4}
          variants={pathVariants}
          animate="visible"
        />

        {/* Geometric Superscript Exponent ² */}
        <motion.path
          d={exponentPath}
          stroke="#06b6d4"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
          custom={0.7}
          variants={pathVariants}
          animate="visible"
          className="drop-shadow-[0_0_8px_rgba(6,182,212,0.6)]"
        />

        {/* Geometric Vertex Dots/Nodes to represent Precision/Interconnected Graphs */}
        <motion.circle
          cx="18"
          cy="30"
          r="4.5"
          fill="#3b82f6"
          stroke="#030306"
          strokeWidth="1.5"
          custom={1.0}
          variants={dotVariants}
        />
        <motion.circle
          cx="82"
          cy="30"
          r="4.5"
          fill="#06b6d4"
          stroke="#030306"
          strokeWidth="1.5"
          custom={1.1}
          variants={dotVariants}
        />
        <motion.circle
          cx="50"
          cy="58"
          r="5.5"
          fill="#8b5cf6"
          stroke="#030306"
          strokeWidth="1.5"
          custom={1.2}
          variants={dotVariants}
          className="drop-shadow-[0_0_6px_#8b5cf6]"
        />
        <motion.circle
          cx="30"
          cy="42"
          r="4"
          fill="#8b5cf6"
          stroke="#030306"
          strokeWidth="1.5"
          custom={1.3}
          variants={dotVariants}
        />
        <motion.circle
          cx="70"
          cy="42"
          r="4"
          fill="#ec4899"
          stroke="#030306"
          strokeWidth="1.5"
          custom={1.4}
          variants={dotVariants}
        />
      </svg>
    </motion.div>
  );
}
