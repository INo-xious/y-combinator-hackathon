'use client';

/**
 * LandingView — Re-exports the new premium LandingPage component.
 * 
 * This file preserves the original import path used by page.tsx
 * while delegating to the new modular landing page implementation.
 * The LandingPageProps interface matches the original LandingViewProps.
 */

import LandingPage from '@/components/landing/LandingPage';

interface LandingViewProps {
  onNavigate: (view: string) => void;
}

export default function LandingView({ onNavigate }: LandingViewProps) {
  return <LandingPage onNavigate={onNavigate} />;
}
