/**
 * DOCUMIND ACTION STUDIO CONTROLLER
 * Loads available documents and research dossiers, triggers artifact generation,
 * persists decision artifacts to Supabase, allows editing, reopening, and exporting.
 */

let currentArtifact = null;
let savedArtifacts = [];

document.addEventListener("DOMContentLoaded", async () => {
  const authenticated = await window.authManager.requireAuth();
  if (!authenticated) return;

  setupModeTabs();
  await loadSourcesDropdown();
  await loadSavedArtifacts();
  setupActionGenerator();
});

function setupModeTabs() {
  const tabCreate = document.getElementById("tab-btn-create");
  const tabSaved = document.getElementById("tab-btn-saved");
  const viewCreate = document.getElementById("view-create-artifact");
  const viewSaved = document.getElementById("view-saved-artifacts");

  tabCreate?.addEventListener("click", () => {
    tabCreate.classList.add("active");
    tabSaved.classList.remove("active");
    viewCreate.style.display = "block";
    viewSaved.style.display = "none";
  });

  tabSaved?.addEventListener("click", () => {
    tabSaved.classList.add("active");
    tabCreate.classList.remove("active");
    viewCreate.style.display = "none";
    viewSaved.style.display = "block";
    loadSavedArtifacts();
  });

  document.getElementById("btn-refresh-saved")?.addEventListener("click", () => {
    loadSavedArtifacts();
  });
}

async function loadSourcesDropdown() {
  const sel = document.getElementById("select-action-source");
  sel.innerHTML = '<option value="">Select Knowledge Source...</option>';

  try {
    // 1. Documents
    const docsData = await window.apiClient.get("/documents");
    const docs = (docsData.documents || []).filter(d => d.status === "ready");

    if (docs.length > 0) {
      const docGroup = document.createElement("optgroup");
      docGroup.label = "Knowledge Base Documents";
      docs.forEach(d => {
        const opt = document.createElement("option");
        opt.value = `doc:${d.id}`;
        opt.textContent = d.name;
        docGroup.appendChild(opt);
      });
      sel.appendChild(docGroup);
    }

    // 2. Research Reports
    const resData = await window.apiClient.get("/research/history");
    const reports = resData.reports || [];
    if (reports.length > 0) {
      const repGroup = document.createElement("optgroup");
      repGroup.label = "Research Studio Reports";
      reports.forEach(r => {
        const opt = document.createElement("option");
        opt.value = `res:${r.id}`;
        opt.textContent = r.title || r.topic;
        repGroup.appendChild(opt);
      });
      sel.appendChild(repGroup);
    }
  } catch (err) {
    console.error("[ActionStudio] Error loading sources:", err);
  }
}

