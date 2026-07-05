"""Self-contained HTML renderer for a trace's causal DAG (``agent-rr view``).

Produces one dependency-free HTML file: layered DAG layout computed here in
Python (longest-path-from-root layering), rendered as absolutely-positioned
HTML nodes over one SVG edge layer. No CDN scripts, no network — the file
works offline and can be committed or attached to a bug report next to the
trace it visualises.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Union

from .events import EVENT_TYPE_METADATA, TraceEvent

_NODE_WIDTH = 240
_NODE_HEIGHT = 78
_H_GAP = 90
_V_GAP = 36
_MARGIN = 40

_TYPE_COLORS = {
    "root_input": "#2563eb",
    "llm_call": "#7c3aed",
    "tool_call": "#059669",
    "final_output": "#d97706",
}

_CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; margin: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #f8fafc; color: #0f172a;
}
@media (prefers-color-scheme: dark) {
  body { background: #0b1120; color: #e2e8f0; }
  .node { background: #1e293b; border-color: #334155; }
  header { background: #0f172a; border-color: #1e293b; }
  #detail { background: #0f172a; border-color: #1e293b; }
  pre { background: #1e293b; }
}
header {
  padding: 14px 24px; border-bottom: 1px solid #e2e8f0; background: #fff;
  display: flex; gap: 18px; align-items: baseline; flex-wrap: wrap;
}
header h1 { font-size: 16px; }
header .meta { font-size: 12px; opacity: 0.7; font-family: ui-monospace, monospace; }
#canvas { position: relative; overflow: auto; padding-bottom: 220px; }
svg.edges { position: absolute; top: 0; left: 0; pointer-events: none; }
.node {
  position: absolute; width: 240px; height: 78px; border: 1px solid #cbd5e1;
  border-radius: 10px; background: #fff; padding: 8px 12px; cursor: pointer;
  border-left-width: 5px; box-shadow: 0 1px 3px rgba(0,0,0,.08);
  overflow: hidden; transition: box-shadow .12s;
}
.node:hover { box-shadow: 0 4px 14px rgba(0,0,0,.18); }
.node.selected { outline: 2px solid #2563eb; }
.node .type { font-size: 10px; letter-spacing: .08em; text-transform: uppercase; opacity: .65; }
.node .name { font-size: 14px; font-weight: 600; margin: 2px 0; white-space: nowrap; text-overflow: ellipsis; overflow: hidden; }
.node .hash { font-size: 10px; font-family: ui-monospace, monospace; opacity: .55; }
.node.error { border-color: #dc2626; background: #fef2f2; }
@media (prefers-color-scheme: dark) { .node.error { background: #3f1d1d; } }
.badge { font-size: 10px; color: #dc2626; font-weight: 700; }
#detail {
  position: fixed; bottom: 0; left: 0; right: 0; max-height: 200px; overflow: auto;
  border-top: 1px solid #e2e8f0; background: #fff; padding: 12px 24px; display: none;
}
#detail.open { display: block; }
#detail h2 { font-size: 13px; margin-bottom: 6px; }
pre { font-size: 12px; background: #f1f5f9; padding: 8px; border-radius: 6px; overflow: auto; }
"""

_JS = """
document.addEventListener("DOMContentLoaded", () => {
  const rawData = document.getElementById('agent-rr-trace-data').textContent;
  const NODES = JSON.parse(rawData);
  const detail = document.getElementById('detail');
  let selected = null;
  function show(id) {
    const n = NODES[id];
    if (selected) selected.classList.remove('selected');
    selected = document.getElementById('node-' + id);
    selected.classList.add('selected');
    document.getElementById('detail-title').textContent = n.label;
    document.getElementById('detail-body').textContent = JSON.stringify(
      {payload: n.payload, historical_response: n.historical_response,
       status: n.status, error: n.error, parent_event_ids: n.parents,
       argument_hash: n.argument_hash, context_hash: n.context_hash}, null, 2);
    detail.classList.add('open');
  }
  document.querySelectorAll('.node').forEach(el =>
    el.addEventListener('click', () => show(el.dataset.id)));
});
"""


def _layout(events: list[TraceEvent]) -> dict[str, tuple[int, int]]:
    """Longest-path layering: column = 1 + max(parent columns); row = order
    of appearance within the column. Valid traces guarantee parents precede
    children in sequence order, so one forward pass suffices."""
    depth: dict[str, int] = {}
    rows: dict[int, int] = {}
    positions: dict[str, tuple[int, int]] = {}
    for event in events:
        parents = event.parent_event_ids
        column = 0 if not parents else 1 + max(depth[p] for p in parents)
        depth[event.event_id] = column
        row = rows.get(column, 0)
        rows[column] = row + 1
        positions[event.event_id] = (column, row)
    return positions


