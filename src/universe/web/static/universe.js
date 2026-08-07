/* Universe page — hand-rolled force-directed graph over /api/universe.
   Vanilla ES module, SVG rendering, no libraries. */

const SVG_NS = 'http://www.w3.org/2000/svg';

const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
}[char]));

/* One color per modality + knowledge combination. */
const KC_TYPE_COLORS = {
  'explain-concept': { accent: '#2563eb', dark: '#60a5fa' },
  'explain-procedure': { accent: '#7c3aed', dark: '#a78bfa' },
  'do-procedure': { accent: '#b45309', dark: '#fbbf24' },
  'do-concept': { accent: '#15803d', dark: '#4ade80' },
};
const NEUTRAL_COLOR = { accent: '#64748b', dark: '#94a3b8' };

const reducedMotion = typeof window.matchMedia === 'function'
  && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* Simulation constants. */
const REPULSION = 1700;
const REPULSION_CUTOFF2 = 420 * 420;
const SPRING_MUTUAL = { length: 120, strength: 0.03 };
const SPRING_GROUP = { length: 27, strength: 0.22 };
const CENTERING = 0.012;
const DAMPING = 0.85;
const ALPHA_DECAY = 0.986;
const ALPHA_MIN = 0.02;
const NODE_EDGE_GAP = 15;

/* Semantic zoom — stroke widths in world units at zoom 1; JS divides them
   by the zoom factor so edges, hulls, and dashes stay constant on screen. */
const EDGE_WIDTH_MUTUAL = 1.4;
const EDGE_WIDTH_ONEWAY = 1.1;
const ONEWAY_DASH = [4.5, 4];
const HULL_PAD = 30;

const $ = (selector, root = document) => root.querySelector(selector);

const els = {
  svg: $('[data-svg]'),
  canvas: $('[data-canvas]'),
  overlay: $('[data-overlay]'),
  overlayMessage: $('[data-overlay-message]'),
  emptyNote: $('[data-empty-note]'),
  detail: $('[data-detail]'),
  status: $('[data-status]'),
  search: $('[data-search]'),
  sourceFilter: $('[data-source-filter]'),
  toggleOneway: $('[data-toggle-oneway]'),
  toggleUnmerged: $('[data-toggle-unmerged]'),
  compositeCount: $('[data-composite-count]'),
};

const state = {
  nodes: [],
  nodeById: new Map(),
  mutualEdges: [],
  oneWayEdges: [],
  springs: [],
  groups: [],
  grouping: null,
  groupById: new Map(),
  sources: [],
  hasVerdicts: false,
  selectedId: null,
  selectedGroupId: null,
  sticky: false,
  filters: { query: '', source: '', oneway: true, unmergedOnly: false },
};

const sim = { alpha: 1, running: false };
const view = { cx: 0, cy: 0, zoom: 1, baseW: 900 };
const layers = { hulls: null, edges: null, oneway: null, nodes: null };

/* ---------------------------------------------------------------- fetch */