async function loadSavedArtifacts() {
  const listContainer = document.getElementById("saved-artifacts-list");
  const pill = document.getElementById("saved-count-pill");

  try {
    const data = await window.apiClient.get("/action/artifacts");
    savedArtifacts = data.artifacts || [];

    if (pill) pill.textContent = savedArtifacts.length;

    if (savedArtifacts.length === 0) {
      listContainer.innerHTML = `
        <div class="empty-state" style="padding:40px 16px;">
          <div class="empty-title">No Saved Artifacts</div>
          <div class="empty-subtitle">Generate an implementation plan or checklist in the Create tab and it will appear here.</div>
        </div>
      `;
      return;
    }

    let html = '<div style="display:flex;flex-direction:column;gap:12px;">';
    savedArtifacts.forEach(art => {
      const dateStr = art.created_at ? new Date(art.created_at).toLocaleDateString() : "Recent";
      html += `
        <div class="card" style="padding:16px 20px;display:flex;align-items:center;justify-content:space-between;border:1px solid var(--border-color);margin:0;">
          <div>
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
              <span class="badge-auth legal" style="font-size:0.7rem;">${escapeHtml(art.artifact_type.toUpperCase())}</span>
              <h3 style="font-size:1.05rem;font-weight:700;margin:0;">${escapeHtml(art.title)}</h3>
            </div>
            <div style="font-size:0.8125rem;color:var(--text-muted);">
              Source: <strong>${escapeHtml(art.source_title || 'Workspace Knowledge')}</strong> • Saved on ${dateStr}
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <button type="button" class="btn btn-primary btn-sm btn-reopen-artifact" data-id="${art.id}">
              Open & Edit
            </button>
            <button type="button" class="btn btn-secondary btn-sm btn-delete-artifact" data-id="${art.id}" style="color:var(--danger);">
              Delete
            </button>
          </div>
        </div>
      `;
    });
    html += '</div>';
    listContainer.innerHTML = html;

    // Attach listeners
    listContainer.querySelectorAll(".btn-reopen-artifact").forEach(btn => {
      btn.addEventListener("click", () => {
        reopenArtifact(btn.getAttribute("data-id"));
      });
    });

    listContainer.querySelectorAll(".btn-delete-artifact").forEach(btn => {
      btn.addEventListener("click", () => {
        deleteArtifact(btn.getAttribute("data-id"));
      });
    });

  } catch (err) {
    console.error("[ActionStudio] Load saved error:", err);
    listContainer.innerHTML = `<div style="color:var(--danger);padding:16px;">Failed to load saved artifacts: ${escapeHtml(err.message)}</div>`;
  }
}

async function reopenArtifact(artifactId) {
  try {
    const data = await window.apiClient.get(`/action/artifacts/${artifactId}`);
    currentArtifact = data;

    // Switch to create tab to view artifact
    document.getElementById("tab-btn-create").click();
    document.getElementById("action-results").style.display = "block";
    document.getElementById("action-empty").style.display = "none";

    renderActionArtifact(data);
  } catch (err) {
    console.error("[ActionStudio] Reopen error:", err);
    alert("Could not open artifact: " + err.message);
  }
}

async function deleteArtifact(artifactId) {
  if (!confirm("Are you sure you want to permanently delete this decision artifact?")) return;
  try {
    await window.apiClient.delete(`/action/artifacts/${artifactId}`);
    await loadSavedArtifacts();
  } catch (err) {
    console.error("[ActionStudio] Delete error:", err);
    alert("Failed to delete artifact: " + err.message);
  }
}

function setupActionGenerator() {
  const btn = document.getElementById("btn-generate-action");
  btn.addEventListener("click", async () => {
    const artifactType = document.getElementById("select-artifact-type").value;
    const rawSource = document.getElementById("select-action-source").value;
    const instructions = document.getElementById("action-instructions-input").value.trim();

    if (!rawSource) {
      alert("Please select a knowledge source document or research report.");
      return;
    }

    const [sourceTypePrefix, sourceId] = rawSource.split(":");
    const sourceType = sourceTypePrefix === "res" ? "research" : "document";

    await executeActionGeneration(artifactType, sourceType, sourceId, instructions);
  });
}

async function executeActionGeneration(artifactType, sourceType, sourceId, instructions) {
  const loading = document.getElementById("action-loading");
  const resultsContainer = document.getElementById("action-results");
  const emptyState = document.getElementById("action-empty");

  loading.style.display = "block";
  resultsContainer.style.display = "none";
  emptyState.style.display = "none";

  try {
    const data = await window.apiClient.post("/action/generate", {
      artifact_type: artifactType,
      source_type: sourceType,
      source_id: sourceId,
      custom_instructions: instructions
    });

    currentArtifact = data;
    renderActionArtifact(data);
    resultsContainer.style.display = "block";

    // Refresh saved counter
    loadSavedArtifacts();

  } catch (err) {
    console.error("[ActionStudio] Generation error:", err);
    alert("Failed to generate action artifact: " + err.message);
    emptyState.style.display = "block";
  } finally {
    loading.style.display = "none";
  }
}

