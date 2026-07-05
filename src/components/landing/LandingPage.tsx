'use client';

import React, { useRef, useEffect, Suspense } from 'react';
import LandingNavbar from './LandingNavbar';
import HeroSection from './HeroSection';
import ProblemSection from './ProblemSection';
import SolutionSection from './SolutionSection';
import FeaturesSection from './FeaturesSection';
import DemoSection from './DemoSection';
import ArchitectureSection from './ArchitectureSection';
import PerformanceSection from './PerformanceSection';
import CTASection from './CTASection';
import FooterSection from './FooterSection';
import NeuralScene from './NeuralScene';
import { useMousePosition } from '@/hooks/useMousePosition';

interface LandingPageProps {
  onNavigate: (view: string) => void;
}

export default function LandingPage({ onNavigate }: LandingPageProps) {
  const mouse = useMousePosition();
  const scrollProgress = useRef(0);
  const scrollVelocity = useRef(0);

  const featuresRef = useRef<HTMLDivElement>(null);
  const demoRef = useRef<HTMLDivElement>(null);
  const architectureRef = useRef<HTMLDivElement>(null);
  const performanceRef = useRef<HTMLDivElement>(null);

  const scrollToSection = (section: string) => {
    let targetRef: React.RefObject<HTMLDivElement | null> | null = null;
    if (section === 'features') targetRef = featuresRef;
    if (section === 'demo') targetRef = demoRef;
    if (section === 'architecture') targetRef = architectureRef;
    if (section === 'performance') targetRef = performanceRef;

    if (targetRef?.current) {
      targetRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  // Setup Lenis Smooth Scrolling & track window scroll progress
  useEffect(() => {
    // Dynamically import Lenis to prevent SSR issue
    import('lenis').then(({ default: Lenis }) => {
      const lenis = new Lenis({
        duration: 1.2,
        easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)), // Apple/Linear smooth exponential transition
        smoothWheel: true,
      });

      function raf(time: number) {
        lenis.raf(time);
        requestAnimationFrame(raf);
      }
      requestAnimationFrame(raf);

      return () => {
        lenis.destroy();
      };
    });

    let lastScrollY = window.scrollY;
    let lastTime = Date.now();

    const handleScroll = () => {
      const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
      const currentScrollY = window.scrollY;
      
      if (scrollHeight > 0) {
        scrollProgress.current = currentScrollY / scrollHeight;
      }
      
      const now = Date.now();
      const dt = Math.max(1, now - lastTime);
      const dy = currentScrollY - lastScrollY;
      
      // Calculate velocity (pixels per ms) and smooth it
      scrollVelocity.current = scrollVelocity.current * 0.85 + Math.abs(dy / dt) * 0.15;
      
      lastScrollY = currentScrollY;
      lastTime = now;
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll(); // initial call
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-[#030306] text-white overflow-x-hidden selection:bg-blue-500/20 relative">
      {/* Immersive 3D Backdrop Scene */}
      <Suspense fallback={null}>
        <NeuralScene 
          mouseX={mouse.x} 
          mouseY={mouse.y} 
          scrollProgress={scrollProgress}
          scrollVelocity={scrollVelocity}
        />
      </Suspense>

      {/* Foreground Content */}
      <div className="relative z-10">
        {/* Fixed Navigation */}
        <LandingNavbar onNavigate={onNavigate} onScrollTo={scrollToSection} />

        {/* Hero — Full viewport */}
        <HeroSection onNavigate={onNavigate} onScrollToTour={() => scrollToSection('demo')} />

        {/* Problem — Pain points */}
        <ProblemSection />

        {/* Solution — How it works conceptually */}
        <SolutionSection />

        {/* Features — Interactive cards */}
        <div ref={featuresRef}>
          <FeaturesSection />
        </div>

        {/* Demo — Interactive time-travel debugger (PRESERVED) */}
        <div ref={demoRef}>
          <DemoSection />
        </div>

        {/* Architecture — Developer workflow */}
        <div ref={architectureRef}>
          <ArchitectureSection onNavigate={onNavigate} />
        </div>

        {/* Performance — Animated metrics */}
        <div ref={performanceRef}>
          <PerformanceSection />
        </div>

        {/* Final CTA */}
        <CTASection onNavigate={onNavigate} />

        {/* Footer */}
        <FooterSection />
      </div>
    </div>
  );
}