async function fetchJSON(url) {
  const response = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body?.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

/* ---------------------------------------------------------------- build */

function buildGraph(data) {
  const rawNodes = Array.isArray(data.nodes) ? data.nodes : [];
  const rawEdges = Array.isArray(data.edges) ? data.edges : [];
  state.groups = Array.isArray(data.groups) ? data.groups : [];
  state.grouping = data.grouping || null;
  state.hasVerdicts = rawEdges.length > 0;

  /* Sources remain provenance for filtering and inspection. They never
     receive persistent graph colors: a global source palette cannot scale. */
  const seen = new Map();
  for (const node of rawNodes) {
    if (node.source_id != null && !seen.has(node.source_id)) {
      seen.set(node.source_id, node.source_title || String(node.source_id));
    }
  }
  state.sources = [...seen.entries()]
    .map(([id, title]) => ({ id: String(id), title }))
    .sort((a, b) => a.title.localeCompare(b.title));

  /* Group membership from the committed composites. */
  const memberOf = new Map();
  state.groupById = new Map();
  for (const group of state.groups) {
    group.canonicalStatement = group.canonical_statement || '';
    group.canonicalStatus = group.canonical_status || 'missing';
    group.canonicalReason = group.canonical_reason || '';
    state.groupById.set(String(group.id), group);
    for (const member of group.members || []) {
      memberOf.set(String(member), String(group.id));
    }
  }

  state.nodes = rawNodes.map((raw) => ({
    id: String(raw.id),
    statement: raw.statement || '',
    modality: raw.modality || '',
    knowledge: raw.knowledge || '',
    sourceId: raw.source_id == null ? null : String(raw.source_id),
    sourceTitle: raw.source_title || '',
    task: raw.task || '',
    answer: raw.answer || '',
    groupId: memberOf.get(String(raw.id))
      ?? (raw.group_id == null ? null : String(raw.group_id)),
    x: 0, y: 0, vx: 0, vy: 0,
    pinned: false,
    dim: false,
    el: null,
  }));
  state.nodeById = new Map(state.nodes.map((node) => [node.id, node]));

  for (const group of state.groups) {
    group.sources = sourcesForGroup(group);
  }

  state.mutualEdges = [];
  state.oneWayEdges = [];
  for (const edge of rawEdges) {
    const a = state.nodeById.get(String(edge.a));
    const b = state.nodeById.get(String(edge.b));
    if (!a || !b) continue;
    if (edge.mutual) {
      state.mutualEdges.push({ a, b, el: null });
    } else if (edge.ab === 'clear_yes' && edge.ba !== 'clear_yes') {
      state.oneWayEdges.push({ from: a, to: b, el: null });
    } else if (edge.ba === 'clear_yes' && edge.ab !== 'clear_yes') {
      state.oneWayEdges.push({ from: b, to: a, el: null });
    }
    /* Other verdict levels stay hidden in v1. */
  }

  /* Springs: mutual verdicts, plus stronger pairwise pull inside groups. */
  state.springs = state.mutualEdges.map(({ a, b }) => ({ a, b, ...SPRING_MUTUAL }));
  for (const group of state.groups) {
    const members = (group.members || [])
      .map((id) => state.nodeById.get(String(id)))
      .filter(Boolean);
    for (let i = 0; i < members.length; i += 1) {
      for (let j = i + 1; j < members.length; j += 1) {
        state.springs.push({ a: members[i], b: members[j], ...SPRING_GROUP });
      }
    }
  }

  seedPositions();
}

function seedPositions() {
  const count = state.nodes.length || 1;
  const radius = Math.max(180, Math.sqrt(count) * 46);
  view.baseW = Math.max(900, radius * 2.7);

  const groupIds = state.groups.map((group) => String(group.id));
  const groupCenter = new Map();
  groupIds.forEach((id, index) => {
    const angle = (index / Math.max(1, groupIds.length)) * Math.PI * 2;
    groupCenter.set(id, {
      x: Math.cos(angle) * radius * 0.55,
      y: Math.sin(angle) * radius * 0.55,
    });
  });

  const golden = Math.PI * (3 - Math.sqrt(5));
  let loose = 0;
  state.nodes.forEach((node, index) => {
    const center = node.groupId ? groupCenter.get(node.groupId) : null;
    if (center) {
      const angle = index * golden;
      node.x = center.x + Math.cos(angle) * 13 + (index % 3);
      node.y = center.y + Math.sin(angle) * 13 + (index % 2);
    } else {
      const angle = loose * golden;
      const r = radius * Math.sqrt((loose + 0.5) / count);
      node.x = Math.cos(angle) * r;
      node.y = Math.sin(angle) * r;
      loose += 1;
    }
  });
}

/* ----------------------------------------------------------- simulation */

function tick() {
  const nodes = state.nodes;
  const n = nodes.length;
  const fx = new Float64Array(n);
  const fy = new Float64Array(n);
  nodes.forEach((node, index) => { node._i = index; });

  for (let i = 0; i < n; i += 1) {
    const a = nodes[i];
    for (let j = i + 1; j < n; j += 1) {
      const b = nodes[j];
      let dx = a.x - b.x;
      let dy = a.y - b.y;
      let d2 = dx * dx + dy * dy;
      if (d2 > REPULSION_CUTOFF2) continue;
      if (d2 < 1) { dx = (i - j) * 0.31; dy = 0.53; d2 = 0.4; }
      const sameComposite = a.groupId && a.groupId === b.groupId;
      const force = (REPULSION * (sameComposite ? 0.12 : 1)) / d2;
      const d = Math.sqrt(d2);
      const ux = dx / d;
      const uy = dy / d;
      fx[i] += ux * force; fy[i] += uy * force;
      fx[j] -= ux * force; fy[j] -= uy * force;
    }
  }

  for (const spring of state.springs) {
    const dx = spring.b.x - spring.a.x;
    const dy = spring.b.y - spring.a.y;
    const d = Math.sqrt(dx * dx + dy * dy) || 1;
    const force = spring.strength * (d - spring.length);
    const ux = (dx / d) * force;
    const uy = (dy / d) * force;
    fx[spring.a._i] += ux; fy[spring.a._i] += uy;
    fx[spring.b._i] -= ux; fy[spring.b._i] -= uy;
  }

  for (let i = 0; i < n; i += 1) {
    const node = nodes[i];
    if (node.pinned) { node.vx = 0; node.vy = 0; continue; }
    fx[i] -= node.x * CENTERING;
    fy[i] -= node.y * CENTERING;
    node.vx = (node.vx + fx[i] * sim.alpha) * DAMPING;
    node.vy = (node.vy + fy[i] * sim.alpha) * DAMPING;
    node.x += node.vx;
    node.y += node.vy;
  }
}

function frame() {
  if (sim.alpha > ALPHA_MIN) {
    tick();
    sim.alpha *= ALPHA_DECAY;
    render();
    window.requestAnimationFrame(frame);
  } else {
    sim.running = false;
    render();
  }
}

function reheat(boost = 0.5) {
  sim.alpha = Math.max(sim.alpha, boost);
  if (reducedMotion) return;
  if (!sim.running) {
    sim.running = true;
    window.requestAnimationFrame(frame);
  }
}

function settleInstantly() {
  sim.alpha = 1;
  let guard = 0;
  while (sim.alpha > ALPHA_MIN && guard < 600) {
    tick();
    sim.alpha *= ALPHA_DECAY;
    guard += 1;
  }
  render();
}

/* ------------------------------------------------------------ rendering */

function mountScaffold() {
  els.svg.innerHTML = `
    <defs>
      <marker id="u-arrow" viewBox="0 0 8 8" refX="7" refY="4"
              markerWidth="7" markerHeight="7" orient="auto">
        <path class="u-arrowhead" d="M0 0 L8 4 L0 8 Z"></path>
      </marker>
    </defs>
    <g data-layer-hulls></g>
    <g data-layer-edges></g>
    <g data-layer-oneway></g>
    <g data-layer-nodes></g>
  `;
  layers.hulls = $('[data-layer-hulls]', els.svg);
  layers.edges = $('[data-layer-edges]', els.svg);
  layers.oneway = $('[data-layer-oneway]', els.svg);
  layers.nodes = $('[data-layer-nodes]', els.svg);
  syncedZoom = 0; /* fresh layer groups need their stroke widths re-applied */
}

function glyphCircle(className, radius) {
  return `<circle class="${className}" r="${radius}"></circle>`;
}

function kcTypeKey(node) {
  if (
    (node.modality === 'do' || node.modality === 'explain')
    && (node.knowledge === 'concept' || node.knowledge === 'procedure')
  ) {
    return `${node.modality}-${node.knowledge}`;
  }
  return 'other';
}

function kcTypeColor(node) {
  return KC_TYPE_COLORS[kcTypeKey(node)] || NEUTRAL_COLOR;
}

function sourcesForGroup(group) {
  const sources = new Map();
  for (const id of group?.members || []) {
    const node = state.nodeById.get(String(id));
    if (node?.sourceId != null) {
      sources.set(node.sourceId, node.sourceTitle || node.sourceId);
    }
  }
  return [...sources.entries()]
    .map(([id, title]) => ({ id, title }))
    .sort((a, b) => a.title.localeCompare(b.title));
}

function groupTypeColor(group) {
  const counts = new Map();
  for (const id of group?.members || []) {
    const node = state.nodeById.get(String(id));
    if (!node) continue;
    const type = kcTypeKey(node);
    counts.set(type, (counts.get(type) || 0) + 1);
  }
  const type = [...counts.entries()]
    .sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0]))[0]?.[0];
  return KC_TYPE_COLORS[type] || NEUTRAL_COLOR;
}

