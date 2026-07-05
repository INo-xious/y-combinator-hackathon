'use client';

import { useState, useEffect } from 'react';

/**
 * Tracks mouse position normalized to window dimensions.
 * Returns values from -0.5 to 0.5 centered on viewport middle.
 * Used for parallax, 3D camera movement, and cursor-reactive effects.
 */
export function useMousePosition() {
  const [position, setPosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setPosition({
        x: (e.clientX / window.innerWidth) - 0.5,
        y: (e.clientY / window.innerHeight) - 0.5,
      });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return position;
}
