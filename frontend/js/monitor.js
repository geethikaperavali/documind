/**
 * DOCUMIND LIVE MONITOR CONTROLLER
 * Manages surveillance watchlists, triggers live external sweeps,
 * toggles pause/resume, deletes topics, and renders alert history dossiers.
 */

let trackedTopics = [];

document.addEventListener("DOMContentLoaded", async () => {
  const authenticated = await window.authManager.requireAuth();
  if (!authenticated) return;

  setupTabs();
  setupAddTopicForm();
  await loadMonitoredTopics();
});

function setupTabs() {
  const tabTopics = document.getElementById("tab-btn-topics");
  const tabHistory = document.getElementById("tab-btn-history");
  const viewTopics = document.getElementById("view-watchlists");
  const viewHistory = document.getElementById("view-history");

  tabTopics?.addEventListener("click", () => {
    tabTopics.classList.add("active");
    tabHistory.classList.remove("active");
    viewTopics.style.display = "block";
    viewHistory.style.display = "none";
  });

  tabHistory?.addEventListener("click", () => {
    tabHistory.classList.add("active");
    tabTopics.classList.remove("active");
    viewTopics.style.display = "none";
    viewHistory.style.display = "block";
    loadSurveillanceLogs();
  });

  document.getElementById("btn-refresh-logs")?.addEventListener("click", () => {
    loadSurveillanceLogs();
  });
}

function setupAddTopicForm() {
  const form = document.getElementById("add-topic-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const input = document.getElementById("new-topic-input");
    const freq = document.getElementById("select-topic-frequency").value;
    const topic = input ? input.value.trim() : "";
    if (!topic) return;

    const btn = document.getElementById("btn-add-topic");
    btn.disabled = true;
    btn.textContent = "Tracking...";

    try {
      const res = await window.apiClient.post("/monitor/topics", {
        topic,
        frequency: freq
      });

      input.value = "";
      await loadMonitoredTopics();

    } catch (err) {
      console.error("[LiveMonitor] Add topic error:", err);
      alert("Failed to track topic: " + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "+ Track Topic";
    }
  });
}

async function loadMonitoredTopics() {
  const container = document.getElementById("topics-list-container");
  const countBadge = document.getElementById("topics-count-badge");

  try {
    const data = await window.apiClient.get("/monitor/topics");
    trackedTopics = data.topics || [];

    if (countBadge) countBadge.textContent = `${trackedTopics.length} Tracked`;

    if (trackedTopics.length === 0) {
      container.innerHTML = `
        <div class="empty-state" style="padding:48px 20px;">
          <div class="empty-title">No Tracked Topics</div>
          <div class="empty-subtitle">Add a law, regulatory body, or market topic above to monitor live updates automatically.</div>
        </div>
      `;
      return;
    }

    renderTopicsList(trackedTopics);

  } catch (err) {
    console.error("[LiveMonitor] Failed to load topics:", err);
  }
}

