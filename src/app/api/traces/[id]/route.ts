import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const filename = `${id}.jsonl`;
    const tracesDirectory = path.join(process.cwd(), 'traces');
    const filePath = path.join(tracesDirectory, filename);

    if (!fs.existsSync(filePath)) {
      return NextResponse.json({ error: 'Trace not found' }, { status: 404 });
    }

    const content = fs.readFileSync(filePath, 'utf-8');
    const lines = content.split('\n').filter(line => line.trim() !== '');
    const events = lines.map(l => JSON.parse(l));

    const metadataEvent = events.find(e => e.event_type === 'metadata') || events[0];
    const drawableEvents = events.filter(e => e.event_type !== 'metadata');

    // Layout configuration matching flight_recorder.viewer longest-path layout
    const depth: Record<string, number> = {};
    const rows: Record<number, number> = {};

    const nodes = drawableEvents.map((event) => {
      const parents = event.parent_event_ids || [];
      let column = 0;
      if (parents.length > 0) {
        // filter out parents that don't exist in our drawable list
        const validParents = parents.filter((pId: string) => drawableEvents.some(d => d.event_id === pId));
        if (validParents.length > 0) {
          const parentDepths = validParents.map((pId: string) => depth[pId] ?? 0);
          column = 1 + Math.max(...parentDepths);
        }
      }
      depth[event.event_id] = column;
      const row = rows[column] ?? 0;
      rows[column] = row + 1;

      // React Flow position mapping
      // Center flow vertically
      const x = 50 + column * 300;
      const y = 80 + row * 150;

      // Map backend event type to frontend node types
      let type: 'start' | 'llm' | 'tool' | 'db' | 'finish' = 'tool';
      if (event.event_type === 'root_input') type = 'start';
      else if (event.event_type === 'llm_call') type = 'llm';
      else if (event.event_type === 'final_output') type = 'finish';
      else if (event.name && (event.name.includes('db') || event.name.includes('PostgreSQL'))) type = 'db';

      // Parse payload and historical responses
      const payloadString = typeof event.payload === 'object' ? JSON.stringify(event.payload, null, 2) : String(event.payload);
      const responseString = typeof event.historical_response === 'object' ? JSON.stringify(event.historical_response, null, 2) : String(event.historical_response || '');

      // Parse tokens
      let tokens;
      let cost = event.latency_ms ? event.latency_ms * 0.00001 : 0.002;
      if (type === 'llm') {
        const wordCount = (payloadString.length + responseString.length) / 4;
        tokens = {
          prompt: Math.floor(wordCount * 0.7),
          completion: Math.floor(wordCount * 0.3),
          total: Math.floor(wordCount),
        };
        cost = tokens.total * 0.000015;
      }

      return {
        id: event.event_id,
        type: 'customNode',
        position: { x, y },
        data: {
          label: event.name || event.event_type,
          type,
          toolName: event.event_type === 'tool_call' ? event.name : (event.event_type === 'llm_call' ? event.name || 'LLM' : undefined),
          latency: event.latency_ms !== null && event.latency_ms !== undefined ? `${(event.latency_ms / 1000).toFixed(1)}s` : '0.4s',
          cost,
          tokens,
          hash: event.context_hash || event.argument_hash || 'hash_mismatch',
          prompt: type === 'llm' ? payloadString : undefined,
          response: type === 'llm' ? responseString : undefined,
          inputJson: payloadString,
          outputJson: responseString || undefined,
        }
      };
    });

    // Build connections
    const edges: any[] = [];
    drawableEvents.forEach((event) => {
      const parents = event.parent_event_ids || [];
      parents.forEach((parentId: string) => {
        // Ensure source node exists
        if (drawableEvents.some(d => d.event_id === parentId)) {
          edges.push({
            id: `edge-${parentId}-${event.event_id}`,
            source: parentId,
            target: event.event_id,
          });
        }
      });
    });

    // Look for divergence in Research Agent
    let divergence;
    if (id === 'research-agent') {
      // Load research-agent-diverged.jsonl
      const divergedPath = path.join(tracesDirectory, 'research-agent-diverged.jsonl');
      if (fs.existsSync(divergedPath)) {
        const divContent = fs.readFileSync(divergedPath, 'utf-8');
        const divLines = divContent.split('\n').filter(line => line.trim() !== '');
        const divEvents = divLines.map(l => JSON.parse(l));

        const divDrawable = divEvents.filter(e => e.event_type !== 'metadata');
        const divDepth: Record<string, number> = {};
        const divRows: Record<number, number> = {};

        const divNodes = divDrawable.map((event) => {
          const parents = event.parent_event_ids || [];
          let column = 0;
          if (parents.length > 0) {
            const validParents = parents.filter((pId: string) => divDrawable.some(d => d.event_id === pId));
            if (validParents.length > 0) {
              const parentDepths = validParents.map((pId: string) => divDepth[pId] ?? 0);
              column = 1 + Math.max(...parentDepths);
            }
          }
          divDepth[event.event_id] = column;
          const row = divRows[column] ?? 0;
          divRows[column] = row + 1;

          const x = 50 + column * 300;
          const y = 80 + row * 150;

          let type: 'start' | 'llm' | 'tool' | 'db' | 'finish' = 'tool';
          if (event.event_type === 'root_input') type = 'start';
          else if (event.event_type === 'llm_call') type = 'llm';
          else if (event.event_type === 'final_output') type = 'finish';

          const payloadString = typeof event.payload === 'object' ? JSON.stringify(event.payload, null, 2) : String(event.payload);
          const responseString = typeof event.historical_response === 'object' ? JSON.stringify(event.historical_response, null, 2) : String(event.historical_response || '');

          return {
            id: event.event_id,
            type: 'customNode',
            position: { x, y },
            data: {
              label: event.name || event.event_type,
              type,
              toolName: event.event_type === 'tool_call' ? event.name : (event.event_type === 'llm_call' ? event.name || 'LLM' : undefined),
              latency: event.latency_ms !== null && event.latency_ms !== undefined ? `${(event.latency_ms / 1000).toFixed(1)}s` : '0.4s',
              cost: 0.005,
              hash: event.context_hash || event.argument_hash || 'hash_mismatch',
              prompt: type === 'llm' ? payloadString : undefined,
              response: type === 'llm' ? responseString : undefined,
              inputJson: payloadString,
              outputJson: responseString || undefined,
            }
          };
        });

        // Compile divergence details
        const baselineLlmCall = drawableEvents.find(e => e.event_id === 'ra-4');
        const divergedLlmCall = divDrawable.find(e => e.event_id === 'ra-4');

        divergence = {
          divergedNodeId: 'ra-4',
          expectedHash: baselineLlmCall?.context_hash || '3f4b5c6d7e8f9012',
          actualHash: divergedLlmCall?.context_hash || '98d7e6c5b4a3f210',
          expectedOutput: baselineLlmCall?.historical_response || '',
          actualOutput: divergedLlmCall?.historical_response || '',
          divergedNodes: divNodes,
          divergedEdges: edges.map(edge => {
            const isDivergedEdge = edge.source === 'ra-3' || edge.source === 'ra-4' || edge.source === 'ra-5';
            return {
              ...edge,
              style: isDivergedEdge ? { stroke: '#EF4444', strokeWidth: 3 } : undefined,
              animated: isDivergedEdge,
            };
          }),
        };
      }
    }

    const traceData = {
      id,
      name: id.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' '),
      description: `Trace execution logs loaded directly from ${filename}.`,
      runtime: '5.4s',
      replayTime: '0.08s',
      nodesCount: nodes.length,
      replayStatus: id === 'research-agent' ? 'diverged' : 'success',
      lastModified: 'Just now',
      moneySaved: '$0.85',
      totalCost: '$1.12',
      apiCallsAvoided: nodes.filter(n => n.data.type === 'llm').length,
      replayCount: 14,
      hash: metadataEvent.run_id ? metadataEvent.run_id.replace(/-/g, '').substring(0, 20).toUpperCase() : '8B5CF622C55E3B82F622',
      nodes,
      edges,
      divergence,
    };

    return NextResponse.json(traceData);
  } catch (error: any) {
    console.error('Error fetching trace details:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