function mountGraph() {
  for (const node of state.nodes) {
    const color = kcTypeColor(node);
    const group = node.groupId ? state.groupById.get(node.groupId) : null;
    const displayStatement = group?.canonicalStatement || node.statement;
    const accessibleLabel = group?.canonicalStatement
      ? `${node.statement} · member of ${group.canonicalStatement}`
      : node.statement;
    const provenanceCount = group?.sources?.length || (node.sourceId == null ? 0 : 1);

    const el = document.createElementNS(SVG_NS, 'g');
    el.setAttribute('class', 'u-node');
    el.setAttribute('tabindex', '0');
    el.setAttribute('role', 'button');
    el.setAttribute('aria-label', accessibleLabel || 'Knowledge component');
    el.dataset.id = node.id;
    el.setAttribute('style', `--kc:${color.accent};--kc-dark:${color.dark}`);
    el.innerHTML = `
      ${glyphCircle('u-node__focus', 15.5)}
      ${glyphCircle('u-node__ring', 9.5)}
      ${glyphCircle('u-node__dot', 6)}
      <title>${esc(displayStatement)}${group?.canonicalStatement ? `\nMember: ${esc(node.statement)}` : ''}\n${provenanceCount} source${provenanceCount === 1 ? '' : 's'}</title>
    `;
    node.el = el;
    layers.nodes.append(el);
  }

  for (const edge of state.mutualEdges) {
    const el = document.createElementNS(SVG_NS, 'line');
    el.setAttribute('class', 'u-edge u-edge--mutual');
    edge.el = el;
    layers.edges.append(el);
  }

  for (const edge of state.oneWayEdges) {
    const el = document.createElementNS(SVG_NS, 'line');
    el.setAttribute('class', 'u-edge u-edge--oneway');
    el.setAttribute('marker-end', 'url(#u-arrow)');
    edge.el = el;
    layers.oneway.append(el);
  }

  for (const group of state.groups) {
    const members = (group.members || [])
      .map((id) => state.nodeById.get(String(id)))
      .filter(Boolean);
    if (members.length < 2) continue;
    const color = groupTypeColor(group);
    const el = document.createElementNS(SVG_NS, 'path');
    el.setAttribute('class', 'u-hull');
    el.setAttribute('style', `--hull:${color.accent};--hull-dark:${color.dark}`);
    el.setAttribute('tabindex', '0');
    el.setAttribute('role', 'button');
    el.setAttribute('aria-label', `${group.canonicalStatement || 'Composite knowledge component'} · ${members.length} members`);
    el.dataset.group = String(group.id);
    group._members = members;
    group._hullEl = el;
    el.addEventListener('click', () => {
      if (group._ignoreClick) {
        group._ignoreClick = false;
        return;
      }
      selectGroup(group, { sticky: true });
    });
    layers.hulls.append(el);
  }
}