function renderTopicsList(topics) {
  const container = document.getElementById("topics-list-container");
  container.innerHTML = "";

  topics.forEach((t, idx) => {
    const card = document.createElement("div");
    card.className = "monitor-card";
    card.id = `card-topic-${idx}`;

    const isPaused = t.status === "paused";
    const statusBadgeClass = isPaused ? "badge-failed" : "badge-ready";
    const statusText = isPaused ? "Paused" : "Active Surveillance";
    const toggleActionText = isPaused ? "Resume" : "Pause";

    card.innerHTML = `
      <div class="monitor-card-header" style="flex-wrap:wrap;gap:12px;">
        <div style="flex:1;min-width:280px;">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
            <h4 style="font-size:1.1rem;font-weight:700;color:var(--text-main);margin:0;">${escapeHtml(t.topic)}</h4>
            <span class="badge ${statusBadgeClass}">${escapeHtml(statusText)}</span>
            <span class="badge" style="background:#f1f5f9;color:var(--text-secondary);">${escapeHtml((t.frequency || 'Daily').toUpperCase())}</span>
          </div>
          <div style="font-size:0.8125rem;color:var(--text-muted);margin-top:4px;">
            Last Checked: ${t.last_checked ? new Date(t.last_checked).toLocaleString() : 'Pending sweep'}
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
          <button type="button" class="btn btn-primary btn-sm btn-sweep-now" data-topic="${escapeHtml(t.topic)}" data-id="${t.id}">
            Run Sweep Now
          </button>
          <button type="button" class="btn btn-secondary btn-sm btn-toggle-status" data-id="${t.id}" data-current="${t.status || 'active'}">
            ${toggleActionText}
          </button>
          <button type="button" class="btn btn-secondary btn-sm btn-delete-topic" data-id="${t.id}" style="color:var(--danger);">
            Delete
          </button>
        </div>
      </div>

      <div class="monitor-delta-box" id="delta-box-${idx}" style="background:#f8fafc;border:1px solid var(--border-color);border-radius:var(--radius-sm);padding:14px;font-size:0.875rem;color:var(--text-secondary);margin-top:10px;">
        <em>Click "Run Sweep Now" to scan live gazettes, news, and regulatory feeds for this topic.</em>
      </div>
    `;

    container.appendChild(card);
  });

  // Attach sweep button handlers
  container.querySelectorAll(".btn-sweep-now").forEach((btn, idx) => {
    btn.addEventListener("click", async () => {
      const topicName = btn.getAttribute("data-topic");
      const topicId = btn.getAttribute("data-id");
      await executeTopicSweep(topicName, topicId, idx, btn);
    });
  });

  // Attach toggle pause/resume handlers
  container.querySelectorAll(".btn-toggle-status").forEach(btn => {
    btn.addEventListener("click", async () => {
      const topicId = btn.getAttribute("data-id");
      const current = btn.getAttribute("data-current");
      const newStatus = current === "paused" ? "active" : "paused";
      try {
        await window.apiClient.put(`/monitor/topics/${topicId}`, { status: newStatus });
        await loadMonitoredTopics();
      } catch (err) {
        alert("Failed to toggle status: " + err.message);
      }
    });
  });

  // Attach delete handlers
  container.querySelectorAll(".btn-delete-topic").forEach(btn => {
    btn.addEventListener("click", async () => {
      if (!confirm("Are you sure you want to stop tracking and delete this topic?")) return;
      const topicId = btn.getAttribute("data-id");
      try {
        await window.apiClient.delete(`/monitor/topics/${topicId}`);
        await loadMonitoredTopics();
      } catch (err) {
        alert("Failed to delete topic: " + err.message);
      }
    });
  });
}

