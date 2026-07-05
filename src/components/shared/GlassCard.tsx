'use client';

import React, { useRef, useState } from 'react';

/**
 * GlassCard — Glassmorphism card with optional 3D tilt effect on mouse hover.
 * Features dynamic gradient border that follows the cursor.
 */
interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  tilt?: boolean;
  glowColor?: string;
}

export default function GlassCard({ 
  children, 
  className = '', 
  tilt = true,
  glowColor = 'rgba(59, 130, 246, 0.15)',
}: GlassCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [transform, setTransform] = useState('perspective(800px) rotateX(0deg) rotateY(0deg)');
  const [glowPos, setGlowPos] = useState({ x: 50, y: 50 });

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!tilt || !cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    
    const rotateX = (y - 0.5) * -8; // Max 4 degrees
    const rotateY = (x - 0.5) * 8;
    
    setTransform(`perspective(800px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`);
    setGlowPos({ x: x * 100, y: y * 100 });
  };

  const handleMouseLeave = () => {
    setTransform('perspective(800px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)');
    setGlowPos({ x: 50, y: 50 });
  };

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className={`relative rounded-2xl transition-transform duration-300 ease-out ${className}`}
      style={{ transform }}
    >
      {/* Dynamic glow that follows cursor */}
      <div 
        className="absolute inset-0 rounded-2xl opacity-0 hover:opacity-100 transition-opacity duration-500 pointer-events-none"
        style={{
          background: `radial-gradient(600px circle at ${glowPos.x}% ${glowPos.y}%, ${glowColor}, transparent 40%)`,
        }}
      />
      
      {/* Glass background */}
      <div className="relative h-full rounded-2xl bg-white/[0.03] backdrop-blur-sm border border-white/[0.06] overflow-hidden">
        {/* Inner gradient border glow */}
        <div 
          className="absolute inset-0 rounded-2xl opacity-0 hover:opacity-100 transition-opacity duration-500 pointer-events-none"
          style={{
            background: `radial-gradient(400px circle at ${glowPos.x}% ${glowPos.y}%, ${glowColor}, transparent 40%)`,
          }}
        />
        <div className="relative z-10 h-full">
          {children}
        </div>
      </div>
    </div>
  );
}