function convexHull(points) {
  if (points.length < 3) return points.slice();
  const sorted = points.slice().sort((a, b) => (a.x - b.x) || (a.y - b.y));
  const cross = (o, a, b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
  const lower = [];
  for (const p of sorted) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop();
    lower.push(p);
  }
  const upper = [];
  for (let i = sorted.length - 1; i >= 0; i -= 1) {
    const p = sorted[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop();
    upper.push(p);
  }
  lower.pop();
  upper.pop();
  return lower.concat(upper);
}

function render() {
  /* Semantic zoom: the viewBox scales distances, so counter-scale each
     glyph group by 1/zoom to keep it constant-size on screen. The scale
     is centered on the node position, so hover/drag targets stay aligned. */
  const inv = 1 / view.zoom;
  const glyphScale = Math.abs(inv - 1) < 1e-4 ? '' : ` scale(${inv.toFixed(4)})`;
  for (const node of state.nodes) {
    node.el.setAttribute('transform',
      `translate(${node.x.toFixed(2)} ${node.y.toFixed(2)})${glyphScale}`);
  }

  for (const edge of state.mutualEdges) {
    edge.el.setAttribute('x1', edge.a.x.toFixed(2));
    edge.el.setAttribute('y1', edge.a.y.toFixed(2));
    edge.el.setAttribute('x2', edge.b.x.toFixed(2));
    edge.el.setAttribute('y2', edge.b.y.toFixed(2));
  }

  for (const edge of state.oneWayEdges) {
    const dx = edge.to.x - edge.from.x;
    const dy = edge.to.y - edge.from.y;
    const d = Math.sqrt(dx * dx + dy * dy) || 1;
    /* Glyphs are counter-scaled by 1/zoom, so the gap that keeps the
       arrow tip off the glyph border scales the same way. */
    const trim = Math.min(NODE_EDGE_GAP * inv, d * 0.4);
    edge.el.setAttribute('x1', edge.from.x.toFixed(2));
    edge.el.setAttribute('y1', edge.from.y.toFixed(2));
    edge.el.setAttribute('x2', (edge.to.x - (dx / d) * trim).toFixed(2));
    edge.el.setAttribute('y2', (edge.to.y - (dy / d) * trim).toFixed(2));
  }

  for (const group of state.groups) {
    if (!group._hullEl) continue;
    const hull = convexHull(group._members.map((m) => ({ x: m.x, y: m.y })));
    if (!hull.length) continue;
    const path = hull
      .map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
      .join(' ');
    group._hullEl.setAttribute('d', `${path} Z`);
  }
}

/* ------------------------------------------------------------- viewport */

function applyView() {
  const rect = els.svg.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  const w = view.baseW / view.zoom;
  const h = (w * rect.height) / rect.width;
  els.svg.setAttribute('viewBox',
    `${(view.cx - w / 2).toFixed(2)} ${(view.cy - h / 2).toFixed(2)} ${w.toFixed(2)} ${h.toFixed(2)}`);
  syncZoomScale();
}

/* Counter-scale strokes so edges, hulls, and dashes keep their screen
   width at every zoom level. Stroke widths sit on the layer groups and
   inherit; the arrow marker sizes from stroke-width, so it follows too.
   No-op while panning/resizing (zoom unchanged). */
let syncedZoom = 0;

function syncZoomScale() {
  if (!layers.nodes || view.zoom === syncedZoom) return;
  syncedZoom = view.zoom;
  const inv = 1 / view.zoom;
  layers.edges.setAttribute('stroke-width', (EDGE_WIDTH_MUTUAL * inv).toFixed(3));
  layers.oneway.setAttribute('stroke-width', (EDGE_WIDTH_ONEWAY * inv).toFixed(3));
  layers.oneway.setAttribute('stroke-dasharray',
    ONEWAY_DASH.map((step) => (step * inv).toFixed(3)).join(' '));
  layers.hulls.setAttribute('stroke-width', (HULL_PAD * inv).toFixed(2));
  render();
}

function toWorld(clientX, clientY) {
  const rect = els.svg.getBoundingClientRect();
  const w = view.baseW / view.zoom;
  const h = (w * rect.height) / rect.width;
  return {
    x: view.cx - w / 2 + ((clientX - rect.left) / rect.width) * w,
    y: view.cy - h / 2 + ((clientY - rect.top) / rect.height) * h,
  };
}

/* ---------------------------------------------------------- interaction */

let gesture = null;

function bindCanvas() {
  els.svg.addEventListener('pointerdown', (event) => {
    if (event.button !== 0) return;
    const nodeEl = event.target.closest?.('.u-node');
    const hullEl = event.target.closest?.('.u-hull');
    els.svg.setPointerCapture(event.pointerId);
    if (nodeEl) {
      const node = state.nodeById.get(nodeEl.dataset.id);
      if (!node) return;
      node.pinned = true;
      gesture = { type: 'node', node, moved: false, x: event.clientX, y: event.clientY };
    } else {
      const group = hullEl ? state.groupById.get(hullEl.dataset.group) : null;
      if (group) group._ignoreClick = false;
      gesture = {
        type: group ? 'group' : 'pan', group,
        moved: false, x: event.clientX, y: event.clientY,
      };
      els.svg.classList.add('is-panning');
    }
  });

  els.svg.addEventListener('pointermove', (event) => {
    if (!gesture) return;
    const dx = event.clientX - gesture.x;
    const dy = event.clientY - gesture.y;
    if (Math.abs(dx) + Math.abs(dy) > 3) gesture.moved = true;
    if (gesture.moved && gesture.type === 'group') gesture.group._ignoreClick = true;

    if (gesture.type === 'node') {
      const point = toWorld(event.clientX, event.clientY);
      gesture.node.x = point.x;
      gesture.node.y = point.y;
      gesture.node.vx = 0;
      gesture.node.vy = 0;
      if (reducedMotion) render();
      else reheat(0.35);
    } else {
      const rect = els.svg.getBoundingClientRect();
      const w = view.baseW / view.zoom;
      view.cx -= (dx / rect.width) * w;
      view.cy -= (dy / rect.width) * w;
      gesture.x = event.clientX;
      gesture.y = event.clientY;
      applyView();
    }
  });

  const endGesture = (event) => {
    if (!gesture) return;
    if (gesture.type === 'node') {
      gesture.node.pinned = false;
      if (!gesture.moved) selectNode(gesture.node, { sticky: true });
      else if (reducedMotion) render();
      else reheat(0.25);
    } else if (gesture.type === 'pan' && !gesture.moved) {
      clearSelection();
    }
    els.svg.classList.remove('is-panning');
    if (event?.pointerId != null && els.svg.hasPointerCapture?.(event.pointerId)) {
      els.svg.releasePointerCapture(event.pointerId);
    }
    gesture = null;
  };
  els.svg.addEventListener('pointerup', endGesture);
  els.svg.addEventListener('pointercancel', endGesture);

  els.svg.addEventListener('wheel', (event) => {
    event.preventDefault();
    const before = toWorld(event.clientX, event.clientY);
    const factor = Math.exp(-event.deltaY * 0.0016);
    view.zoom = Math.min(9, Math.max(0.22, view.zoom * factor));
    const after = toWorld(event.clientX, event.clientY);
    view.cx += before.x - after.x;
    view.cy += before.y - after.y;
    applyView();
  }, { passive: false });

  els.svg.addEventListener('pointerover', (event) => {
    if (gesture || state.sticky) return;
    const nodeEl = event.target.closest?.('.u-node');
    if (!nodeEl) return;
    const node = state.nodeById.get(nodeEl.dataset.id);
    if (node) selectNode(node, { sticky: false });
  });

  els.svg.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    const nodeEl = event.target.closest?.('.u-node');
    const hullEl = event.target.closest?.('.u-hull');
    if (nodeEl) {
      event.preventDefault();
      const node = state.nodeById.get(nodeEl.dataset.id);
      if (node) selectNode(node, { sticky: true });
    } else if (hullEl) {
      event.preventDefault();
      const group = state.groupById.get(hullEl.dataset.group);
      if (group) selectGroup(group, { sticky: true });
    }
  });

  if (typeof ResizeObserver === 'function') {
    new ResizeObserver(() => applyView()).observe(els.svg);
  } else {
    window.addEventListener('resize', applyView);
  }
}