async function executeTopicSweep(topic, topicId, cardIdx, btn) {
  const deltaBox = document.getElementById(`delta-box-${cardIdx}`);
  btn.disabled = true;
  deltaBox.innerHTML = '<div style="display:flex;align-items:center;gap:8px;"><div class="spinner" style="width:16px;height:16px;border-width:2px;"></div> Sweeping live external sources...</div>';

  try {
    const data = await window.apiClient.post("/monitor/check", {
      topic,
      topic_id: topicId
    });

    const isSignificant = data.change_level === "Significant Shift";
    const levelClass = isSignificant ? "badge-failed" : data.change_level === "Routine Update" ? "badge-processing" : "badge-ready";

    let sourcesHtml = "";
    (data.sources || []).forEach(s => {
      sourcesHtml += `<div style="font-size:0.75rem;margin-top:4px;">• <a href="${escapeHtml(s.url)}" target="_blank" rel="noopener noreferrer" style="color:var(--primary);text-decoration:none;">${escapeHtml(s.title)}</a> (${escapeHtml(s.domain || '')}, ${escapeHtml(s.published_date || 'Recent')})</div>`;
    });

    deltaBox.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
        <span class="badge ${levelClass}" style="font-size:0.75rem;font-weight:700;">${escapeHtml(data.change_level)}</span>
        <span style="font-size:0.75rem;color:var(--text-muted);">${new Date(data.checked_at).toLocaleTimeString()}</span>
      </div>
      <div style="font-weight:600;font-size:0.925rem;color:var(--text-main);margin-bottom:6px;">${escapeHtml(data.headline || '')}</div>
      <div style="line-height:1.5;margin-bottom:10px;">${escapeHtml(data.summary || '')}</div>
      ${sourcesHtml ? `<div style="border-top:1px solid var(--border-color);padding-top:8px;margin-top:8px;"><strong style="font-size:0.75rem;text-transform:uppercase;color:var(--text-muted);">Verified Citations:</strong>${sourcesHtml}</div>` : ''}
    `;

  } catch (err) {
    console.error("[LiveMonitor] Sweep failed:", err);
    deltaBox.innerHTML = `<span style="color:var(--danger);">Sweep failed: ${escapeHtml(err.message)}</span>`;
  } finally {
    btn.disabled = false;
  }
}

async function loadSurveillanceLogs() {
  const container = document.getElementById("monitor-logs-container");
  container.innerHTML = '<div style="text-align:center;padding:32px;color:var(--text-muted);">Loading logs...</div>';

  try {
    const data = await window.apiClient.get("/monitor/logs?limit=25");
    const logs = data.logs || [];

    if (logs.length === 0) {
      container.innerHTML = `
        <div class="empty-state" style="padding:40px 16px;">
          <div class="empty-title">No Surveillance Logs Recorded</div>
          <div class="empty-subtitle">Trigger a sweep or let the background monitor execute automated checks to populate logs.</div>
        </div>
      `;
      return;
    }

    let html = '<div style="display:flex;flex-direction:column;gap:14px;">';
    logs.forEach(log => {
      const isSignificant = log.change_level === "Significant Shift";
      const levelClass = isSignificant ? "badge-failed" : log.change_level === "Routine Update" ? "badge-processing" : "badge-ready";
      const logData = log.log_data || {};
      const sources = logData.sources || [];

      let sourcesSnippet = "";
      if (sources.length > 0) {
        sourcesSnippet = '<div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border-color);font-size:0.75rem;">';
        sources.slice(0, 3).forEach(s => {
          sourcesSnippet += `<div>• <a href="${escapeHtml(s.url)}" target="_blank" rel="noopener noreferrer" style="color:var(--primary);">${escapeHtml(s.title)}</a> (${escapeHtml(s.domain || '')})</div>`;
        });
        sourcesSnippet += '</div>';
      }

      html += `
        <div class="card" style="padding:16px 20px;border:1px solid var(--border-color);margin:0;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
            <div style="display:flex;align-items:center;gap:8px;">
              <span class="badge ${levelClass}" style="font-size:0.75rem;">${escapeHtml(log.change_level)}</span>
              <strong style="font-size:0.95rem;color:var(--text-main);">${escapeHtml(log.topic)}</strong>
            </div>
            <span style="font-size:0.75rem;color:var(--text-muted);">${new Date(log.created_at).toLocaleString()}</span>
          </div>
          <div style="font-weight:600;font-size:0.9rem;margin-bottom:4px;color:var(--text-main);">${escapeHtml(log.headline)}</div>
          <p style="font-size:0.85rem;line-height:1.5;color:var(--text-secondary);margin:0;">${escapeHtml(logData.summary || '')}</p>
          ${sourcesSnippet}
        </div>
      `;
    });
    html += '</div>';
    container.innerHTML = html;

  } catch (err) {
    console.error("[LiveMonitor] Load logs error:", err);
    container.innerHTML = `<div style="color:var(--danger);padding:16px;">Failed to load logs: ${escapeHtml(err.message)}</div>`;
  }
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
