'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from '@/components/Sidebar';
import Navbar from '@/components/Navbar';
import CommandPalette from '@/components/CommandPalette';
import DashboardView from '@/components/DashboardView';
import LandingView from '@/components/LandingView';
import TraceExplorerView from '@/components/TraceExplorerView';
import ReplayViewer from '@/components/ReplayViewer';
import NodeInspector from '@/components/NodeInspector';
import CompareRunsView from '@/components/CompareRunsView';
import SettingsView from '@/components/SettingsView';
import { MOCK_TRACES, Trace, TraceNode } from '@/data/traces';

export default function Page() {
  const [activeView, setActiveView] = useState<string>('landing');
  const [selectedTraceId, setSelectedTraceId] = useState<string>('customer-support');
  const [timelineIndex, setTimelineIndex] = useState<number>(0);
  const [isReplaying, setIsReplaying] = useState<boolean>(false);
  const [redactionEnabled, setRedactionEnabled] = useState<boolean>(true);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState<boolean>(false);
  const [selectedNode, setSelectedNode] = useState<TraceNode | null>(null);

  // Dynamic state loaded from filesystem Python backend
  const [traces, setTraces] = useState<Trace[]>(MOCK_TRACES);
  const [activeTrace, setActiveTrace] = useState<Trace>(MOCK_TRACES[0]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isRecordingLive, setIsRecordingLive] = useState<boolean>(false);

  // Divergence check status
  const [divergenceReport, setDivergenceReport] = useState<{
    sequenceIndex: number;
    nodeId: string;
    expectedHash: string;
    actualHash: string;
    expectedPayload: unknown;
    actualPayload: unknown;
  } | null>(null);

  // Fetch list of traces on mount
  const fetchTracesList = async () => {
    try {
      const response = await fetch('/api/traces');
      if (response.ok) {
        const data = await response.json();
        if (data && data.length > 0) {
          setTraces(data);
        }
      }
    } catch (error) {
      console.error('Failed to fetch traces list from backend:', error);
    }
  };

  useEffect(() => {
    setTimeout(() => {
      fetchTracesList();
    }, 0);
  }, []);

  // Fetch trace details when active trace selection changes
  const fetchTraceDetails = async (id: string) => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/traces/${id}`);
      if (response.ok) {
        const data = await response.json();
        if (data) {
          setActiveTrace(data);
          // Set initial node selected
          if (data.nodes && data.nodes.length > 0) {
            setSelectedNode(data.nodes[0]);
          }
          // Clear any historical divergence reports on switch
          setDivergenceReport(null);
          setTimelineIndex(0);
          setIsReplaying(false);
          setIsLoading(false);
          return;
        }
      }
    } catch (error) {
      console.error(`Failed to fetch trace details for ${id}:`, error);
    }

    // Fallback to static mock trace if backend API is not responding
    const fallbackTrace = MOCK_TRACES.find(t => t.id === id) || MOCK_TRACES[0];
    setActiveTrace(fallbackTrace);
    if (fallbackTrace.nodes && fallbackTrace.nodes.length > 0) {
      setSelectedNode(fallbackTrace.nodes[0]);
    }
    setDivergenceReport(null);
    setTimelineIndex(0);
    setIsReplaying(false);
    setIsLoading(false);
  };

  useEffect(() => {
    setTimeout(() => {
      fetchTraceDetails(selectedTraceId);
    }, 0);
  }, [selectedTraceId]);

  // POST Request to trigger Python replayer validate commands
  const triggerReplayPlayback = useCallback(async () => {
    if (isReplaying) {
      setIsReplaying(false);
      return;
    }

    // Reset scrubber
    setTimelineIndex(0);
    setDivergenceReport(null);

    try {
      const response = await fetch(`/api/traces/${selectedTraceId}/replay`, {
        method: 'POST',
      });
      if (response.ok) {
        const result = await response.json();
        if (result.status === 'diverged') {
          setDivergenceReport({
            sequenceIndex: result.sequenceIndex,
            nodeId: result.nodeId,
            expectedHash: result.expectedHash,
            actualHash: result.actualHash,
            expectedPayload: result.expectedPayload,
            actualPayload: result.actualPayload,
          });
        }
      }
    } catch (err) {
      console.error('Failed to trigger python replay validation:', err);
    }

    // Start playback animation
    setIsReplaying(true);
  }, [isReplaying, selectedTraceId]);

  // Hook to watch timelineIndex during playback to detect divergence step
  useEffect(() => {
    if (isReplaying && divergenceReport && timelineIndex === divergenceReport.sequenceIndex) {
      // Divergence step reached! Stop playback and flash red
      // Automatically navigate to split screen view to compare runs
      setTimeout(() => {
        setIsReplaying(false);
        setActiveView('compare');
      }, 1200);
    }
  }, [timelineIndex, isReplaying, divergenceReport]);

  // Global keyboard shortcuts
  useEffect(() => {
    const handleGlobalShortcuts = (e: KeyboardEvent) => {
      if (e.code === 'Space' && activeView === 'replay' && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'SELECT' && document.activeElement?.tagName !== 'TEXTAREA') {
        e.preventDefault();
        triggerReplayPlayback();
      }
      if (activeView === 'replay' && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'SELECT') {
        if (e.key === 'ArrowRight') {
          e.preventDefault();
          setIsReplaying(false);
          setTimelineIndex(prev => Math.min(activeTrace.nodes.length - 1, prev + 1));
        }
        if (e.key === 'ArrowLeft') {
          e.preventDefault();
          setIsReplaying(false);
          setTimelineIndex(prev => Math.max(0, prev - 1));
        }
      }
    };
    window.addEventListener('keydown', handleGlobalShortcuts);
    return () => window.removeEventListener('keydown', handleGlobalShortcuts);
  }, [activeView, isReplaying, activeTrace.nodes.length, divergenceReport, triggerReplayPlayback]);

  const handleSelectTrace = (traceId: string) => {
    setSelectedTraceId(traceId);
  };

  // POST Request to trigger Python live recorder run scripts
  const handleTriggerLiveRecording = async () => {
    setIsRecordingLive(true);
    setIsReplaying(false);
    
    try {
      const response = await fetch('/api/traces/record', {
        method: 'POST',
      });
      if (response.ok) {
        // Refresh list and reload details
        await fetchTracesList();
        setSelectedTraceId('customer-support');
        await fetchTraceDetails('customer-support');
      }
    } catch (err) {
      console.error('Failed to run live agent recorder:', err);
    } finally {
      setIsRecordingLive(false);
    }
  };

  const handleReplayFromHere = (nodeId: string) => {
    const index = activeTrace.nodes.findIndex(n => n.id === nodeId);
    if (index !== -1) {
      setTimelineIndex(index);
      setIsReplaying(true);
    }
  };

  const renderActiveView = () => {
    if (isLoading) {
      return (
        <div className="flex h-[calc(100vh-4rem)] items-center justify-center bg-brand-bg text-brand-secondary text-sm">
          <div className="text-center space-y-3">
            <div className="w-10 h-10 border-2 border-brand-primary border-t-transparent rounded-full animate-spin mx-auto" />
            <span>Loading trace causal DAG...</span>
          </div>
        </div>
      );
    }

    switch (activeView) {
      case 'landing':
        return (
          <LandingView 
            onNavigate={setActiveView}
          />
        );
      case 'dashboard':
        return (
          <DashboardView 
            onNavigate={setActiveView}
            onSelectTrace={handleSelectTrace}
            redactionEnabled={redactionEnabled}
            onToggleRedaction={() => setRedactionEnabled(!redactionEnabled)}
            traces={traces}
          />
        );
      case 'explorer':
        return (
          <TraceExplorerView 
            onSelectTrace={handleSelectTrace}
            onNavigate={setActiveView}
            traces={traces}
          />
        );
      case 'replay':
        return (
          <div className="flex-1 flex overflow-hidden">
            <ReplayViewer 
              trace={activeTrace}
              selectedNode={selectedNode}
              onSelectNode={setSelectedNode}
              timelineIndex={timelineIndex}
              setTimelineIndex={setTimelineIndex}
              isReplaying={isReplaying}
              setIsReplaying={setIsReplaying}
            />
            <NodeInspector 
              node={selectedNode}
              onReplayFromHere={handleReplayFromHere}
            />
          </div>
        );
      case 'compare':
        return (
          <CompareRunsView 
            onSelectTrace={handleSelectTrace}
            onNavigate={setActiveView}
            traces={traces}
          />
        );
      case 'settings':
        return (
          <SettingsView 
            redactionEnabled={redactionEnabled}
            onToggleRedaction={() => setRedactionEnabled(!redactionEnabled)}
          />
        );
      default:
        return (
          <DashboardView 
            onNavigate={setActiveView}
            onSelectTrace={handleSelectTrace}
            redactionEnabled={redactionEnabled}
            onToggleRedaction={() => setRedactionEnabled(!redactionEnabled)}
            traces={traces}
          />
        );
    }
  };

  const isLanding = activeView === 'landing';

  return (
    <div className={`flex bg-brand-bg text-brand-text ${isLanding ? 'min-h-screen' : 'h-screen overflow-hidden'}`}>
      {/* Sidebar Panel Navigation */}
      {!isLanding && (
        <Sidebar 
          activeView={activeView}
          onNavigate={setActiveView}
          isRecording={isRecordingLive || (selectedTraceId === 'customer-support' && isReplaying)}
        />
      )}

      {/* Primary Workspace Window */}
      <div className={`flex-1 flex flex-col ${isLanding ? '' : 'overflow-hidden'}`}>
        {/* Top Navbar */}
        {!isLanding && (
          <Navbar 
            activeView={activeView}
            activeTrace={activeTrace}
            onOpenCommandPalette={() => setCommandPaletteOpen(true)}
            redactionEnabled={redactionEnabled}
          />
        )}

        {/* View Frame */}
        <main className={`flex-1 bg-brand-bg relative ${isLanding ? '' : 'overflow-hidden'}`}>
          <AnimatePresence mode="wait">
            <motion.div
              key={activeView + (isLoading ? '-loading' : '-ready')}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.15 }}
              className={isLanding ? "w-full" : "h-full w-full flex flex-col overflow-y-auto"}
            >
              {renderActiveView()}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      {/* Command Palette Overlay */}
      <AnimatePresence>
        {commandPaletteOpen && (
          <CommandPalette 
            isOpen={commandPaletteOpen}
            onClose={() => setCommandPaletteOpen(false)}
            onNavigate={setActiveView}
            onSelectTrace={handleSelectTrace}
            onTriggerReplay={triggerReplayPlayback}
            traces={traces}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