/* -------------------------------------------------------------- filters */

function bindControls() {
  els.search.addEventListener('input', () => {
    state.filters.query = els.search.value;
    applyFilters();
  });
  els.sourceFilter.addEventListener('change', () => {
    state.filters.source = els.sourceFilter.value;
    applyFilters();
  });
  els.toggleOneway.addEventListener('change', () => {
    state.filters.oneway = els.toggleOneway.checked;
    applyFilters();
  });
  els.toggleUnmerged.addEventListener('change', () => {
    state.filters.unmergedOnly = els.toggleUnmerged.checked;
    applyFilters();
  });
}

function populateSourceFilter() {
  const options = ['<option value="">All sources</option>'];
  for (const source of state.sources) {
    options.push(`<option value="${esc(source.id)}">${esc(source.title)}</option>`);
  }
  els.sourceFilter.innerHTML = options.join('');
}

function applyFilters() {
  if (!layers.nodes) return;
  const { query, source, oneway, unmergedOnly } = state.filters;
  const needle = query.trim().toLowerCase();
  let visible = 0;

  for (const node of state.nodes) {
    const group = node.groupId ? state.groupById.get(node.groupId) : null;
    const canonical = group?.canonicalStatement || '';
    const matches = (!needle
      || node.statement.toLowerCase().includes(needle)
      || canonical.toLowerCase().includes(needle))
      && (!source || node.sourceId === source)
      && (!unmergedOnly || !node.groupId);
    node.dim = !matches;
    if (matches) visible += 1;
    node.el.classList.toggle('is-dim', node.dim);
    node.el.classList.toggle('is-source-match', Boolean(source) && node.sourceId === source);
  }

  for (const edge of state.mutualEdges) {
    edge.el.classList.toggle('is-dim', edge.a.dim || edge.b.dim);
  }
  /* SVG groups ignore the HTML `hidden` attribute — toggle display instead. */
  layers.oneway.style.display = oneway ? '' : 'none';
  if (oneway) {
    for (const edge of state.oneWayEdges) {
      edge.el.classList.toggle('is-dim', edge.from.dim || edge.to.dim);
    }
  }
  layers.hulls.style.display = unmergedOnly ? 'none' : '';
  if (!unmergedOnly) {
    for (const group of state.groups) {
      if (!group._hullEl) continue;
      const anyVisible = group._members.some((member) => !member.dim);
      group._hullEl.classList.toggle('is-dim', !anyVisible);
    }
  }

  updateStatus(visible);
}

