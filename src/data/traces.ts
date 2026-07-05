export interface TraceNodeData {
  label: string;
  type: 'start' | 'llm' | 'tool' | 'db' | 'logic' | 'finish';
  toolName?: string;
  latency: string;
  cost: number;
  tokens?: {
    prompt: number;
    completion: number;
    total: number;
  };
  hash: string;
  prompt?: string;
  response?: string;
  inputJson?: string;
  outputJson?: string;
}

export interface TraceNode {
  id: string;
  type: string;
  data: TraceNodeData;
  position: { x: number; y: number };
}

export interface TraceEdge {
  id: string;
  source: string;
  target: string;
  animated?: boolean;
  style?: React.CSSProperties;
}

export interface Trace {
  id: string;
  name: string;
  description: string;
  runtime: string;
  replayTime: string;
  nodesCount: number;
  replayStatus: 'success' | 'diverged' | 'recording';
  lastModified: string;
  moneySaved: string;
  totalCost: string;
  apiCallsAvoided: number;
  replayCount: number;
  hash: string;
  nodes: TraceNode[];
  edges: TraceEdge[];
  divergence?: {
    divergedNodeId: string;
    expectedHash: string;
    actualHash: string;
    expectedOutput: string;
    actualOutput: string;
    divergedNodes: TraceNode[];
    divergedEdges: TraceEdge[];
  };
}

