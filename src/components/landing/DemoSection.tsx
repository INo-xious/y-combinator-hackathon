'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Play, Pause, RotateCcw, AlertTriangle, Cpu, Database,
  ShieldCheck, Zap, CheckCircle2, Terminal, Activity,
} from 'lucide-react';
import SectionHeader from '@/components/shared/SectionHeader';

/**
 * DemoSection — Interactive Time-Travel Debugger Sandbox.
 * 
 * CRITICAL: This component preserves ALL existing interactive debugger logic
 * from the original LandingView.tsx, including:
 * - DEMO_STEPS data
 * - Playback timer
 * - Scrubber controls (play/pause/reset/slider)
 * - Divergence simulation toggle
 * - JSON inspector panel
 * - Accumulated metrics display
 */

interface DemoStep {
  id: string;
  label: string;
  type: 'start' | 'db' | 'llm' | 'tool' | 'finish';
  toolName?: string;
  latency: string;
  cost: string;
  description: string;
  inputJson: string;
  outputJson: string;
  divergedOutputJson?: string;
}

const DEMO_STEPS: DemoStep[] = [
  {
    id: '1',
    label: 'Start Execution',
    type: 'start',
    latency: '0.0s',
    cost: '$0.000',
    description: 'Client triggers agent execution with incoming user request.',
    inputJson: JSON.stringify({ userId: 'usr_9812', message: 'I want a refund for my order #10023. It arrived damaged.' }, null, 2),
    outputJson: JSON.stringify({ userId: 'usr_9812', orderId: '10023', condition: 'damaged' }, null, 2),
  },
  {
    id: '2',
    label: 'Fetch Order details',
    type: 'db',
    toolName: 'PostgreSQL - orders_db',
    latency: '0.3s',
    cost: '$0.001',
    description: 'Agent queries the database to retrieve order timestamp, items, and delivery status.',
    inputJson: JSON.stringify({ orderId: '10023', fields: ['status', 'amount', 'delivered_at'] }, null, 2),
    outputJson: JSON.stringify({ status: 'delivered', amount: 89.99, delivered_at: '2026-07-04T14:30:00Z', items: ['Wireless Earbuds Pro'] }, null, 2),
  },
  {
    id: '3',
    label: 'Intent Classification',
    type: 'llm',
    toolName: 'gpt-4o-mini',
    latency: '1.2s',
    cost: '$0.005',
    description: 'LLM classifies intent from customer message to select correct tool flows.',
    inputJson: JSON.stringify({ model: 'gpt-4o-mini', prompt: 'Categorize query: "I want a refund..."' }, null, 2),
    outputJson: JSON.stringify({ category: 'REFUND', confidence: 0.99, escalate: false }, null, 2),
  },
  {
    id: '4',
    label: 'Check Refund Policy',
    type: 'tool',
    toolName: 'RefundPolicyChecker',
    latency: '0.4s',
    cost: '$0.002',
    description: 'Local business rules engine checks refund timeframe and conditions.',
    inputJson: JSON.stringify({ delivered_at: '2026-07-04T14:30:00Z', condition: 'damaged' }, null, 2),
    outputJson: JSON.stringify({ eligible: true, maxRefundAmount: 89.99, requiresManualReview: false }, null, 2),
  },
  {
    id: '5',
    label: 'Decide Refund Action',
    type: 'llm',
    toolName: 'gpt-4o',
    latency: '2.1s',
    cost: '$0.045',
    description: 'Decision model processes inputs to output final refund action approval.',
    inputJson: JSON.stringify({ model: 'gpt-4o', eligible: true, amount: 89.99, temperature: 0.1 }, null, 2),
    outputJson: JSON.stringify({
      action: 'APPROVE_REFUND',
      amount: 89.99,
      reason: 'Order arrived damaged within 30-day window. Auto-refund approved.',
    }, null, 2),
    divergedOutputJson: JSON.stringify({
      action: 'REJECT_REFUND',
      amount: 0,
      reason: 'Policy requires customer to submit photo proof. Set to manual review escalations.',
    }, null, 2),
  },
  {
    id: '6',
    label: 'Stripe Refund API',
    type: 'tool',
    toolName: 'StripeRefundGate',
    latency: '1.1s',
    cost: '$0.012',
    description: 'Executes transaction refund through payment gateway.',
    inputJson: JSON.stringify({ transactionId: 'ch_3Mv98L2eZvY', amount: 8999 }, null, 2),
    outputJson: JSON.stringify({ refundId: 're_3Mv98L2eZvY_1', status: 'succeeded', amountRefunded: 8999 }, null, 2),
    divergedOutputJson: JSON.stringify({ error: 'Refund skipped because approval action was negative.', status: 'skipped' }, null, 2),
  },
  {
    id: '7',
    label: 'Finish & Respond',
    type: 'finish',
    latency: '0.3s',
    cost: '$0.000',
    description: 'Returns finalized response code and customer-facing message.',
    inputJson: JSON.stringify({ status: 'completed' }, null, 2),
    outputJson: JSON.stringify({ status: 'completed', refundIssued: true, responseText: 'We have processed a full refund of $89.99.' }, null, 2),
    divergedOutputJson: JSON.stringify({ status: 'escalated', refundIssued: false, responseText: 'Your request requires manual review. Please upload order photo proof.' }, null, 2),
  },
];