function updateStatus(visible) {
  const total = state.nodes.length;
  const parts = [];
  parts.push(visible === total ? `${total} KCs` : `${visible} of ${total} KCs`);
  parts.push(`${state.mutualEdges.length} mutual links`);
  if (state.oneWayEdges.length) parts.push(`${state.oneWayEdges.length} one-way`);
  if (state.grouping?.stale) {
    parts.unshift(`${state.grouping.id} is stale — rebuild required`);
    els.status.classList.add('is-stale');
    els.status.title = (state.grouping.stale_reasons || []).join('; ');
  } else {
    els.status.classList.remove('is-stale');
    els.status.title = '';
  }
  els.status.textContent = parts.join(' · ');
}

/* --------------------------------------------------------- detail panel */

function selectNode(node, { sticky }) {
  if (sticky) {
    state.sticky = true;
  } else if (state.sticky) {
    return;
  }
  if (state.selectedId === node.id && sticky === state.sticky) {
    renderSelectionMarks();
    return;
  }
  state.selectedId = node.id;
  state.selectedGroupId = node.groupId;
  renderSelectionMarks();
  renderDetail(node.groupId ? state.groupById.get(node.groupId) : null, node);
}

function selectGroup(group, { sticky }) {
  if (!group) return;
  if (sticky) {
    state.sticky = true;
  } else if (state.sticky) {
    return;
  }
  state.selectedId = null;
  state.selectedGroupId = String(group.id);
  renderSelectionMarks();
  renderDetail(group, null);
}

