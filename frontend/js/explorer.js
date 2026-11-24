/**
 * DOCUMIND KNOWLEDGE EXPLORER CONTROLLER
 * Canvas-based interactive Force-Directed Knowledge Graph.
 * Supports physics layout, drag & drop, zooming, keyword search,
 * entity category filtering, and interactive relationship jumping.
 */

let allNodes = [];
let allLinks = [];
let graphNodes = [];
let graphLinks = [];
let selectedNode = null;
let hoveredNode = null;
let isDragging = false;
let draggedNode = null;
let zoom = 1.0;
let panX = 0;
let panY = 0;
let animationId = null;
let activeCategoryFilter = "all";
let activeSearchFilter = "";

const TYPE_COLORS = {
  statute: "#2563eb",
  organization: "#7c3aed",
  person: "#059669",
  temporal_date: "#d97706",
  concept: "#0f172a"
};

document.addEventListener("DOMContentLoaded", async () => {
  const authenticated = await window.authManager.requireAuth();
  if (!authenticated) return;

  setupCanvas();
  setupFilterControls();
  await loadDocumentsDropdown();
  await fetchGraphData("all", false);
  setupControls();
});

async function loadDocumentsDropdown() {
  try {
    const data = await window.apiClient.get("/documents");
    const sel = document.getElementById("select-graph-document");
    (data.documents || []).forEach(d => {
      const opt = document.createElement("option");
      opt.value = d.id;
      opt.textContent = `${d.name} (${d.chunk_count} chunks)`;
      sel.appendChild(opt);
    });

    sel.addEventListener("change", (e) => {
      fetchGraphData(e.target.value, false);
    });

    document.getElementById("btn-refresh-graph")?.addEventListener("click", () => {
      fetchGraphData(sel.value, true);
    });
  } catch (err) {
    console.error("[Explorer] Error loading documents:", err);
  }
}

async function fetchGraphData(docId, forceRefresh = false) {
  const statsBadge = document.getElementById("graph-stats-badge");
  const emptyOverlay = document.getElementById("graph-empty-overlay");

  if (statsBadge) statsBadge.textContent = forceRefresh ? "Re-extracting entities & relations..." : "Extracting graph...";
  if (emptyOverlay) emptyOverlay.style.display = "none";

  try {
    let url = `/explorer/graph?document_id=${docId || 'all'}`;
    if (forceRefresh) url += "&refresh=true";

    const data = await window.apiClient.get(url);

    allNodes = data.nodes || [];
    allLinks = data.links || [];

    if (allNodes.length === 0) {
      if (emptyOverlay) {
        emptyOverlay.style.display = "flex";
        const emptyMsg = document.getElementById("graph-empty-msg");
        if (emptyMsg && data.summary) emptyMsg.textContent = data.summary;
      }
      if (statsBadge) statsBadge.textContent = "0 Entities Found";
      clearGraphCanvas();
      return;
    }

    applyFilters();

    if (statsBadge) {
      const cacheNote = data.cached ? " (Cached)" : "";
      statsBadge.textContent = `${allNodes.length} Entities • ${allLinks.length} Relations${cacheNote}`;
    }
  } catch (err) {
    console.error("[Explorer] Failed to load graph:", err);
    if (statsBadge) statsBadge.textContent = "Failed to load graph.";
  }
}

function setupFilterControls() {
  // Search input
  const searchInput = document.getElementById("input-search-node");
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener("input", (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        activeSearchFilter = e.target.value.trim().toLowerCase();
        applyFilters();
      }, 150);
    });
  }

  // Category chips
  const chips = document.querySelectorAll(".graph-filter-chip");
  chips.forEach(chip => {
    chip.addEventListener("click", () => {
      chips.forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      activeCategoryFilter = chip.dataset.type;
      applyFilters();
    });
  });
}

function applyFilters() {
  let filteredNodes = allNodes;

  // Filter by category
  if (activeCategoryFilter !== "all") {
    filteredNodes = filteredNodes.filter(n => n.type === activeCategoryFilter);
  }

  // Filter by search keyword
  if (activeSearchFilter) {
    filteredNodes = filteredNodes.filter(n => 
      (n.label && n.label.toLowerCase().includes(activeSearchFilter)) ||
      (n.description && n.description.toLowerCase().includes(activeSearchFilter))
    );
  }

  const allowedIds = new Set(filteredNodes.map(n => n.id));
  const filteredLinks = allLinks.filter(l => allowedIds.has(l.source) && allowedIds.has(l.target));

  initGraphLayout(filteredNodes, filteredLinks);
}