def render_trace_html(events: list[TraceEvent], trace_name: str) -> str:
    """Return one self-contained HTML page for the trace's causal DAG."""
    drawable = [e for e in events if e.event_type != EVENT_TYPE_METADATA]
    metadata = events[0] if events and events[0].event_type == EVENT_TYPE_METADATA else None
    positions = _layout(drawable)

    def px(col_row: tuple[int, int]) -> tuple[int, int]:
        column, row = col_row
        x = _MARGIN + column * (_NODE_WIDTH + _H_GAP)
        y = _MARGIN + row * (_NODE_HEIGHT + _V_GAP)
        return x, y

    max_x = max((px(pos)[0] for pos in positions.values()), default=0) + _NODE_WIDTH + _MARGIN
    max_y = max((px(pos)[1] for pos in positions.values()), default=0) + _NODE_HEIGHT + _MARGIN

    node_divs: list[str] = []
    edge_paths: list[str] = []
    node_data: dict[str, dict] = {}
    for event in drawable:
        x, y = px(positions[event.event_id])
        color = _TYPE_COLORS.get(event.event_type, "#64748b")
        label = event.name or event.event_type
        error_cls = " error" if event.status == "error" else ""
        badge = '<span class="badge">ERROR</span>' if event.status == "error" else ""
        node_divs.append(
            f'<div class="node{error_cls}" id="node-{event.event_id}" '
            f'data-id="{event.event_id}" '
            f'style="left:{x}px;top:{y}px;border-left-color:{color}">'
            f'<div class="type">{html.escape(event.event_type)} '
            f'&middot; seq {event.call_sequence_index} {badge}</div>'
            f'<div class="name">{html.escape(label)}</div>'
            f'<div class="hash">{html.escape((event.context_hash or "")[:16])}&hellip;</div>'
            f"</div>"
        )
        for parent_id in event.parent_event_ids:
            px1, py1 = px(positions[parent_id])
            x1, y1 = px1 + _NODE_WIDTH, py1 + _NODE_HEIGHT // 2
            x2, y2 = x, y + _NODE_HEIGHT // 2
            mid = (x1 + x2) // 2
            edge_paths.append(
                f'<path d="M{x1},{y1} C{mid},{y1} {mid},{y2} {x2},{y2}" '
                f'fill="none" stroke="#94a3b8" stroke-width="1.5" '
                f'marker-end="url(#arrow)"/>'
            )
        node_data[event.event_id] = {
            "label": f"{event.event_type} · {label}",
            "payload": event.payload,
            "historical_response": event.historical_response,
            "status": event.status,
            "error": event.error,
            "parents": event.parent_event_ids,
            "argument_hash": event.argument_hash,
            "context_hash": event.context_hash,
        }

    meta_bits = ""
    if metadata is not None:
        payload = metadata.payload or {}
        meta_bits = (
            f'<span class="meta">agent: {html.escape(str(payload.get("agent_id", "?")))}</span>'
            f'<span class="meta">run: {html.escape(str(payload.get("run_id", "?")))}</span>'
            f'<span class="meta">recorded: {html.escape(str(payload.get("trace_creation_time", "?")))}</span>'
        )

    safe_json = json.dumps(node_data, ensure_ascii=False, sort_keys=True)\
        .replace("<", "\\u003c")\
        .replace(">", "\\u003e")\
        .replace("&", "\\u0026")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent-RR · {html.escape(trace_name)}</title>
<style>{_CSS}</style>
</head>
<body>
<header>
  <h1>✈️ Agent-RR causal DAG — {html.escape(trace_name)}</h1>
  {meta_bits}
  <span class="meta">{len(drawable)} events · click a node for details</span>
</header>
<div id="canvas" style="width:{max_x}px;height:{max_y}px">
  <svg class="edges" width="{max_x}" height="{max_y}">
    <defs>
      <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3"
              orient="auto" markerUnits="strokeWidth">
        <path d="M0,0 L7,3 L0,6 Z" fill="#94a3b8"/>
      </marker>
    </defs>
    {''.join(edge_paths)}
  </svg>
  {''.join(node_divs)}
</div>
<div id="detail"><h2 id="detail-title"></h2><pre id="detail-body"></pre></div>
<script type="application/json" id="agent-rr-trace-data">
{safe_json}
</script>
<script>{_JS}</script>
</body>
</html>
"""


def write_trace_html(
    events: list[TraceEvent],
    trace_file: Union[str, Path],
    output_file: Union[str, Path, None] = None,
) -> Path:
    """Render *events* to HTML next to *trace_file* (or at *output_file*)."""
    trace_path = Path(trace_file)
    out_path = Path(output_file) if output_file is not None else trace_path.with_suffix(".html")
    out_path.write_text(render_trace_html(events, trace_path.name), encoding="utf-8")
    return out_path