export const MOCK_TRACES: Trace[] = [
  {
    id: 'customer-support',
    name: 'Customer Support Agent',
    description: 'Handles product refunds and categorizes support tickets using CRM tools.',
    runtime: '5.4s',
    replayTime: '0.08s',
    nodesCount: 7,
    replayStatus: 'success',
    lastModified: '2 mins ago',
    moneySaved: '$0.12',
    totalCost: '$0.15',
    apiCallsAvoided: 3,
    replayCount: 14,
    hash: '8B5CF622C55E3B82F622',
    nodes: [
      {
        id: '1',
        type: 'customNode',
        position: { x: 250, y: 50 },
        data: {
          label: 'Start Execution',
          type: 'start',
          latency: '0.0s',
          cost: 0,
          hash: '6a0c01a2f64d0a1b',
          inputJson: JSON.stringify({ userId: 'usr_9812', message: 'I want a refund for my order #10023. It arrived damaged.' }, null, 2)
        }
      },
      {
        id: '2',
        type: 'customNode',
        position: { x: 250, y: 150 },
        data: {
          label: 'Fetch Order details',
          type: 'db',
          toolName: 'PostgreSQL - orders_db',
          latency: '0.3s',
          cost: 0.001,
          hash: 'e81a38b28f117c2a',
          inputJson: JSON.stringify({ orderId: '10023', fields: ['status', 'amount', 'delivered_at'] }, null, 2),
          outputJson: JSON.stringify({ status: 'delivered', amount: 89.99, delivered_at: '2026-07-04T14:30:00Z', items: ['Wireless Earbuds Pro'] }, null, 2)
        }
      },
      {
        id: '3',
        type: 'customNode',
        position: { x: 250, y: 250 },
        data: {
          label: 'Intent Classification',
          type: 'llm',
          toolName: 'gpt-4o-mini',
          latency: '1.2s',
          cost: 0.005,
          tokens: { prompt: 450, completion: 42, total: 492 },
          hash: '5f9e8a716c52bb3d',
          prompt: 'Categorize the user inquiry: "I want a refund for my order #10023. It arrived damaged." Available categories: REFUND, STATUS_CHECK, GENERAL_HELP.',
          response: '{\n  "category": "REFUND",\n  "confidence": 0.99\n}',
          inputJson: JSON.stringify({ model: 'gpt-4o-mini', temperature: 0 }, null, 2),
          outputJson: JSON.stringify({ category: 'REFUND', confidence: 0.99 }, null, 2)
        }
      },
      {
        id: '4',
        type: 'customNode',
        position: { x: 250, y: 350 },
        data: {
          label: 'Check Refund Policy',
          type: 'tool',
          toolName: 'RefundPolicyChecker',
          latency: '0.4s',
          cost: 0.002,
          hash: 'a9b23c71de24f5a1',
          inputJson: JSON.stringify({ delivered_at: '2026-07-04T14:30:00Z', current_time: '2026-07-05T11:24:00Z', condition: 'damaged' }, null, 2),
          outputJson: JSON.stringify({ eligible: true, maxRefundAmount: 89.99, requiresManualReview: false }, null, 2)
        }
      },
      {
        id: '5',
        type: 'customNode',
        position: { x: 250, y: 450 },
        data: {
          label: 'Decide Refund',
          type: 'llm',
          toolName: 'gpt-4o',
          latency: '2.1s',
          cost: 0.045,
          tokens: { prompt: 1200, completion: 150, total: 1350 },
          hash: 'c82b1928fa2d44ee',
          prompt: 'Decide whether to issue an auto-refund for Order #10023. Eligible: true, amount: 89.99. User reports it arrived damaged.',
          response: '{\n  "action": "APPROVE_REFUND",\n  "amount": 89.99,\n  "reason": "Order was received in damaged condition and is within the 30-day return window. No manual verification required.",\n  "notificationMessage": "We are sorry to hear your order arrived damaged. We have processed a full refund of $89.99 to your original payment method."\n}',
          inputJson: JSON.stringify({ model: 'gpt-4o', temperature: 0.1 }, null, 2),
          outputJson: JSON.stringify({ action: 'APPROVE_REFUND', amount: 89.99, reason: 'Order was received in damaged condition...' }, null, 2)
        }
      },
      {
        id: '6',
        type: 'customNode',
        position: { x: 250, y: 550 },
        data: {
          label: 'Stripe Refund API',
          type: 'tool',
          toolName: 'StripeRefundGate',
          latency: '1.1s',
          cost: 0.012,
          hash: '4e33912da8a912bb',
          inputJson: JSON.stringify({ transactionId: 'ch_3Mv98L2eZvYKY', amount: 8999, currency: 'usd' }, null, 2),
          outputJson: JSON.stringify({ refundId: 're_3Mv98L2eZvYKY_1', status: 'succeeded', amountRefunded: 8999 }, null, 2)
        }
      },
      {
        id: '7',
        type: 'customNode',
        position: { x: 250, y: 650 },
        data: {
          label: 'Finish & Respond',
          type: 'finish',
          latency: '0.3s',
          cost: 0,
          hash: '8f729dbb1c34a2e5',
          outputJson: JSON.stringify({ status: 'completed', refundIssued: true, refundId: 're_3Mv98L2eZvYKY_1', responseText: 'We have processed a full refund of $89.99.' }, null, 2)
        }
      }
    ],
    edges: [
      { id: 'e1-2', source: '1', target: '2' },
      { id: 'e2-3', source: '2', target: '3' },
      { id: 'e3-4', source: '3', target: '4' },
      { id: 'e4-5', source: '4', target: '5' },
      { id: 'e5-6', source: '5', target: '6' },
      { id: 'e6-7', source: '6', target: '7' }
    ]
  },
  {
    id: 'travel-planner',
    name: 'Travel Planner Agent',
    description: 'Finds flights and hotels, builds standard itineraries, and maps routes.',
    runtime: '8.2s',
    replayTime: '0.15s',
    nodesCount: 6,
    replayStatus: 'success',
    lastModified: '15 mins ago',
    moneySaved: '$0.34',
    totalCost: '$0.42',
    apiCallsAvoided: 4,
    replayCount: 8,
    hash: 'F59E0B22C55E3B82F622',
    nodes: [
      {
        id: 't1',
        type: 'customNode',
        position: { x: 250, y: 50 },
        data: {
          label: 'Start Travel Query',
          type: 'start',
          latency: '0.0s',
          cost: 0,
          hash: '09a8b71d2b3c4e5f',
          inputJson: JSON.stringify({ destination: 'Tokyo', durationDays: 3, budget: 1500 }, null, 2)
        }
      },
      {
        id: 't2',
        type: 'customNode',
        position: { x: 250, y: 150 },
        data: {
          label: 'Find Flight API',
          type: 'tool',
          toolName: 'AmadeusFlightSearch',
          latency: '2.3s',
          cost: 0.02,
          hash: 'bc72e18d6e9f2a81',
          inputJson: JSON.stringify({ origin: 'LAX', destination: 'NRT', date: '2026-10-10' }, null, 2),
          outputJson: JSON.stringify({ options: [{ airline: 'ANA', price: 850, departure: '11:45 AM' }, { airline: 'JAL', price: 920, departure: '1:15 PM' }] }, null, 2)
        }
      },
      {
        id: 't3',
        type: 'customNode',
        position: { x: 250, y: 250 },
        data: {
          label: 'Find Hotel API',
          type: 'tool',
          toolName: 'HotelsProAPI',
          latency: '1.9s',
          cost: 0.015,
          hash: '22e3bc78fa12bb4d',
          inputJson: JSON.stringify({ destination: 'Tokyo', ratingMin: 4, checkIn: '2026-10-10', nights: 3 }, null, 2),
          outputJson: JSON.stringify({ results: [{ name: 'Shibuya Stream Hotel', pricePerNight: 180, rating: 4.6 }, { name: 'Hotel Gracery Shinjuku', pricePerNight: 140, rating: 4.4 }] }, null, 2)
        }
      },
      {
        id: 't4',
        type: 'customNode',
        position: { x: 250, y: 350 },
        data: {
          label: 'Fetch Tokyo Weather',
          type: 'tool',
          toolName: 'OpenWeatherAPI',
          latency: '0.8s',
          cost: 0.005,
          hash: '45efd981ba23cdee',
          inputJson: JSON.stringify({ city: 'Tokyo', month: 'October' }, null, 2),
          outputJson: JSON.stringify({ averageTemp: '18C', conditions: 'Mostly sunny', rainProbability: '12%' }, null, 2)
        }
      },
      {
        id: 't5',
        type: 'customNode',
        position: { x: 250, y: 450 },
        data: {
          label: 'Generate Itinerary',
          type: 'llm',
          toolName: 'gpt-4o',
          latency: '2.8s',
          cost: 0.052,
          tokens: { prompt: 2100, completion: 450, total: 2550 },
          hash: 'f93d3bb7e82ac110',
          prompt: 'Create a 3-day itinerary for Tokyo. Budget: $1500. Hotel: Hotel Gracery Shinjuku ($140/night). Flight: ANA ($850). Weather: 18C, Mostly sunny. Outline morning, afternoon, evening activities.',
          response: '### Day 1: Modern Tokyo (Shinjuku & Shibuya)\n* **Morning**: Check in at Hotel Gracery. Stroll through Shinjuku Gyoen National Garden.\n* **Afternoon**: Head to Shibuya. Cross Shibuya Crossing and shop at Shibuya 109.\n* **Evening**: Dinner at Omoide Yokocho for yakitori skewers.\n\n### Day 2: Traditional Tokyo\n* **Morning**: Visit Senso-ji Temple in Asakusa.\n* **Afternoon**: Cruise down Sumida River to Odaiba.\n* **Evening**: Explore Odaiba Seaside Park and dinner overlooking Rainbow Bridge.\n\n### Day 3: Pop Culture & Shopping\n* **Morning**: Anime shopping in Akihabara.\n* **Afternoon**: Visit Harajuku and Takeshita Street.\n* **Evening**: Observation deck at Tokyo Metropolitan Government Building.',
          inputJson: JSON.stringify({ model: 'gpt-4o', temperature: 0.5 }, null, 2),
          outputJson: JSON.stringify({ itineraryLength: 3, outline: '3-day itinerary ready' }, null, 2)
        }
      },
      {
        id: 't6',
        type: 'customNode',
        position: { x: 250, y: 550 },
        data: {
          label: 'Finish Itinerary',
          type: 'finish',
          latency: '0.4s',
          cost: 0,
          hash: 'fa238c92e10db4e5',
          outputJson: JSON.stringify({ status: 'success', totalPrice: 1410, itineraryGenerated: true }, null, 2)
        }
      }
    ],
    edges: [
      { id: 'et1-2', source: 't1', target: 't2' },
      { id: 'et2-3', source: 't2', target: 't3' },
      { id: 'et3-4', source: 't3', target: 't4' },
      { id: 'et4-5', source: 't4', target: 't5' },
      { id: 'et5-6', source: 't5', target: 't6' }
    ]
  },
  {
    id: 'research-agent',
    name: 'Research Agent',
    description: 'Searches the web, extracts metadata, compiles bibliography, and synthesizes report. Diverges on run.',
    runtime: '12.6s',
    replayTime: '0.22s',
    nodesCount: 6,
    replayStatus: 'diverged',
    lastModified: 'Just now',
    moneySaved: '$0.85',
    totalCost: '$1.12',
    apiCallsAvoided: 5,
    replayCount: 22,
    hash: 'EF444422C55E3B82F622',
    nodes: [
      {
        id: 'r1',
        type: 'customNode',
        position: { x: 250, y: 50 },
        data: {
          label: 'Start Research',
          type: 'start',
          latency: '0.0s',
          cost: 0,
          hash: 'a1b2c3d4e5f60718',
          inputJson: JSON.stringify({ query: 'LLM context caching performance benefits', maxSources: 3 }, null, 2)
        }
      },
      {
        id: 'r2',
        type: 'customNode',
        position: { x: 250, y: 150 },
        data: {
          label: 'Google Web Search',
          type: 'tool',
          toolName: 'SerperAPI',
          latency: '1.2s',
          cost: 0.005,
          hash: 'e3f4a5b6c7d81234',
          inputJson: JSON.stringify({ q: 'LLM context caching performance benchmark speedup API costs' }, null, 2),
          outputJson: JSON.stringify({
            organic: [
              { title: 'Understanding Context Caching', snippet: 'Context caching allows users to cache prompt prefixes, cutting latency by 50% and API costs by up to 80%.' },
              { title: 'Benchmark of LLM Context Caching', snippet: 'Our benchmarks show a 4x reduction in time-to-first-token (TTFT) for prompts exceeding 100k tokens.' }
            ]
          }, null, 2)
        }
      },
      {
        id: 'r3',
        type: 'customNode',
        position: { x: 250, y: 250 },
        data: {
          label: 'Extract Source Text',
          type: 'tool',
          toolName: 'WebScraper',
          latency: '1.8s',
          cost: 0.002,
          hash: 'f9e8d7c6b5a41122',
          inputJson: JSON.stringify({ url: 'https://example.com/llm-caching-benchmarks' }, null, 2),
          outputJson: JSON.stringify({ rawText: 'Prompt caching stores the KV cache of system prompts. This reduces time-to-first-token. For Anthropic Claude 3.5 Sonnet, caching saves 90% of prompt token costs if reused. In our test, time was cut from 4.8 seconds to 1.2 seconds, reflecting a 75% latency decrease.' }, null, 2)
        }
      },
      {
        id: 'r4',
        type: 'customNode',
        position: { x: 250, y: 350 },
        data: {
          label: 'Synthesize Report',
          type: 'llm',
          toolName: 'claude-3-5-sonnet',
          latency: '4.6s',
          cost: 0.075,
          tokens: { prompt: 4800, completion: 600, total: 5400 },
          hash: '3f4b5c6d7e8f9012',
          prompt: 'Write a technical summary about LLM Context Caching. Include cost savings, latency metrics, and details about Claude 3.5 Sonnet prompt caching.',
          response: '## Analysis of LLM Context Caching Benefits\n\n### 1. Cost Savings\nBy reusing KV caches, prompt caching cuts input token expenses significantly. For Claude 3.5 Sonnet, developers save **90%** on prompt tokens for cached segments, yielding substantial cost reductions.\n\n### 2. Latency Optimization\nBenchmarks verify a massive reduction in Time-to-First-Token (TTFT). In verified tests, execution latency dropped from 4.8 seconds to 1.2 seconds, resulting in a **75% speedup**.\n\n### 3. Conclusion\nContext caching is essential for RAG pipelines and long-context applications.',
          inputJson: JSON.stringify({ model: 'claude-3-5-sonnet', temperature: 0.2 }, null, 2),
          outputJson: JSON.stringify({ status: 'report_generated', size: 452 }, null, 2)
        }
      },
      {
        id: 'r5',
        type: 'customNode',
        position: { x: 250, y: 450 },
        data: {
          label: 'Compile Bibliography',
          type: 'llm',
          toolName: 'gpt-4o-mini',
          latency: '2.5s',
          cost: 0.015,
          tokens: { prompt: 800, completion: 180, total: 980 },
          hash: 'a9b8c7d6e5f41234',
          prompt: 'Compile a Markdown bibliography containing references for the following source: https://example.com/llm-caching-benchmarks ("Benchmark of LLM Context Caching").',
          response: '### Bibliography\n\n* **Reference 1**: "Benchmark of LLM Context Caching." *Example Tech Blog*. Available at: https://example.com/llm-caching-benchmarks.\n* **Reference 2**: "Understanding Context Caching." *Developer Docs*. Caching prompt prefixes to reduce latency and API costs.',
          inputJson: JSON.stringify({ model: 'gpt-4o-mini', temperature: 0.0 }, null, 2),
          outputJson: JSON.stringify({ bibCount: 2 }, null, 2)
        }
      },
      {
        id: 'r6',
        type: 'customNode',
        position: { x: 250, y: 550 },
        data: {
          label: 'Finish Report Output',
          type: 'finish',
          latency: '0.5s',
          cost: 0,
          hash: 'cb23da718e2bb4f5',
          outputJson: JSON.stringify({ status: 'completed', reportLength: 1205, sourcesAttached: 2 }, null, 2)
        }
      }
    ],
    edges: [
      { id: 'er1-2', source: 'r1', target: 'r2' },
      { id: 'er2-3', source: 'r2', target: 'r3' },
      { id: 'er3-4', source: 'r3', target: 'r4' },
      { id: 'er4-5', source: 'r4', target: 'r5' },
      { id: 'er5-6', source: 'r5', target: 'r6' }
    ],
    divergence: {
      divergedNodeId: 'r4',
      expectedHash: '3f4b5c6d7e8f9012',
      actualHash: '98d7e6c5b4a3f210',
      expectedOutput: '## Analysis of LLM Context Caching Benefits\n\n### 1. Cost Savings\nBy reusing KV caches, prompt caching cuts input token expenses significantly. For Claude 3.5 Sonnet, developers save **90%** on prompt tokens for cached segments, yielding substantial cost reductions.\n\n### 2. Latency Optimization\nBenchmarks verify a massive reduction in Time-to-First-Token (TTFT). In verified tests, execution latency dropped from 4.8 seconds to 1.2 seconds, resulting in a **75% speedup**.\n\n### 3. Conclusion\nContext caching is essential for RAG pipelines and long-context applications.',
      actualOutput: '## Analysis of LLM Context Caching Benefits\n\n### 1. Cost Savings\nBy reusing KV caches, prompt caching cuts input token expenses significantly. For Claude 3.5 Sonnet, developers save **50%** on prompt tokens for cached segments, which is lower than expected.\n\n### 2. Latency Optimization\nBenchmarks verify a minor reduction in Time-to-First-Token (TTFT). In verified tests, execution latency dropped from 4.8 seconds to 3.6 seconds, resulting in a **25% speedup** only.\n\n### 3. Conclusion\nContext caching shows marginal performance improvements with the new model configuration.',
      divergedNodes: [
        {
          id: 'r1',
          type: 'customNode',
          position: { x: 250, y: 50 },
          data: {
            label: 'Start Research',
            type: 'start',
            latency: '0.0s',
            cost: 0,
            hash: 'a1b2c3d4e5f60718',
            inputJson: JSON.stringify({ query: 'LLM context caching performance benefits', maxSources: 3 }, null, 2)
          }
        },
        {
          id: 'r2',
          type: 'customNode',
          position: { x: 250, y: 150 },
          data: {
            label: 'Google Web Search',
            type: 'tool',
            toolName: 'SerperAPI',
            latency: '1.2s',
            cost: 0.005,
            hash: 'e3f4a5b6c7d81234',
            inputJson: JSON.stringify({ q: 'LLM context caching performance benchmark speedup API costs' }, null, 2),
            outputJson: JSON.stringify({
              organic: [
                { title: 'Understanding Context Caching', snippet: 'Context caching allows users to cache prompt prefixes, cutting latency by 50% and API costs by up to 80%.' },
                { title: 'Benchmark of LLM Context Caching', snippet: 'Our benchmarks show a 4x reduction in time-to-first-token (TTFT) for prompts exceeding 100k tokens.' }
              ]
            }, null, 2)
          }
        },
        {
          id: 'r3',
          type: 'customNode',
          position: { x: 250, y: 250 },
          data: {
            label: 'Extract Source Text',
            type: 'tool',
            toolName: 'WebScraper',
            latency: '1.8s',
            cost: 0.002,
            hash: 'f9e8d7c6b5a41122',
            inputJson: JSON.stringify({ url: 'https://example.com/llm-caching-benchmarks' }, null, 2),
            outputJson: JSON.stringify({ rawText: 'Prompt caching stores the KV cache of system prompts. This reduces time-to-first-token. For Anthropic Claude 3.5 Sonnet, caching saves 90% of prompt token costs if reused. In our test, time was cut from 4.8 seconds to 1.2 seconds, reflecting a 75% latency decrease.' }, null, 2)
          }
        },
        {
          id: 'r4',
          type: 'customNode',
          position: { x: 250, y: 350 },
          data: {
            label: 'Synthesize Report',
            type: 'llm',
            toolName: 'claude-3-5-sonnet',
            latency: '4.9s',
            cost: 0.075,
            tokens: { prompt: 4800, completion: 590, total: 5390 },
            hash: '98d7e6c5b4a3f210',
            prompt: 'Write a technical summary about LLM Context Caching. Include cost savings, latency metrics, and details about Claude 3.5 Sonnet prompt caching.',
            response: '## Analysis of LLM Context Caching Benefits\n\n### 1. Cost Savings\nBy reusing KV caches, prompt caching cuts input token expenses significantly. For Claude 3.5 Sonnet, developers save **50%** on prompt tokens for cached segments, which is lower than expected.\n\n### 2. Latency Optimization\nBenchmarks verify a minor reduction in Time-to-First-Token (TTFT). In verified tests, execution latency dropped from 4.8 seconds to 3.6 seconds, resulting in a **25% speedup** only.\n\n### 3. Conclusion\nContext caching shows marginal performance improvements with the new model configuration.',
            inputJson: JSON.stringify({ model: 'claude-3-5-sonnet', temperature: 0.7 }, null, 2),
            outputJson: JSON.stringify({ status: 'report_generated', size: 412 }, null, 2)
          }
        },
        {
          id: 'r5',
          type: 'customNode',
          position: { x: 250, y: 450 },
          data: {
            label: 'Compile Bibliography',
            type: 'llm',
            toolName: 'gpt-4o-mini',
            latency: '2.5s',
            cost: 0.015,
            tokens: { prompt: 800, completion: 180, total: 980 },
            hash: 'a9b8c7d6e5f41234',
            prompt: 'Compile a Markdown bibliography containing references for the following source: https://example.com/llm-caching-benchmarks ("Benchmark of LLM Context Caching").',
            response: '### Bibliography\n\n* **Reference 1**: "Benchmark of LLM Context Caching." *Example Tech Blog*. Available at: https://example.com/llm-caching-benchmarks.\n* **Reference 2**: "Understanding Context Caching." *Developer Docs*. Caching prompt prefixes to reduce latency and API costs.',
            inputJson: JSON.stringify({ model: 'gpt-4o-mini', temperature: 0.0 }, null, 2),
            outputJson: JSON.stringify({ bibCount: 2 }, null, 2)
          }
        },
        {
          id: 'r6',
          type: 'customNode',
          position: { x: 250, y: 550 },
          data: {
            label: 'Finish Report Output',
            type: 'finish',
            latency: '0.5s',
            cost: 0,
            hash: '4d8a1c92ea8bb3f2',
            outputJson: JSON.stringify({ status: 'completed', reportLength: 1024, sourcesAttached: 2 }, null, 2)
          }
        }
      ],
      divergedEdges: [
        { id: 'er1-2', source: 'r1', target: 'r2' },
        { id: 'er2-3', source: 'r2', target: 'r3' },
        { id: 'er3-4', source: 'r3', target: 'r4', style: { stroke: '#EF4444', strokeWidth: 3 }, animated: true },
        { id: 'er4-5', source: 'r4', target: 'r5', style: { stroke: '#EF4444' } },
        { id: 'er5-6', source: 'r5', target: 'r6', style: { stroke: '#EF4444' } }
      ]
    }
  },
  {
    id: 'coding-assistant',
    name: 'Coding Assistant',
    description: 'Generates files, triggers tests, compiles code, and fixes compile errors in a sandbox.',
    runtime: '6.8s',
    replayTime: '0.10s',
    nodesCount: 5,
    replayStatus: 'success',
    lastModified: '3 hours ago',
    moneySaved: '$0.75',
    totalCost: '$0.95',
    apiCallsAvoided: 3,
    replayCount: 5,
    hash: '3B82F622C55E8B5C3B82',
    nodes: [
      {
        id: 'c1',
        type: 'customNode',
        position: { x: 250, y: 50 },
        data: {
          label: 'Start Coding Request',
          type: 'start',
          latency: '0.0s',
          cost: 0,
          hash: '2b3c4d5e6f7a8b9c',
          inputJson: JSON.stringify({ prompt: 'Implement a binary search tree in TypeScript', lang: 'typescript' }, null, 2)
        }
      },
      {
        id: 'c2',
        type: 'customNode',
        position: { x: 250, y: 150 },
        data: {
          label: 'Generate Code',
          type: 'llm',
          toolName: 'claude-3-5-sonnet',
          latency: '3.4s',
          cost: 0.045,
          tokens: { prompt: 1500, completion: 400, total: 1900 },
          hash: 'd8c7b6a5f4e3d2c1',
          prompt: 'Write a TypeScript class BinarySearchTree with insert and search methods.',
          response: 'class Node {\n  value: number;\n  left: Node | null = null;\n  right: Node | null = null;\n  constructor(value: number) {\n    this.value = value;\n  }\n}\n\nexport class BinarySearchTree {\n  root: Node | null = null;\n  insert(value: number) {\n    const newNode = new Node(value);\n    if (!this.root) {\n      this.root = newNode;\n      return;\n    }\n    let current = this.root;\n    while (true) {\n      if (value < current.value) {\n        if (!current.left) {\n          current.left = newNode;\n          break;\n        }\n        current = current.left;\n      } else {\n        if (!current.right) {\n          current.right = newNode;\n          break;\n        }\n        current = current.right;\n      }\n    }\n  }\n}',
          inputJson: JSON.stringify({ model: 'claude-3-5-sonnet', temperature: 0.1 }, null, 2),
          outputJson: JSON.stringify({ language: 'typescript', lines: 34 }, null, 2)
        }
      },
      {
        id: 'c3',
        type: 'customNode',
        position: { x: 250, y: 250 },
        data: {
          label: 'Write Unit Tests',
          type: 'llm',
          toolName: 'gpt-4o-mini',
          latency: '1.8s',
          cost: 0.008,
          tokens: { prompt: 900, completion: 150, total: 1050 },
          hash: 'e5d4c3b2a1f6e5d4',
          prompt: 'Write Jest tests for the BinarySearchTree implementation containing inserts.',
          response: 'import { BinarySearchTree } from "./bst";\n\ntest("insert nodes", () => {\n  const bst = new BinarySearchTree();\n  bst.insert(10);\n  bst.insert(5);\n  bst.insert(15);\n  expect(bst.root?.value).toBe(10);\n  expect(bst.root?.left?.value).toBe(5);\n  expect(bst.root?.right?.value).toBe(15);\n});',
          inputJson: JSON.stringify({ model: 'gpt-4o-mini', temperature: 0 }, null, 2),
          outputJson: JSON.stringify({ testFile: 'bst.test.ts', tests: 1 }, null, 2)
        }
      },
      {
        id: 'c4',
        type: 'customNode',
        position: { x: 250, y: 350 },
        data: {
          label: 'Run Jest Tests',
          type: 'tool',
          toolName: 'JestTestRunner',
          latency: '1.2s',
          cost: 0.002,
          hash: 'f9a8e7d6c5b4a3e2',
          inputJson: JSON.stringify({ files: ['bst.ts', 'bst.test.ts'] }, null, 2),
          outputJson: JSON.stringify({ success: true, passed: 1, failed: 0, timeSecs: 0.8 }, null, 2)
        }
      },
      {
        id: 'c5',
        type: 'customNode',
        position: { x: 250, y: 450 },
        data: {
          label: 'Finish Coding Task',
          type: 'finish',
          latency: '0.4s',
          cost: 0,
          hash: 'ba729dc5e4d3c2b1',
          outputJson: JSON.stringify({ status: 'completed', testsPassed: true, fileCreated: 'bst.ts' }, null, 2)
        }
      }
    ],
    edges: [
      { id: 'ec1-2', source: 'c1', target: 'c2' },
      { id: 'ec2-3', source: 'c2', target: 'c3' },
      { id: 'ec3-4', source: 'c3', target: 'c4' },
      { id: 'ec4-5', source: 'c4', target: 'c5' }
    ]
  },
  {
    id: 'sales-agent',
    name: 'Sales Agent',
    description: 'Scrapes company data, updates CRM records, and drafts custom sales pitch emails.',
    runtime: '4.8s',
    replayTime: '0.07s',
    nodesCount: 5,
    replayStatus: 'success',
    lastModified: '1 day ago',
    moneySaved: '$0.40',
    totalCost: '$0.52',
    apiCallsAvoided: 3,
    replayCount: 19,
    hash: '8B5CF622C55E8B5C8B5C',
    nodes: [
      {
        id: 's1',
        type: 'customNode',
        position: { x: 250, y: 50 },
        data: {
          label: 'Start Sales Run',
          type: 'start',
          latency: '0.0s',
          cost: 0,
          hash: '1c2d3e4f5a6b7c8d',
          inputJson: JSON.stringify({ company: 'Acme Corp', contactPerson: 'Jane Doe', role: 'VP Engineering' }, null, 2)
        }
      },
      {
        id: 's2',
        type: 'customNode',
        position: { x: 250, y: 150 },
        data: {
          label: 'Fetch CRM Status',
          type: 'tool',
          toolName: 'HubspotAPI',
          latency: '0.8s',
          cost: 0.005,
          hash: 'bc8d7c6b5a4f3e2d',
          inputJson: JSON.stringify({ companyName: 'Acme Corp' }, null, 2),
          outputJson: JSON.stringify({ companyId: 'acme_908', lifetimeValue: 0, status: 'lead', owner: 'Unassigned' }, null, 2)
        }
      },
      {
        id: 's3',
        type: 'customNode',
        position: { x: 250, y: 250 },
        data: {
          label: 'Draft Pitch Email',
          type: 'llm',
          toolName: 'gpt-4o',
          latency: '2.5s',
          cost: 0.038,
          tokens: { prompt: 1400, completion: 220, total: 1620 },
          hash: '9e8d7c6b5a4a3b2c',
          prompt: 'Draft a short B2B sales email to Jane Doe, VP Engineering at Acme Corp. Pitch our new product: Agent-RR, the deterministic replay engine for AI agents that saves 80% on API testing costs.',
          response: 'Subject: Record once. Replay forever - Agent-RR for Acme Corp\n\nHi Jane,\n\nI saw you are heading engineering at Acme Corp. AI teams struggle with expensive and flaky agent testing due to constant LLM API invocations.\n\nAgent-RR records your agent runs and replayed execution paths deterministically without making repeat LLM calls, saving up to 80% in API charges and letting you debug step-by-step.\n\nWould you be open to a 10-minute demo next Tuesday?\n\nBest,\nSales Agent',
          inputJson: JSON.stringify({ model: 'gpt-4o', temperature: 0.7 }, null, 2),
          outputJson: JSON.stringify({ subject: 'Record once. Replay forever - Agent-RR for Acme Corp', charCount: 450 }, null, 2)
        }
      },
      {
        id: 's4',
        type: 'customNode',
        position: { x: 250, y: 350 },
        data: {
          label: 'Send Email API',
          type: 'tool',
          toolName: 'SendGridSMTP',
          latency: '1.1s',
          cost: 0.002,
          hash: 'e5d4a3b2c1f6e5d4',
          inputJson: JSON.stringify({ to: 'jane.doe@acme.com', subject: 'Record once. Replay forever - Agent-RR for Acme Corp' }, null, 2),
          outputJson: JSON.stringify({ emailSent: true, messageId: 'sg_8731dha829' }, null, 2)
        }
      },
      {
        id: 's5',
        type: 'customNode',
        position: { x: 250, y: 450 },
        data: {
          label: 'Finish Run & Log',
          type: 'finish',
          latency: '0.4s',
          cost: 0,
          hash: 'ab7d8c9e1f2b3c4d',
          outputJson: JSON.stringify({ status: 'success', emailSent: true, logLogged: true }, null, 2)
        }
      }
    ],
    edges: [
      { id: 'es1-2', source: 's1', target: 's2' },
      { id: 'es2-3', source: 's2', target: 's3' },
      { id: 'es3-4', source: 's3', target: 's4' },
      { id: 'es4-5', source: 's4', target: 's5' }
    ]
  }
];