function clearGraphCanvas() {
  const canvas = document.getElementById("knowledge-graph-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (animationId) cancelAnimationFrame(animationId);
}

function initGraphLayout(nodes, links) {
  const canvas = document.getElementById("knowledge-graph-canvas");
  const width = canvas.width;
  const height = canvas.height;

  // Initialize node positions in a circle around center
  const radius = Math.min(width, height) * 0.35;
  const count = nodes.length;

  graphNodes = nodes.map((n, i) => {
    const angle = (i / (count || 1)) * 2 * Math.PI;
    return {
      ...n,
      x: width / 2 + radius * Math.cos(angle) + (Math.random() - 0.5) * 40,
      y: height / 2 + radius * Math.sin(angle) + (Math.random() - 0.5) * 40,
      vx: 0,
      vy: 0,
      radius: n.type === "statute" ? 18 : 14
    };
  });

  // Map links to node objects
  const nodeMap = new Map(graphNodes.map(n => [n.id, n]));
  graphLinks = links.map(l => ({
    ...l,
    sourceNode: nodeMap.get(l.source),
    targetNode: nodeMap.get(l.target)
  })).filter(l => l.sourceNode && l.targetNode);

  if (animationId) cancelAnimationFrame(animationId);
  runSimulation();
}

function runSimulation() {
  const canvas = document.getElementById("knowledge-graph-canvas");
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;

  function step() {
    // 1. Physics: Repulsion between all nodes
    for (let i = 0; i < graphNodes.length; i++) {
      for (let j = i + 1; j < graphNodes.length; j++) {
        const a = graphNodes[i];
        const b = graphNodes[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;

        if (dist < 260) {
          const force = (260 - dist) / 260 * 1.5;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;

          if (a !== draggedNode) { a.vx -= fx; a.vy -= fy; }
          if (b !== draggedNode) { b.vx += fx; b.vy += fy; }
        }
      }
    }

    // 2. Physics: Spring attraction along links
    graphLinks.forEach(link => {
      const a = link.sourceNode;
      const b = link.targetNode;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const targetDist = 120;
      const force = (dist - targetDist) * 0.035;

      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;

      if (a !== draggedNode) { a.vx -= fx; a.vy -= fy; }
      if (b !== draggedNode) { b.vx += fx; b.vy += fy; }
    });

    // 3. Center Gravity & Damping
    const centerX = width / 2;
    const centerY = height / 2;

    graphNodes.forEach(node => {
      if (node !== draggedNode) {
        node.vx += (centerX - node.x) * 0.005;
        node.vy += (centerY - node.y) * 0.005;
        node.vx *= 0.82;
        node.vy *= 0.82;
        node.x += node.vx;
        node.y += node.vy;
      }
    });

    // 4. Render
    renderCanvas(ctx, width, height);
    animationId = requestAnimationFrame(step);
  }

  step();
}

function renderCanvas(ctx, width, height) {
  ctx.clearRect(0, 0, width, height);

  ctx.save();
  ctx.translate(panX + width / 2, panY + height / 2);
  ctx.scale(zoom, zoom);
  ctx.translate(-width / 2, -height / 2);

  // Draw links
  graphLinks.forEach(link => {
    const isHighlighted = (selectedNode && (link.sourceNode === selectedNode || link.targetNode === selectedNode));
    ctx.beginPath();
    ctx.moveTo(link.sourceNode.x, link.sourceNode.y);
    ctx.lineTo(link.targetNode.x, link.targetNode.y);
    ctx.strokeStyle = isHighlighted ? "#2563eb" : "#e2e8f0";
    ctx.lineWidth = isHighlighted ? 2.5 : 1.2;
    ctx.stroke();

    // Draw relation label
    if (isHighlighted || zoom > 0.8) {
      const midX = (link.sourceNode.x + link.targetNode.x) / 2;
      const midY = (link.sourceNode.y + link.targetNode.y) / 2;
      ctx.fillStyle = isHighlighted ? "#1e40af" : "#94a3b8";
      ctx.font = "9px Inter, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(link.relation, midX, midY - 3);
    }
  });

  // Draw nodes
  graphNodes.forEach(node => {
    const isSelected = node === selectedNode;
    const isHovered = node === hoveredNode;
    const color = TYPE_COLORS[node.type] || "#0f172a";

    // Outer glow for selected or hovered
    if (isSelected || isHovered) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.radius + 6, 0, 2 * Math.PI);
      ctx.fillStyle = "rgba(37, 99, 235, 0.15)";
      ctx.fill();
    }

    // Node body
    ctx.beginPath();
    ctx.arc(node.x, node.y, node.radius, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();

    // Node label
    ctx.fillStyle = isSelected ? "#2563eb" : "#0f172a";
    ctx.font = isSelected ? "bold 11px Inter, system-ui, sans-serif" : "10px Inter, system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(node.label, node.x, node.y + node.radius + 13);
  });

  ctx.restore();
}

function setupCanvas() {
  const canvas = document.getElementById("knowledge-graph-canvas");
  const container = canvas.parentElement;

  function resize() {
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
  }
  resize();
  window.addEventListener("resize", resize);

  // Mouse interaction
  canvas.addEventListener("mousedown", (e) => {
    const rect = canvas.getBoundingClientRect();
    const pos = screenToWorld(e.clientX - rect.left, e.clientY - rect.top, canvas.width, canvas.height);
    const clicked = findNodeAt(pos.x, pos.y);

    if (clicked) {
      isDragging = true;
      draggedNode = clicked;
      selectNode(clicked);
    }
  });

  window.addEventListener("mousemove", (e) => {
    const rect = canvas.getBoundingClientRect();
    const pos = screenToWorld(e.clientX - rect.left, e.clientY - rect.top, canvas.width, canvas.height);

    if (isDragging && draggedNode) {
      draggedNode.x = pos.x;
      draggedNode.y = pos.y;
    } else {
      hoveredNode = findNodeAt(pos.x, pos.y);
      canvas.style.cursor = hoveredNode ? "pointer" : "default";
    }
  });

  window.addEventListener("mouseup", () => {
    isDragging = false;
    draggedNode = null;
  });

  // Wheel zoom
  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.08 : 0.92;
    zoom = Math.max(0.4, Math.min(2.5, zoom * factor));
  });
}