function clearSelection() {
  state.sticky = false;
  state.selectedId = null;
  state.selectedGroupId = null;
  renderSelectionMarks();
  els.detail.innerHTML = '<p class="universe-detail__placeholder">Click a node to inspect that KC, or click a composite field to inspect the whole composite. Drag the background to pan, scroll to zoom, drag a node to nudge the layout.</p>';
}

function renderSelectionMarks() {
  for (const node of state.nodes) {
    node.el.classList.toggle('is-selected', node.id === state.selectedId && state.sticky);
  }
  for (const group of state.groups) {
    group._hullEl?.classList.toggle(
      'is-selected', String(group.id) === state.selectedGroupId && state.sticky,
    );
  }
}

function axisChip(label, value) {
  if (!value) return '';
  return `<span class="universe-axis">${esc(label)} · ${esc(value)}</span>`;
}

function detailMembers(group, selectedNode) {
  const members = group
    ? (group.members || []).map((id) => state.nodeById.get(String(id))).filter(Boolean)
    : (selectedNode ? [selectedNode] : []);
  if (!selectedNode) return members;
  return [selectedNode, ...members.filter((member) => member.id !== selectedNode.id)];
}

function membersBySource(members) {
  const sources = new Map();
  for (const member of members) {
    const key = member.sourceId || '__unlinked__';
    if (!sources.has(key)) {
      sources.set(key, {
        id: member.sourceId,
        title: member.sourceTitle || 'Unlinked source',
        members: [],
      });
    }
    sources.get(key).members.push(member);
  }
  return [...sources.values()];
}