function renderActionArtifact(data) {
  const container = document.getElementById("action-results");
  const typeLabels = {
    plan: "Implementation Plan",
    checklist: "Action & Compliance Checklist",
    tasks: "Work Breakdown Structure",
    business_analysis: "Strategic & Risk Analysis",
    report: "Executive Decision Brief",
    study: "Study Material & Flashcards"
  };

  let html = `
    <div class="card" style="margin-bottom:24px;">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;border-bottom:1px solid var(--border-color);padding-bottom:16px;margin-bottom:20px;flex-wrap:wrap;gap:12px;">
        <div style="flex:1;min-width:300px;">
          <span class="badge-auth legal" style="margin-bottom:6px;">${typeLabels[data.artifact_type] || 'Action Artifact'}</span>
          <input type="text" id="edit-artifact-title" value="${escapeHtml(data.title || 'Decision Artifact')}" class="form-control" style="font-size:1.35rem;font-weight:700;margin:6px 0;border:none;border-bottom:1px dashed var(--border-color);border-radius:0;padding:4px 0;background:transparent;width:100%;">
          <div style="font-size:0.8125rem;color:var(--text-muted);">
            Source: <strong>${escapeHtml(data.source_title || 'Workspace Knowledge')}</strong> • ${data.created_at ? new Date(data.created_at).toLocaleString() : 'Just now'}
          </div>
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
          <button type="button" class="btn btn-primary btn-sm" id="btn-save-action-edits">
            Save Changes
          </button>
          <button type="button" class="btn btn-secondary btn-sm" id="btn-copy-action">
            Copy Markdown
          </button>
          <button type="button" class="btn btn-secondary btn-sm" id="btn-download-action">
            Download .md
          </button>
        </div>
      </div>

      <div style="margin-bottom:24px;">
        <h3 style="font-size:0.95rem;font-weight:600;margin-bottom:8px;text-transform:uppercase;color:var(--text-muted);">Operational Context & Objective</h3>
        <textarea id="edit-artifact-summary" class="form-control" rows="3" style="width:100%;font-size:0.925rem;line-height:1.6;border:1px solid var(--border-color);">${escapeHtml(data.executive_summary || '')}</textarea>
      </div>
  `;

  // Render Sections & Interactive Checklist Items
  (data.sections || []).forEach((sec, sIdx) => {
    html += `
      <div style="margin-bottom:24px;">
        <h3 style="font-size:1.05rem;font-weight:600;color:var(--text-main);margin-bottom:4px;">${escapeHtml(sec.heading || `Phase ${sIdx + 1}`)}</h3>
        ${sec.description ? `<p style="font-size:0.85rem;color:var(--text-muted);margin-bottom:12px;">${escapeHtml(sec.description)}</p>` : ''}
        <div>
    `;

    (sec.items || []).forEach((item, iIdx) => {
      const itemId = `check-${sIdx}-${iIdx}`;
      const isDone = item.status === "done";
      const prioClass = item.priority === 'High' ? 'failed' : item.priority === 'Medium' ? 'processing' : 'ready';

      html += `
        <div class="action-item-box ${isDone ? 'done' : ''}" id="box-${itemId}">
          <input type="checkbox" class="action-checkbox" id="${itemId}" ${isDone ? 'checked' : ''} onchange="toggleItemDone(${sIdx}, ${iIdx})">
          <div style="flex:1;">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
              <label for="${itemId}" class="action-item-text ${isDone ? 'done' : ''}" id="label-${itemId}" style="font-weight:600;font-size:0.9rem;cursor:pointer;">
                ${escapeHtml(item.name)}
              </label>
              <span class="badge badge-${prioClass}" style="font-size:0.7rem;padding:2px 6px;">${escapeHtml(item.priority || 'Normal')}</span>
            </div>
            <div style="font-size:0.8125rem;color:var(--text-secondary);line-height:1.45;">${escapeHtml(item.details || '')}</div>
          </div>
        </div>
      `;
    });

    html += `</div></div>`;
  });

  // Key Deliverables
  if (data.deliverables && data.deliverables.length > 0) {
    html += `
      <div style="background:#f8fafc;border:1px solid var(--border-color);border-radius:var(--radius-md);padding:16px;margin-top:20px;">
        <h4 style="font-size:0.875rem;font-weight:600;margin-bottom:8px;text-transform:uppercase;color:var(--text-muted);">Key Deliverables & Verification Gates</h4>
        <ul style="margin:0;padding-left:20px;font-size:0.875rem;color:var(--text-secondary);">
    `;
    data.deliverables.forEach(d => { html += `<li>${escapeHtml(d)}</li>`; });
    html += `</ul></div>`;
  }

  html += `</div>`;
  container.innerHTML = html;

  // Setup save edits button
  document.getElementById("btn-save-action-edits")?.addEventListener("click", async () => {
    if (!currentArtifact || !currentArtifact.id) return;
    const newTitle = document.getElementById("edit-artifact-title").value.trim();
    const newSummary = document.getElementById("edit-artifact-summary").value.trim();

    currentArtifact.title = newTitle;
    currentArtifact.executive_summary = newSummary;

    const btn = document.getElementById("btn-save-action-edits");
    btn.disabled = true;
    btn.textContent = "Saving...";

    try {
      await window.apiClient.put(`/action/artifacts/${currentArtifact.id}`, {
        title: newTitle,
        artifact_data: currentArtifact
      });
      btn.textContent = "Saved";
      setTimeout(() => { btn.disabled = false; btn.textContent = "Save Changes"; }, 1500);
    } catch (err) {
      console.error("[ActionStudio] Save error:", err);
      alert("Failed to save changes: " + err.message);
      btn.disabled = false;
      btn.textContent = "Save Changes";
    }
  });

  // Setup copy button
  document.getElementById("btn-copy-action")?.addEventListener("click", () => {
    if (!currentArtifact) return;
    const md = generateActionMarkdown(currentArtifact);
    navigator.clipboard.writeText(md).then(() => {
      const btn = document.getElementById("btn-copy-action");
      btn.textContent = "Copied";
      setTimeout(() => { btn.textContent = "Copy Markdown"; }, 1500);
    });
  });

  // Setup download button
  document.getElementById("btn-download-action")?.addEventListener("click", () => {
    if (!currentArtifact) return;
    const md = generateActionMarkdown(currentArtifact);
    const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const safeTitle = (currentArtifact.title || "action-plan").toLowerCase().replace(/[^a-z0-9]/g, "_");
    a.href = url;
    a.download = `${safeTitle}.md`;
    a.click();
    URL.revokeObjectURL(url);
  });
}