export default function DemoSection() {
  // Scrubber simulator state — identical to original
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [simulateDivergence, setSimulateDivergence] = useState<boolean>(false);

  // Accumulated metrics
  const [accumulatedLatency, setAccumulatedLatency] = useState<number>(0);
  const [accumulatedCost, setAccumulatedCost] = useState<number>(0);
  const [savedTokensMsg, setSavedTokensMsg] = useState<string>('0% tokens cached');

  // Playback timer loop — identical to original
  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (isPlaying) {
      interval = setInterval(() => {
        setCurrentStep((prev) => {
          if (prev >= DEMO_STEPS.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [isPlaying]);

  // Dynamic values calculation — identical to original
  useEffect(() => {
    let lat = 0;
    let cost = 0;
    for (let i = 0; i <= currentStep; i++) {
      const step = DEMO_STEPS[i];
      lat += parseFloat(step.latency);
      cost += parseFloat(step.cost.replace('$', ''));
    }
    setAccumulatedLatency(parseFloat(lat.toFixed(1)));
    setAccumulatedCost(parseFloat(cost.toFixed(3)));

    if (currentStep > 0) {
      setSavedTokensMsg(`Local cache bypassed ${currentStep} LLM/tool calls — saving $${cost.toFixed(3)} API costs`);
    } else {
      setSavedTokensMsg('Drag slider or hit Play to scrub execution');
    }
  }, [currentStep]);

  const handleReset = () => {
    setCurrentStep(0);
    setIsPlaying(false);
  };

  const getStepIcon = (type: string) => {
    switch (type) {
      case 'start': return <Terminal className="w-4 h-4 text-blue-400" />;
      case 'db': return <Database className="w-4 h-4 text-purple-400" />;
      case 'llm': return <Cpu className="w-4 h-4 text-amber-400" />;
      case 'tool': return <Zap className="w-4 h-4 text-emerald-400" />;
      default: return <CheckCircle2 className="w-4 h-4 text-blue-400" />;
    }
  };

  const isDivergedAtStep = (index: number) => {
    return simulateDivergence && index >= 4;
  };

  return (
    <section className="relative py-32 overflow-hidden">
      {/* Top divider */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />
      
      {/* Background ambient */}
      <div className="absolute top-1/3 left-1/4 w-[600px] h-[600px] rounded-full bg-emerald-500/[0.02] blur-[150px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6">
        <SectionHeader
          badge="Interactive playground"
          badgeIcon={<Activity className="w-3.5 h-3.5 animate-pulse" />}
          badgeColor="green"
          title="Experience time-travel debugging"
          subtitle="Scrub through a customer refund agent run below. Toggle the divergence simulator to see how we track regression bugs in real-time."
        />

        {/* Interactive Debugger Widget */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.8, ease: [0.21, 0.45, 0.27, 0.9] }}
          className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch"
        >
          {/* Left Side Controls & Node Checklist */}
          <div className="lg:col-span-5 rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm p-6 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-white/[0.06] pb-4 mb-6">
                <div>
                  <h3 className="text-sm font-semibold text-white">Causal Nodes Checklist</h3>
                  <p className="text-[11px] text-white/30 mt-0.5">Execution flow for Customer Support Agent</p>
                </div>
                <span className="px-2.5 py-1 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 font-mono text-[10px] font-semibold">
                  Step {currentStep + 1} of {DEMO_STEPS.length}
                </span>
              </div>

              <div className="space-y-2">
                {DEMO_STEPS.map((step, idx) => {
                  const isActive = currentStep === idx;
                  const isCompleted = idx < currentStep;
                  const isDiverged = isDivergedAtStep(idx);

                  return (
                    <button
                      key={step.id}
                      onClick={() => {
                        setCurrentStep(idx);
                        setIsPlaying(false);
                      }}
                      className={`w-full flex items-center justify-between p-3 rounded-xl border text-left transition-all duration-200 text-xs font-medium cursor-pointer ${
                        isActive
                          ? isDiverged
                            ? 'border-red-500/40 bg-red-500/[0.08] text-white shadow-lg shadow-red-500/5'
                            : 'border-blue-500/40 bg-blue-500/[0.08] text-white shadow-lg shadow-blue-500/5'
                          : isDiverged
                            ? 'border-red-500/20 bg-red-500/[0.03] text-white/50 hover:text-white'
                            : 'border-white/[0.04] hover:border-white/[0.08] hover:bg-white/[0.02] text-white/50 hover:text-white'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-6 h-6 rounded-lg flex items-center justify-center border transition ${
                          isActive
                            ? isDiverged
                              ? 'bg-red-500/20 border-red-500/40'
                              : 'bg-blue-500/20 border-blue-500/40'
                            : isDiverged
                              ? 'bg-red-500/10 border-red-500/20'
                              : isCompleted
                                ? 'bg-emerald-500/10 border-emerald-500/20'
                                : 'bg-white/[0.03] border-white/[0.06]'
                        }`}>
                          {isCompleted && !isDiverged ? (
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                          ) : (
                            getStepIcon(step.type)
                          )}
                        </div>
                        <div className="flex flex-col">
                          <span className={`font-semibold ${isActive ? 'text-white' : ''}`}>
                            {step.label}
                          </span>
                          <span className="text-[10px] text-white/30 font-mono mt-0.5">
                            {step.toolName ? step.toolName : step.type.toUpperCase()}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {isDiverged && (
                          <span className="flex h-2 w-2 relative">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-75" />
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
                          </span>
                        )}
                        <span className="text-[10px] text-white/30 font-mono bg-white/[0.03] px-1.5 py-0.5 rounded border border-white/[0.04]">
                          {step.latency}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Controls */}
            <div className="mt-8 pt-4 border-t border-white/[0.06] space-y-4">
              {/* Divergence Toggle */}
              <div className="p-3 bg-white/[0.02] border border-white/[0.04] rounded-xl flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <AlertTriangle className={`w-4 h-4 ${simulateDivergence ? 'text-red-400 animate-pulse' : 'text-white/30'}`} />
                  <div className="flex flex-col">
                    <span className="text-xs font-semibold text-white">Simulate Divergence</span>
                    <span className="text-[9px] text-white/30">Mock a prompt drift in Step 5</span>
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={simulateDivergence}
                    onChange={(e) => setSimulateDivergence(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-white/[0.06] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white/30 after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-red-500/30 peer-checked:after:bg-red-400" />
                </label>
              </div>

              {/* Playback controls */}
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setIsPlaying(!isPlaying)}
                    className={`w-9 h-9 rounded-xl flex items-center justify-center cursor-pointer transition-all duration-200 ${
                      isPlaying
                        ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                        : 'bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-lg shadow-blue-500/20'
                    }`}
                  >
                    {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 fill-current" />}
                  </button>
                  <button
                    onClick={handleReset}
                    className="w-9 h-9 rounded-xl border border-white/[0.06] bg-white/[0.02] text-white/40 hover:text-white transition flex items-center justify-center cursor-pointer"
                    title="Reset Scrubber"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="grow">
                  <input
                    type="range"
                    min={0}
                    max={DEMO_STEPS.length - 1}
                    value={currentStep}
                    onChange={(e) => {
                      setCurrentStep(parseInt(e.target.value));
                      setIsPlaying(false);
                    }}
                    className="w-full accent-blue-500 cursor-pointer bg-white/[0.04] rounded-lg appearance-none h-1"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Right Side Inspect Payload Panel */}
          <div className="lg:col-span-7 rounded-2xl border border-white/[0.06] bg-[#08090f] flex flex-col justify-between overflow-hidden shadow-2xl relative">
            {/* Header */}
            <div className="bg-black/40 px-5 py-4 border-b border-white/[0.04] flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-white/[0.06]" />
                  <div className="w-2.5 h-2.5 rounded-full bg-white/[0.06]" />
                  <div className="w-2.5 h-2.5 rounded-full bg-white/[0.06]" />
                </div>
                <span className="text-xs font-semibold font-mono text-white/60">
                  node_inspector_payload.json
                </span>
              </div>

              <div className="flex items-center gap-2">
                {isDivergedAtStep(currentStep) ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold bg-red-500/10 border border-red-500/20 text-red-400 uppercase font-mono tracking-wider">
                    <AlertTriangle className="w-3 h-3" />
                    <span>Diverged</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 uppercase font-mono tracking-wider">
                    <ShieldCheck className="w-3 h-3" />
                    <span>Identical</span>
                  </span>
                )}
              </div>
            </div>

            {/* JSON Inspector */}
            <div className="p-5 flex-1 font-mono text-xs overflow-y-auto space-y-4 select-text">
              {/* Step Metadata */}
              <div>
                <span className="text-[10px] text-white/30 uppercase font-semibold tracking-wider font-sans block mb-2">Step Metadata</span>
                <div className="grid grid-cols-3 gap-3 p-3 bg-white/[0.02] border border-white/[0.04] rounded-xl text-left">
                  <div>
                    <span className="text-[9px] text-white/30 block">Latency</span>
                    <span className="text-xs font-bold text-white font-mono">{DEMO_STEPS[currentStep].latency}</span>
                  </div>
                  <div>
                    <span className="text-[9px] text-white/30 block">API Cost</span>
                    <span className="text-xs font-bold text-amber-400 font-mono">{DEMO_STEPS[currentStep].cost}</span>
                  </div>
                  <div>
                    <span className="text-[9px] text-white/30 block">Integrity Hash</span>
                    <span className="text-[11px] font-semibold text-purple-400 font-mono">
                      SHA:{Math.abs(7910283 + currentStep * 12093).toString(16).substring(0, 8)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Input JSON */}
                <div className="space-y-1.5 text-left">
                  <span className="text-[10px] text-white/30 uppercase font-semibold tracking-wider font-sans">Input parameters</span>
                  <pre className="p-3 bg-white/[0.02] border border-white/[0.04] rounded-xl text-[11px] text-white/40 max-h-56 overflow-y-auto overflow-x-auto whitespace-pre">
                    {DEMO_STEPS[currentStep].inputJson}
                  </pre>
                </div>

                {/* Output JSON */}
                <div className="space-y-1.5 text-left">
                  <span className="text-[10px] text-white/30 uppercase font-semibold tracking-wider font-sans flex items-center justify-between">
                    <span>Output payload</span>
                    {isDivergedAtStep(currentStep) && (
                      <span className="text-[9px] text-red-400 font-semibold animate-pulse uppercase">drift detected</span>
                    )}
                  </span>
                  <pre className={`p-3 border rounded-xl text-[11px] max-h-56 overflow-y-auto overflow-x-auto whitespace-pre transition ${
                    isDivergedAtStep(currentStep)
                      ? 'bg-red-500/[0.04] border-red-500/20 text-red-400'
                      : 'bg-white/[0.02] border-white/[0.04] text-emerald-400'
                  }`}>
                    {isDivergedAtStep(currentStep) && DEMO_STEPS[currentStep].divergedOutputJson
                      ? DEMO_STEPS[currentStep].divergedOutputJson
                      : DEMO_STEPS[currentStep].outputJson
                    }
                  </pre>
                </div>
              </div>

              {/* Divergence warning */}
              {isDivergedAtStep(currentStep) && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-3.5 bg-red-500/[0.06] border border-red-500/20 rounded-xl text-left flex items-start gap-2.5"
                >
                  <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5 animate-pulse" />
                  <div>
                    <h4 className="text-xs font-bold text-white">LLM Divergence Detected on Decisional Node</h4>
                    <p className="text-[10px] text-white/40 mt-1 leading-relaxed">
                      Expected approval hash diverges from live baseline runtime. Output values shifted action from <b className="text-white/60">&quot;APPROVE_REFUND&quot;</b> to <b className="text-white/60">&quot;REJECT_REFUND&quot;</b> due to strict local validation checks on photos. Replayer stopped code execution.
                    </p>
                  </div>
                </motion.div>
              )}

              {/* Causal description */}
              <div className="p-3 bg-white/[0.015] border border-white/[0.04] rounded-xl text-left">
                <span className="text-[10px] text-white/30 uppercase font-semibold tracking-wider font-sans block mb-1.5">Causal Description</span>
                <p className="text-xs text-white/50 leading-relaxed">
                  {DEMO_STEPS[currentStep].description}
                </p>
              </div>
            </div>

            {/* Bottom statistics */}
            <div className="bg-black/40 px-5 py-3 border-t border-white/[0.04] flex flex-col md:flex-row justify-between items-start md:items-center gap-2.5">
              <span className="text-[10px] font-mono text-white/30">
                {savedTokensMsg}
              </span>

              <div className="flex items-center gap-4 text-xs font-mono">
                <div>
                  <span className="text-white/30">Latency: </span>
                  <span className="text-white font-bold">{accumulatedLatency}s</span>
                </div>
                <div className="w-px h-3 bg-white/[0.06]" />
                <div>
                  <span className="text-white/30">Cost: </span>
                  <span className="text-amber-400 font-bold">${accumulatedCost.toFixed(3)}</span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
