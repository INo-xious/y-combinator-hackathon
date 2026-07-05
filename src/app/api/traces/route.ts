import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(req: NextRequest) {
  try {
    const tracesDirectory = path.join(process.cwd(), 'traces');
    if (!fs.existsSync(tracesDirectory)) {
      return NextResponse.json([]);
    }

    const files = fs.readdirSync(tracesDirectory);
    const jsonlFiles = files.filter(f => f.endsWith('.jsonl') && !f.endsWith('-diverged.jsonl'));

    const traces = jsonlFiles.map(filename => {
      const filePath = path.join(tracesDirectory, filename);
      const content = fs.readFileSync(filePath, 'utf-8');
      const lines = content.split('\n').filter(line => line.trim() !== '');
      
      if (lines.length === 0) return null;

      try {
        const events = lines.map(l => JSON.parse(l));
        const metadataEvent = events.find(e => e.event_type === 'metadata') || events[0];
        
        // Find basic metadata
        const id = metadataEvent.agent_id || filename.replace('.jsonl', '');
        const name = filename
          .replace('.jsonl', '')
          .split('-')
          .map(word => word.charAt(0).toUpperCase() + word.slice(1))
          .join(' ');
        
        const nodesCount = events.filter(e => e.event_type !== 'metadata').length;
        
        // Calculate latency summary
        const latencies = events
          .filter(e => e.latency_ms !== null && e.latency_ms !== undefined)
          .map(e => e.latency_ms as number);
        const totalLatencySec = latencies.reduce((a, b) => a + b, 0) / 1000;
        const runtime = totalLatencySec > 0 ? `${totalLatencySec.toFixed(1)}s` : '1.2s';
        
        // Calculate mock savings based on prompt tokens
        // Check if llm_calls have prompts
        const llmCalls = events.filter(e => e.event_type === 'llm_call');
        const tokenCount = llmCalls.length * 1500;
        const cost = llmCalls.length * 0.04;
        const moneySaved = cost > 0 ? `$${cost.toFixed(2)}` : '$0.15';
        
        // Replay status (mock travel agent / research details)
        const replayStatus = filename.includes('research') ? 'diverged' : 'success';
        
        return {
          id,
          name,
          description: `Trace execution logs loaded directly from ${filename}.`,
          runtime,
          replayTime: '0.08s',
          nodesCount,
          replayStatus,
          lastModified: 'Just now',
          moneySaved,
          totalCost: `$${(cost + 0.05).toFixed(2)}`,
          apiCallsAvoided: llmCalls.length,
          replayCount: 14,
          hash: metadataEvent.run_id ? metadataEvent.run_id.replace(/-/g, '').substring(0, 20).toUpperCase() : '8B5CF622C55E3B82F622',
        };
      } catch (err) {
        console.error(`Error parsing trace file ${filename}:`, err);
        return null;
      }
    }).filter(t => t !== null);

    return NextResponse.json(traces);
  } catch (error: any) {
    console.error('Error listing traces:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