function screenToWorld(sx, sy, width, height) {
  const x = (sx - (panX + width / 2)) / zoom + width / 2;
  const y = (sy - (panY + height / 2)) / zoom + height / 2;
  return { x, y };
}

function findNodeAt(wx, wy) {
  for (let i = graphNodes.length - 1; i >= 0; i--) {
    const n = graphNodes[i];
    const dx = n.x - wx;
    const dy = n.y - wy;
    if (Math.sqrt(dx * dx + dy * dy) <= n.radius + 4) {
      return n;
    }
  }
  return null;
}

function selectNode(node) {
  selectedNode = node;
  const drawer = document.getElementById("inspector-drawer");
  document.getElementById("inspector-entity-title").textContent = node.label;
  document.getElementById("inspector-description").textContent = node.description || "No description recorded.";

  const badgeEl = document.getElementById("inspector-badge");
  badgeEl.innerHTML = `<span class="badge-auth ${node.type === 'statute' ? 'legal' : 'web'}">${node.type.toUpperCase()}</span>`;

  // Connected relations
  const listEl = document.getElementById("inspector-relations-list");
  listEl.innerHTML = "";

  const connectedLinks = graphLinks.filter(l => l.sourceNode === node || l.targetNode === node);
  if (connectedLinks.length === 0) {
    listEl.innerHTML = '<div style="font-size:0.8125rem;color:var(--text-muted);">No linked relationships recorded in current view.</div>';
  } else {
    connectedLinks.forEach(l => {
      const isOutgoing = l.sourceNode === node;
      const otherNode = isOutgoing ? l.targetNode : l.sourceNode;
      const div = document.createElement("div");
      div.className = "inspector-relation-card";
      div.style.background = "#f8fafc";
      div.style.border = "1px solid var(--border-color)";
      div.style.borderRadius = "var(--radius-sm)";
      div.style.padding = "8px 10px";
      div.style.fontSize = "0.8125rem";
      div.style.cursor = "pointer";
      div.style.transition = "background 0.15s ease";

      div.innerHTML = `
        <div style="display:flex;align-items:center;justify-content:space-between;">
          <div><strong>${escapeHtml(node.label)}</strong> <span style="color:var(--primary);font-weight:600;">${escapeHtml(l.relation)}</span> <strong>${escapeHtml(otherNode.label)}</strong></div>
          <span style="font-size:0.75rem;color:var(--primary);font-weight:600;">Jump</span>
        </div>
        ${l.evidence ? `<div style="color:var(--text-muted);font-size:0.75rem;margin-top:4px;font-style:italic;">"${escapeHtml(l.evidence)}"</div>` : ''}
      `;

      // Jump to other node on click!
      div.addEventListener("click", () => {
        centerOnNode(otherNode);
        selectNode(otherNode);
      });

      listEl.appendChild(div);
    });
  }

  drawer.classList.add("open");
}

function centerOnNode(node) {
  const canvas = document.getElementById("knowledge-graph-canvas");
  if (!canvas || !node) return;
  panX = canvas.width / 2 - node.x;
  panY = canvas.height / 2 - node.y;
}

function setupControls() {
  document.getElementById("btn-close-inspector")?.addEventListener("click", () => {
    document.getElementById("inspector-drawer")?.classList.remove("open");
    selectedNode = null;
  });

  document.getElementById("btn-zoom-in")?.addEventListener("click", () => {
    zoom = Math.min(2.5, zoom * 1.2);
  });
  document.getElementById("btn-zoom-out")?.addEventListener("click", () => {
    zoom = Math.max(0.4, zoom / 1.2);
  });
  document.getElementById("btn-reset-zoom")?.addEventListener("click", () => {
    zoom = 1.0;
    panX = 0;
    panY = 0;
  });
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
