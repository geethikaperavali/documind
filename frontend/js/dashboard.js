/**
 * DOCUMIND DASHBOARD CONTROLLER
 * Loads live database metrics, recent documents, and recent activity feed.
 */

document.addEventListener("DOMContentLoaded", async () => {
  // 1. Guard route: require authentication
  const authenticated = await window.authManager.requireAuth();
  if (!authenticated) return;

  // 2. Load dashboard data
  await loadDashboardStats();

  // 3. Setup Quick Upload modal if present
  setupQuickUpload();
});

async function loadDashboardStats() {
  const loadingIndicator = document.getElementById("stats-loading");
  if (loadingIndicator) loadingIndicator.style.display = "block";

  try {
    const data = await window.apiClient.get("/dashboard/stats");
    
    // Update metric cards
    const totalDocsEl = document.getElementById("metric-total-docs");
    if (totalDocsEl) totalDocsEl.textContent = data.total_documents ?? 0;

    const storageUsedEl = document.getElementById("metric-storage-used");
    if (storageUsedEl) storageUsedEl.textContent = data.storage_used_formatted || "0 B";

    const questionsAskedEl = document.getElementById("metric-questions-asked");
    if (questionsAskedEl) questionsAskedEl.textContent = data.questions_asked ?? 0;

    // Render Recent Documents
    renderRecentDocuments(data.recent_documents || []);

    // Render Recent Activity
    renderRecentActivity(data.recent_activity || []);

  } catch (error) {
    console.error("[Dashboard] Error loading metrics:", error);
    showDashboardError(error.message);
  } finally {
    if (loadingIndicator) loadingIndicator.style.display = "none";
  }
}

function renderRecentDocuments(docs) {
  const tbody = document.getElementById("recent-docs-tbody");
  const emptyState = document.getElementById("recent-docs-empty");
  if (!tbody) return;

  tbody.innerHTML = "";

  if (docs.length === 0) {
    if (emptyState) emptyState.style.display = "block";
    return;
  }
  if (emptyState) emptyState.style.display = "none";

  docs.forEach(doc => {
    const tr = document.createElement("tr");

    const statusClass = doc.status === "ready" ? "badge-ready" :
                        doc.status === "processing" ? "badge-processing" : "badge-failed";

    const dateStr = doc.created_at ? new Date(doc.created_at).toLocaleDateString(undefined, {
      month: "short", day: "numeric", year: "numeric"
    }) : "—";

    tr.innerHTML = `
      <td>
        <div style="display:flex;align-items:center;gap:10px;">
          <span class="badge-format">${(doc.file_type || "TXT").toUpperCase()}</span>
          <span style="font-weight:600;color:var(--text-main);">${escapeHtml(doc.name)}</span>
        </div>
      </td>
      <td>${formatFileSize(doc.file_size)}</td>
      <td><span class="badge ${statusClass}">${doc.status || "processing"}</span></td>
      <td>${doc.chunk_count || 0} chunks</td>
      <td>${dateStr}</td>
      <td style="text-align:right;">
        <a href="/chat.html" class="btn btn-secondary btn-sm" title="Ask DocuMind about this document">Ask AI</a>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderRecentActivity(activities) {
  const container = document.getElementById("recent-activity-container");
  const emptyState = document.getElementById("recent-activity-empty");
  if (!container) return;

  container.innerHTML = "";

  if (activities.length === 0) {
    if (emptyState) emptyState.style.display = "block";
    return;
  }
  if (emptyState) emptyState.style.display = "none";

  activities.forEach(item => {
    const div = document.createElement("div");
    div.className = "activity-item";

    const isUpload = item.type === "upload";
    const icon = isUpload
      ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>`
      : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>`;

    const timeAgo = formatTimeAgo(item.timestamp);

    div.innerHTML = `
      <div class="activity-icon-wrap">${icon}</div>
      <div class="activity-content">
        <div class="activity-title">${escapeHtml(item.title)}</div>
        <div class="activity-desc">${escapeHtml(item.description)}</div>
      </div>
      <div class="activity-time">${timeAgo}</div>
    `;
    container.appendChild(div);
  });
}

function setupQuickUpload() {
  const btn = document.getElementById("btn-quick-upload");
  if (btn) {
    btn.addEventListener("click", () => {
      window.location.href = window.CONFIG.ROUTES.DOCUMENTS;
    });
  }
}

function showDashboardError(msg) {
  const banner = document.getElementById("dashboard-error-banner");
  if (banner) {
    banner.textContent = msg;
    banner.style.display = "block";
  }
}

function formatFileSize(bytes) {
  if (!bytes) return "0 B";
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(2) + " MB";
}

function formatTimeAgo(dateStr) {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  const now = new Date();
  const seconds = Math.floor((now - date) / 1000);

  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