function memberCard(member, index, selectedNode) {
  const selected = member.id === selectedNode?.id;
  return `
    <article class="universe-member-card${selected ? ' is-selected' : ''}" data-member-id="${esc(member.id)}">
      <div class="universe-member-card__heading">
        <span class="universe-detail__label">${selected ? 'Selected KC' : `KC ${index + 1}`}</span>
        <div class="universe-detail__axes">
          ${axisChip('Knowledge', member.knowledge)}
          ${axisChip('Modality', member.modality)}
        </div>
      </div>
      <h3 class="universe-member-card__statement">${esc(member.statement) || '<em>No statement</em>'}</h3>
      <div class="universe-member-card__field">
        <span class="universe-detail__label">Task</span>
        <p class="universe-detail__body">${esc(member.task) || '—'}</p>
      </div>
      <div class="universe-member-card__field">
        <span class="universe-detail__label">Answer</span>
        <p class="universe-detail__body">${esc(member.answer) || '—'}</p>
      </div>
    </article>
  `;
}

function renderDetail(group, selectedNode) {
  const members = detailMembers(group, selectedNode);
  const sourceGroups = membersBySource(members);
  const displayStatement = group?.canonicalStatement || selectedNode?.statement || '';
  const canonicalNotice = group && !group.canonicalStatement
    ? `<p class="universe-detail__muted">${group.canonicalStatus === 'unsure'
      ? `No canonical statement was produced.${group.canonicalReason ? ` ${esc(group.canonicalReason)}` : ''}`
      : 'Canonical statement has not been produced yet.'}</p>`
    : '';
  let memberIndex = 0;
  const sourceSections = sourceGroups.map((source) => `
    <section class="universe-source-group">
      <div class="universe-source-group__heading">
        <span class="universe-detail__label">Source</span>
        ${source.id
          ? `<a class="universe-detail__source-link" href="/sources?id=${encodeURIComponent(source.id)}">${esc(source.title)}</a>`
          : `<span class="universe-detail__muted">${esc(source.title)}</span>`}
      </div>
      <div class="universe-member-cards">
        ${source.members.map((member) => memberCard(member, memberIndex++, selectedNode)).join('')}
      </div>
    </section>
  `).join('');

  els.detail.innerHTML = `
    <span class="universe-detail__kicker">${group ? 'Composite knowledge component' : 'Knowledge component'}</span>
    <h2 class="universe-detail__statement">${esc(displayStatement) || '<em>No canonical statement</em>'}</h2>
    ${canonicalNotice}
    <p class="universe-detail__summary">${group
      ? `${members.length} KCs · ${sourceGroups.length} source${sourceGroups.length === 1 ? '' : 's'}`
      : 'Unitary KC · not part of a committed composite'}</p>
    <div class="universe-detail__members">
      ${sourceSections || '<p class="universe-detail__muted">No member records found.</p>'}
    </div>
  `;
}

/* ----------------------------------------------------------------- boot */

function showOverlay(html) {
  els.overlayMessage.innerHTML = html;
  els.overlay.hidden = false;
}

function hideOverlay() {
  els.overlay.hidden = true;
}

async function boot() {
  els.emptyNote.hidden = true;
  showOverlay('Loading universe…');
  els.status.textContent = 'Loading universe…';

  let data;
  try {
    data = await fetchJSON('/api/universe');
  } catch (error) {
    showOverlay(`
      Could not load the universe. ${esc(error.message)}<br>
      <button class="button" type="button" data-retry>Try again</button>
    `);
    els.status.textContent = 'Failed to load the universe.';
    els.overlay.querySelector('[data-retry]')?.addEventListener('click', boot, { once: true });
    return;
  }

  buildGraph(data);
  mountScaffold();
  mountGraph();
  bindCanvas();
  applyView();

  els.compositeCount.textContent = `Composite KCs · ${state.groups.length}`;
  populateSourceFilter();
  applyFilters();

  if (!state.nodes.length) {
    showOverlay('No knowledge components in the ledger yet. Ingest a source and run the pipeline to populate the universe.');
    els.status.textContent = 'No knowledge components yet.';
    return;
  }
  hideOverlay();
  els.emptyNote.hidden = state.hasVerdicts;

  if (reducedMotion) settleInstantly();
  else reheat(1);
}

bindControls();
boot();
