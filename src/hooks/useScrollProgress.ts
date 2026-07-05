'use client';

import { useState, useEffect, useRef, RefObject } from 'react';

/**
 * Tracks scroll progress of an element through the viewport.
 * Returns a value from 0 (element below viewport) to 1 (element above viewport).
 * Used for scroll-linked animations and section reveals.
 */
export function useScrollProgress(ref: RefObject<HTMLElement | null>) {
  const [progress, setProgress] = useState(0);
  const [isInView, setIsInView] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsInView(entry.isIntersecting);
      },
      { threshold: 0.1 }
    );

    observer.observe(element);

    const handleScroll = () => {
      if (!element) return;
      const rect = element.getBoundingClientRect();
      const windowHeight = window.innerHeight;
      
      // Calculate how far through the viewport the element has scrolled
      const start = windowHeight;
      const end = -rect.height;
      const current = rect.top;
      const p = 1 - (current - end) / (start - end);
      
      setProgress(Math.max(0, Math.min(1, p)));
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();

    return () => {
      observer.disconnect();
      window.removeEventListener('scroll', handleScroll);
    };
  }, [ref]);

  return { progress, isInView };
}