window.toggleItemDone = function(sIdx, iIdx) {
  const itemId = `check-${sIdx}-${iIdx}`;
  const cb = document.getElementById(itemId);
  const box = document.getElementById(`box-${itemId}`);
  const label = document.getElementById(`label-${itemId}`);

  if (currentArtifact && currentArtifact.sections && currentArtifact.sections[sIdx] && currentArtifact.sections[sIdx].items) {
    currentArtifact.sections[sIdx].items[iIdx].status = cb.checked ? "done" : "pending";
  }

  if (cb.checked) {
    box.classList.add("done");
    label.classList.add("done");
  } else {
    box.classList.remove("done");
    label.classList.remove("done");
  }
};

function generateActionMarkdown(data) {
  let md = `# ${data.title}\n`;
  md += `**Source:** ${data.source_title} | **Date:** ${data.created_at || new Date().toISOString()}\n\n`;
  md += `## Objective\n${data.executive_summary}\n\n`;

  (data.sections || []).forEach(sec => {
    md += `### ${sec.heading}\n${sec.description || ''}\n`;
    (sec.items || []).forEach(item => {
      const checkMark = item.status === "done" ? "[x]" : "[ ]";
      md += `- ${checkMark} **${item.name}** [${item.priority}]: ${item.details}\n`;
    });
    md += "\n";
  });

  if (data.deliverables) {
    md += `### Deliverables\n`;
    data.deliverables.forEach(d => { md += `- ${d}\n`; });
  }
  return md;
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
