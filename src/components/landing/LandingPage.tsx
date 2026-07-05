'use client';

import React, { useRef } from 'react';
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

/**
 * LandingPage — Main orchestrator for the premium landing experience.
 * Manages section refs for anchor navigation.
 * 
 * NOTE: Lenis smooth scroll removed — page.tsx wraps content in
 * h-screen overflow-hidden, so scrolling is handled by the inner
 * overflow-y-auto container. Lenis targets window scroll which is
 * locked by that parent layout.
 * 
 * Props interface matches original LandingView for seamless integration.
 */

interface LandingPageProps {
  onNavigate: (view: string) => void;
}

export default function LandingPage({ onNavigate }: LandingPageProps) {

  // Section refs for anchor navigation
  const sectionRefs = {
    features: useRef<HTMLDivElement>(null),
    demo: useRef<HTMLDivElement>(null),
    architecture: useRef<HTMLDivElement>(null),
    performance: useRef<HTMLDivElement>(null),
  };

  const scrollToSection = (section: string) => {
    const ref = sectionRefs[section as keyof typeof sectionRefs];
    if (ref?.current) {
      ref.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <div className="min-h-screen bg-[#030306] text-white overflow-x-hidden selection:bg-blue-500/20">
      {/* Fixed Navigation */}
      <LandingNavbar onNavigate={onNavigate} onScrollTo={scrollToSection} />

      {/* Hero — Full viewport with 3D scene */}
      <HeroSection onNavigate={onNavigate} onScrollToTour={() => scrollToSection('demo')} />

      {/* Problem — Pain points */}
      <ProblemSection />

      {/* Solution — How it works conceptually */}
      <SolutionSection />

      {/* Features — Interactive cards */}
      <div ref={sectionRefs.features}>
        <FeaturesSection />
      </div>

      {/* Demo — Interactive time-travel debugger (PRESERVED) */}
      <div ref={sectionRefs.demo}>
        <DemoSection />
      </div>

      {/* Architecture — Developer workflow */}
      <div ref={sectionRefs.architecture}>
        <ArchitectureSection onNavigate={onNavigate} />
      </div>

      {/* Performance — Animated metrics */}
      <div ref={sectionRefs.performance}>
        <PerformanceSection />
      </div>

      {/* Final CTA */}
      <CTASection onNavigate={onNavigate} />

      {/* Footer */}
      <FooterSection />
    </div>
  );
}
