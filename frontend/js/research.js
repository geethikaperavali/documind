/**
 * DOCUMIND UNIVERSAL RESEARCH STUDIO CONTROLLER
 * Supports universal research across 12+ domains, AI industry intelligence,
 * source quality audits, and interactive provenance inspection.
 */

let currentDossier = null;
let activeDomain = "general_universal";
let searchAbortController = null;
let loadingInterval = null;
let historyReportsCache = [];

document.addEventListener("DOMContentLoaded", async () => {
  const authenticated = await window.authManager.requireAuth();
  if (!authenticated) return;

  setupDomainPills();
  setupResearchForm();
  setupDossierTabs();
  setupCopyMarkdown();
  setupRegistryModal();
  setupViewModeToggle();
  setupHistoryHandlers();
  setupDepthSegmentedControl();
  setupSuggestedCards();
  setupNewSearchButton();
  loadResearchHistory();
});

/**
 * Domain filter pills
 */
function setupDomainPills() {
  const pills = document.querySelectorAll(".domain-pill, .domain-chip");
  pills.forEach(pill => {
    pill.addEventListener("click", () => {
      pills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      activeDomain = pill.dataset.domain;
    });
  });
}

/**
 * Output tab switching
 */
function setupDossierTabs() {
  const tabs = document.querySelectorAll(".dossier-tab");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

      tab.classList.add("active");
      const targetPane = document.getElementById(tab.dataset.tab);
      if (targetPane) targetPane.classList.add("active");
    });
  });
}

/**
 * Handles Research Query Submission
 */
function setupResearchForm() {
  const form = document.getElementById("research-form");
  const topicInput = document.getElementById("research-topic-input");
  const runBtn = document.getElementById("btn-run-research");

  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const topic = topicInput.value.trim();
    if (!topic) return;

    const depthEl = document.querySelector('input[name="research_depth"]:checked');
    const depth = depthEl ? depthEl.value : "comprehensive";

    // Abort previous in-flight search if user resubmits
    if (searchAbortController) {
      searchAbortController.abort();
    }
    searchAbortController = new AbortController();

    // Show progressive loading state
    setLoadingState(true);

    try {
      const payload = {
        topic,
        domain: activeDomain,
        depth
      };

      const report = await window.apiClient.request("/research/query", {
        method: "POST",
        body: JSON.stringify(payload),
        signal: searchAbortController.signal
      });
      currentDossier = report;
      renderDossierOutput(report);
      loadResearchHistory();
    } catch (err) {
      if (err.name === "AbortError") {
        console.log("[ResearchStudio] Investigation was cancelled by user.");
        return;
      }
      console.error("[ResearchStudio] Query error:", err);
      renderSearchError(err.message || "Failed to complete live investigation.");
    } finally {
      setLoadingState(false);
      searchAbortController = null;
    }
  });
}

function setLoadingState(loading) {
  const loadingEl = document.getElementById("research-loading");
  const resultsEl = document.getElementById("research-results-container");
  const emptyEl = document.getElementById("research-empty");
  const runBtn = document.getElementById("btn-run-research");
  const stepEl = document.getElementById("research-loading-step");

  if (loadingInterval) {
    clearInterval(loadingInterval);
    loadingInterval = null;
  }

  if (loading) {
    if (loadingEl) loadingEl.style.display = "block";
    if (resultsEl) resultsEl.style.display = "none";
    if (emptyEl) emptyEl.style.display = "none";
    if (runBtn) {
      runBtn.disabled = true;
      runBtn.innerHTML = `<span class="spinner-sm" style="display:inline-block;width:14px;height:14px;border:2px solid #fff;border-top-color:transparent;border-radius:50%;animation:spin 0.6s linear infinite;margin-right:6px;"></span> Searching...`;
    }

    const steps = [
      "Discovering live sources across official gazettes, registries & documentation...",
      "Resolving canonical provenance & validating authority tiers...",
      "Evaluating independent benchmark leaderboards & temporal provisions...",
      "Synthesizing structured intelligence dossier..."
    ];
    let stepIdx = 0;
    if (stepEl) stepEl.textContent = steps[0];
    loadingInterval = setInterval(() => {
      stepIdx = (stepIdx + 1) % steps.length;
      if (stepEl) stepEl.textContent = steps[stepIdx];
    }, 1800);
  } else {
    if (loadingEl) loadingEl.style.display = "none";
    if (runBtn) {
      runBtn.disabled = false;
      runBtn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg> <span>Investigate</span> <span class="kbd-badge">↵</span>`;
    }
  }
}

function renderSearchError(errorMessage) {
  const resultsEl = document.getElementById("research-results-container");
  const emptyEl = document.getElementById("research-empty");

  if (resultsEl) resultsEl.style.display = "none";
  if (emptyEl) {
    emptyEl.style.display = "block";
    emptyEl.innerHTML = `
      <div style="text-align:center;padding:48px 24px;">
        <div style="display:flex;justify-content:center;margin-bottom:12px;color:var(--danger);">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        </div>
        <h3 style="font-size:1.1rem;color:var(--danger);margin-bottom:8px;">Investigation Notice</h3>
        <p style="color:var(--text-secondary);max-width:480px;margin:0 auto 16px;font-size:0.9rem;">${escapeHtml(errorMessage)}</p>
        <button type="button" class="btn btn-secondary btn-sm" onclick="document.getElementById('research-form').dispatchEvent(new Event('submit'))">Retry Investigation</button>
      </div>
    `;
  }
}

/**
 * Renders the Dossier and Enriched Intelligence Matrix
 */
function renderDossierOutput(dossier) {
  const resultsEl = document.getElementById("research-results-container");
  const emptyEl = document.getElementById("research-empty");

  if (!resultsEl) return;
  if (emptyEl) emptyEl.style.display = "none";
  resultsEl.style.display = "block";

  const newBtn = document.getElementById("btn-start-new-dossier");
  if (newBtn) newBtn.style.display = "inline-flex";

  // Reset to first tab
  document.querySelectorAll(".dossier-tab").forEach(t => t.classList.remove("active"));
  document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
  document.querySelector('.dossier-tab[data-tab="tab-dossier"]')?.classList.add("active");
  document.getElementById("tab-dossier")?.classList.add("active");

  // Populate Header Meta
  document.getElementById("dossier-title").textContent = dossier.title || `Research: ${dossier.topic}`;
  document.getElementById("dossier-topic").textContent = dossier.topic || "—";
  document.getElementById("dossier-domain").textContent = dossier.domain_label || "Universal Intelligence";
  document.getElementById("dossier-sources-count").textContent = `${dossier.total_sources || 0} (${dossier.official_sources_count || 0} Official)`;
  document.getElementById("dossier-timestamp").textContent = new Date(dossier.created_at || Date.now()).toLocaleString();

  // Populate Sections
  document.getElementById("dossier-summary").innerHTML = formatTextParagraphs(dossier.executive_summary);

  // Key Findings
  const findingsList = document.getElementById("dossier-findings");
  findingsList.innerHTML = "";
  (dossier.key_findings || []).forEach(f => {
    const li = document.createElement("li");
    li.innerHTML = formatCitationBadges(f);
    findingsList.appendChild(li);
  });

  document.getElementById("dossier-policy").innerHTML = formatTextParagraphs(dossier.policy_and_regulatory_framework);
  document.getElementById("dossier-market").innerHTML = formatTextParagraphs(dossier.market_and_industry_dynamics);
  document.getElementById("dossier-risks").innerHTML = formatTextParagraphs(dossier.uncertainties_and_risks);
  document.getElementById("dossier-implications").innerHTML = formatTextParagraphs(dossier.strategic_implications);

  // AI Model Matrix Tab Check
  const aiTabBtn = document.getElementById("tab-btn-ai");
  if (dossier.ai_intelligence_matrix && dossier.ai_intelligence_matrix.models) {
    if (aiTabBtn) aiTabBtn.style.display = "block";
    renderAIMatrix(dossier.ai_intelligence_matrix);
  } else {
    if (aiTabBtn) aiTabBtn.style.display = "none";
  }

  // Populate Source Provenance Grid
  renderSourcesGrid(dossier.sources || []);

  // Populate Source Quality Audit
  renderQualityAudit(dossier.source_quality_audit || {});

  // Scroll smoothly to output
  resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderAIMatrix(aiMatrix) {
  const summaryEl = document.getElementById("ai-matrix-summary");
  if (summaryEl) summaryEl.textContent = aiMatrix.comparison_summary || "Frontier Model & Evaluation Analysis";

  const tbody = document.getElementById("tbody-ai-models");
  if (tbody) {
    tbody.innerHTML = "";
    (aiMatrix.models || []).forEach(m => {
      const pIn = m.pricing?.input_per_1m || m.input_pricing_per_1m || "N/A";
      const pOut = m.pricing?.output_per_1m || m.output_pricing_per_1m || "N/A";
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="font-weight:600;color:var(--primary);">${escapeHtml(m.name)}</td>
        <td>${escapeHtml(m.developer || "—")}</td>
        <td><code>${escapeHtml(m.context_window || "—")}</code></td>
        <td>${escapeHtml(pIn)}</td>
        <td>${escapeHtml(pOut)}</td>
        <td><span class="status-badge active">${escapeHtml(m.weights || "Closed")}</span></td>
        <td><span class="status-badge ${m.deprecated ? 'repealed' : 'active'}">${escapeHtml(m.status || "Active")}</span></td>
      `;
      tbody.appendChild(tr);
    });
  }

  const cardsContainer = document.getElementById("ai-evaluations-cards");
  if (cardsContainer) {
    cardsContainer.innerHTML = "";
    (aiMatrix.models || []).forEach(m => {
      const card = document.createElement("div");
      card.className = "card";
      card.style.padding = "14px 16px";
      card.style.backgroundColor = "var(--bg-page)";

      let vendorBadges = "";
      (m.vendor_claims || []).forEach(vc => {
        vendorBadges += `<span class="badge" style="background-color:#eff6ff;color:#1e40af;margin-right:6px;margin-bottom:4px;">${escapeHtml(vc.benchmark || vc.name)}: <strong>${escapeHtml(vc.score)}</strong> (Vendor)</span>`;
      });

      let indepBadges = "";
      (m.independent_evaluations || []).forEach(ie => {
        indepBadges += `<span class="badge" style="background-color:#ecfdf5;color:#065f46;margin-right:6px;margin-bottom:4px;">${escapeHtml(ie.benchmark || ie.name)}: <strong>${escapeHtml(ie.score)}</strong> (${escapeHtml(ie.evaluator || "Independent")})</span>`;
      });

      card.innerHTML = `
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
          <h4 style="font-size:0.95rem;font-weight:700;color:var(--text-main);">${escapeHtml(m.name)} Evaluation Profile</h4>
          <span style="font-size:11px;color:var(--text-muted);">${escapeHtml(m.developer || "")}</span>
        </div>
        <p style="font-size:0.875rem;color:var(--text-muted);margin-bottom:8px;"><strong>Core Strengths:</strong> ${escapeHtml(m.key_strengths || m.strengths || "Advanced reasoning")}</p>
        <div style="display:flex;flex-direction:column;gap:6px;font-size:0.825rem;">
          ${vendorBadges ? `<div><strong>Vendor Self-Reported:</strong> ${vendorBadges}</div>` : ""}
          ${indepBadges ? `<div><strong>Independent Leaderboards:</strong> ${indepBadges}</div>` : ""}
          ${m.deprecation_status && m.deprecation_status !== "None" ? `<div style="color:var(--danger);font-weight:600;">Deprecation Notice: ${escapeHtml(m.deprecation_status)}</div>` : ""}
        </div>
      `;
      cardsContainer.appendChild(card);
    });
  }

  const discEl = document.getElementById("ai-disclaimer-box");
  if (discEl) {
    discEl.innerHTML = `<strong>Methodology Standard:</strong> ${escapeHtml(aiMatrix.methodology_disclaimer || "Vendor numbers reflect specific laboratory prompting. Consult LMSYS Chatbot Arena and SWE-bench for standardized independent evaluation.")}`;
  }
}

function renderSourcesGrid(sources) {
  const container = document.getElementById("dossier-sources");
  if (!container) return;

  container.innerHTML = "";
  if (sources.length === 0) {
    container.innerHTML = `<div style="color:var(--text-muted);font-size:0.85rem;">No external sources recorded for this synthesis.</div>`;
    return;
  }

  sources.forEach(s => {
    const card = document.createElement("a");
    card.href = s.url || "#";
    card.target = "_blank";
    card.rel = "noopener noreferrer";
    card.className = "source-card";

    let badgeClass = "badge-general";
    if (s.is_official || s.badge === "gov") badgeClass = "badge-official";
    else if (s.badge === "legal") badgeClass = "badge-legal";
    else if (s.badge === "academic") badgeClass = "badge-academic";
    else if (s.badge === "ai-official") badgeClass = "badge-ai";

    card.innerHTML = `
      <div class="source-header">
        <span class="source-domain">${escapeHtml(s.domain || "External Authority")}</span>
        <span class="source-badge ${badgeClass}">${escapeHtml(s.category || (s.is_official ? "Official" : "Web"))}</span>
      </div>
      <div class="source-title" title="${escapeHtml(s.title || '')}">${escapeHtml(s.title || "Reference Document")}</div>
      <div class="source-snippet">${escapeHtml(s.snippet || "Authoritative source reference.")}</div>
      <div class="source-meta">
        <span>Pub: ${escapeHtml(s.published_date || "Recent")}</span>
        <span>•</span>
        <span>Tier: ${escapeHtml(s.level || "tier_2")}</span>
        <span>•</span>
        <span>Freshness: ${escapeHtml(s.freshness || "daily")}</span>
      </div>
    `;

    container.appendChild(card);
  });
}

function renderQualityAudit(audit) {
  const metricsRow = document.getElementById("audit-metrics-row");
  const notesBox = document.getElementById("audit-notes-box");

  if (metricsRow) {
    const qScore = audit.quality_score || 0;
    const scoreColor = qScore >= 75 ? "var(--success)" : (qScore >= 50 ? "var(--warning)" : "var(--danger)");

    metricsRow.innerHTML = `
      <div class="card" style="padding:14px;background-color:var(--bg-page);">
        <div style="font-size:11.5px;font-weight:600;color:var(--text-muted);text-transform:uppercase;">Authority Score</div>
        <div style="font-size:1.8rem;font-weight:700;color:${scoreColor};">${qScore}<span style="font-size:1rem;color:var(--text-muted);">/100</span></div>
      </div>
      <div class="card" style="padding:14px;background-color:var(--bg-page);">
        <div style="font-size:11.5px;font-weight:600;color:var(--text-muted);text-transform:uppercase;">Primary Official Ratio</div>
        <div style="font-size:1.8rem;font-weight:700;color:var(--primary);">${Math.round((audit.official_primary_ratio || 0) * 100)}%</div>
      </div>
      <div class="card" style="padding:14px;background-color:var(--bg-page);">
        <div style="font-size:11.5px;font-weight:600;color:var(--text-muted);text-transform:uppercase;">Tier 1 Authorities</div>
        <div style="font-size:1.8rem;font-weight:700;color:var(--text-main);">${audit.tier_1_count || 0}</div>
      </div>
      <div class="card" style="padding:14px;background-color:var(--bg-page);">
        <div style="font-size:11.5px;font-weight:600;color:var(--text-muted);text-transform:uppercase;">Single Provider Bias</div>
        <div style="font-size:1.2rem;font-weight:700;color:${audit.single_provider_bias_warning ? 'var(--warning)' : 'var(--success)'};margin-top:6px;">
          ${audit.single_provider_bias_warning ? 'Warning' : 'Balanced Diversity'}
        </div>
      </div>
    `;
  }

  if (notesBox) {
    let notesHtml = "<strong>Reliability Notes:</strong><ul style='margin-top:8px;padding-left:18px;'>";
    (audit.notes || []).forEach(n => {
      notesHtml += `<li style='margin-bottom:4px;font-size:0.875rem;color:var(--text-secondary);'>${escapeHtml(n)}</li>`;
    });
    notesHtml += "</ul>";
    notesBox.innerHTML = notesHtml;
  }
}

/**
 * Registry Catalog Modal
 */
function setupRegistryModal() {
  const openBtn = document.getElementById("btn-open-registry-modal");
  const closeBtn = document.getElementById("btn-close-registry-modal");
  const modal = document.getElementById("modal-registry");

  if (openBtn && modal) {
    openBtn.addEventListener("click", async () => {
      modal.style.display = "flex";
      await loadRegistryCatalog();
    });
  }

  if (closeBtn && modal) {
    closeBtn.addEventListener("click", () => {
      modal.style.display = "none";
    });
  }

  modal?.addEventListener("click", (e) => {
    if (e.target === modal) modal.style.display = "none";
  });
}

async function loadRegistryCatalog() {
  const tbody = document.getElementById("tbody-registry-catalog");
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:16px;">Loading catalog...</td></tr>`;

  try {
    const res = await window.apiClient.get("/research/sources/registry");
    const sources = res.sources || [];
    tbody.innerHTML = "";

    sources.forEach(s => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${escapeHtml(s.name)}</strong></td>
        <td>${escapeHtml(s.domain_label || s.domain)}</td>
        <td><code>${escapeHtml(s.source_type)}</code></td>
        <td><span class="status-badge active">${escapeHtml(s.reliability_tier)}</span></td>
        <td>${escapeHtml(s.freshness)}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" style="color:var(--danger);text-align:center;padding:16px;">Error loading registry: ${err.message}</td></tr>`;
  }
}

function setupCopyMarkdown() {
  const copyBtn = document.getElementById("btn-copy-dossier");
  if (!copyBtn) return;

  copyBtn.addEventListener("click", () => {
    if (!currentDossier) return;

    let md = `# ${currentDossier.title || 'Research Dossier: ' + currentDossier.topic}\n\n`;
    md += `**Domain:** ${currentDossier.domain_label || 'Universal'}\n`;
    md += `**Topic:** ${currentDossier.topic}\n`;
    md += `**Retrieved At:** ${currentDossier.created_at}\n\n`;
    md += `## Executive Brief\n${currentDossier.executive_summary}\n\n`;
    md += `## Key Grounded Findings\n`;
    (currentDossier.key_findings || []).forEach(f => { md += `- ${f}\n`; });
    md += `\n## Statutory, Technical & Regulatory Framework\n${currentDossier.policy_and_regulatory_framework}\n\n`;
    md += `## Market & Operational Dynamics\n${currentDossier.market_and_industry_dynamics}\n\n`;
    md += `## Emerging Risks & Uncertainties\n${currentDossier.uncertainties_and_risks}\n\n`;
    md += `## Strategic Recommendations\n${currentDossier.strategic_implications}\n\n`;
    md += `## Source Bibliography\n`;
    (currentDossier.sources || []).forEach((s, idx) => {
      md += `${idx + 1}. [${s.title}](${s.url}) - ${s.domain} (${s.published_date}) [Tier: ${s.level}]\n`;
    });

    navigator.clipboard.writeText(md).then(() => {
      const orig = copyBtn.textContent;
      copyBtn.textContent = "Copied to Clipboard!";
      setTimeout(() => { copyBtn.textContent = orig; }, 2000);
    });
  });
}

function formatTextParagraphs(text) {
  if (!text) return "<p>—</p>";
  return text.split("\n\n").map(p => `<p style="margin-bottom:12px;">${escapeHtml(p.trim())}</p>`).join("");
}

function formatCitationBadges(text) {
  if (!text) return "";
  let escaped = escapeHtml(text);
  return escaped.replace(/\[Source\s*(\d+):?([^\]]*)\]/gi, (match, num, info) => {
    return `<span class="badge badge-official" style="font-size:11px;margin-left:4px;">Source ${num}${info ? ': ' + info.trim() : ''}</span>`;
  });
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

/**
 * View Mode Switching: New Investigation vs Saved Archive
 */
function setupViewModeToggle() {
  const btnInvestigate = document.getElementById("view-mode-investigate");
  const btnHistory = document.getElementById("view-mode-history");

  btnInvestigate?.addEventListener("click", () => switchViewMode("investigate"));
  btnHistory?.addEventListener("click", () => switchViewMode("history"));
}

function switchViewMode(mode) {
  const btnInvestigate = document.getElementById("view-mode-investigate");
  const btnHistory = document.getElementById("view-mode-history");
  const secInvestigate = document.getElementById("section-investigation");
  const secHistory = document.getElementById("section-history");

  if (mode === "investigate") {
    btnInvestigate?.classList.remove("btn-secondary");
    btnInvestigate?.classList.add("btn-primary");
    btnHistory?.classList.remove("btn-primary");
    btnHistory?.classList.add("btn-secondary");

    if (secInvestigate) secInvestigate.style.display = "block";
    if (secHistory) secHistory.style.display = "none";
  } else {
    btnHistory?.classList.remove("btn-secondary");
    btnHistory?.classList.add("btn-primary");
    btnInvestigate?.classList.remove("btn-primary");
    btnInvestigate?.classList.add("btn-secondary");

    if (secInvestigate) secInvestigate.style.display = "none";
    if (secHistory) secHistory.style.display = "block";
  }
}

/**
 * Setup History Archive Controls & Listeners
 */
function setupHistoryHandlers() {
  const searchInput = document.getElementById("history-search-input");
  const refreshBtn = document.getElementById("btn-refresh-history");
  const clearBtn = document.getElementById("btn-clear-history");

  let searchTimeout = null;
  searchInput?.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      const q = e.target.value.trim().toLowerCase();
      if (!q) {
        renderHistoryList(historyReportsCache);
      } else {
        const filtered = historyReportsCache.filter(r => 
          (r.title && r.title.toLowerCase().includes(q)) ||
          (r.topic && r.topic.toLowerCase().includes(q)) ||
          (r.domain && r.domain.toLowerCase().includes(q)) ||
          (r.domain_label && r.domain_label.toLowerCase().includes(q))
        );
        renderHistoryList(filtered);
      }
    }, 250);
  });

  refreshBtn?.addEventListener("click", () => loadResearchHistory());
  clearBtn?.addEventListener("click", () => clearAllHistory());
}

/**
 * Loads Research History from Backend
 */
async function loadResearchHistory() {
  const loadingEl = document.getElementById("history-loading");
  const countEl = document.getElementById("history-count");
  if (loadingEl) loadingEl.style.display = "block";

  try {
    const res = await window.apiClient.get("/research/history");
    const reports = res.reports || [];
    historyReportsCache = reports;

    if (countEl) countEl.textContent = reports.length;
    renderHistoryList(reports);
  } catch (err) {
    console.warn("[ResearchStudio] Failed to load research history:", err.message);
  } finally {
    if (loadingEl) loadingEl.style.display = "none";
  }
}

/**
 * Renders Persisted Research Dossiers Grid / Sidebar
 */
function renderHistoryList(reports) {
  const container = document.getElementById("history-list");
  const emptyEl = document.getElementById("history-empty");
  const countEl = document.getElementById("history-count");
  if (!container) return;

  container.innerHTML = "";
  if (countEl) countEl.textContent = reports ? reports.length : 0;

  if (!reports || reports.length === 0) {
    if (emptyEl) emptyEl.style.display = "block";
    return;
  }
  if (emptyEl) emptyEl.style.display = "none";

  reports.forEach(r => {
    const card = document.createElement("div");
    card.className = "history-item-card";
    card.dataset.id = r.id;
    if (currentDossier && currentDossier.id === r.id) {
      card.classList.add("active");
    }

    const title = escapeHtml(r.title || r.topic || "Research Dossier");
    const domain = escapeHtml(r.domain_label || r.domain || "Universal");
    
    // Relative or short time
    let timeStr = "Recent";
    if (r.created_at) {
      const diffMs = Date.now() - new Date(r.created_at).getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);
      if (diffMins < 2) timeStr = "Just now";
      else if (diffMins < 60) timeStr = `${diffMins}m ago`;
      else if (diffHours < 24) timeStr = `${diffHours}h ago`;
      else if (diffDays === 1) timeStr = "Yesterday";
      else timeStr = new Date(r.created_at).toLocaleDateString([], { month: "short", day: "numeric" });
    }
    const sourcesCount = r.total_sources || (r.sources ? r.sources.length : 0);
    const qScore = r.source_quality_audit?.quality_score || r.quality_score;

    card.innerHTML = `
      <div class="history-item-header">
        <span class="history-item-domain">${domain}</span>
        <span class="history-item-time">${timeStr}</span>
      </div>
      <div class="history-item-title">${title}</div>
      <div class="history-item-footer">
        <span>${sourcesCount} sources ${qScore ? `• ${qScore}/100` : ""}</span>
        <button type="button" class="history-item-delete" title="Delete from history" style="display:inline-flex;align-items:center;justify-content:center;background:none;border:none;cursor:pointer;color:var(--text-muted);padding:4px;">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        </button>
      </div>
    `;

    // Clicking anywhere on card opens the report
    card.addEventListener("click", (e) => {
      if (e.target.closest(".history-item-delete")) return;
      document.querySelectorAll(".history-item-card").forEach(c => c.classList.remove("active"));
      card.classList.add("active");
      openHistoryReport(r.id);
    });

    // Delete button
    card.querySelector(".history-item-delete")?.addEventListener("click", (e) => {
      e.stopPropagation();
      deleteHistoryReport(r.id, title);
    });

    container.appendChild(card);
  });
}

/**
 * Opens a Past Report into Dossier View
 */
async function openHistoryReport(reportId) {
  try {
    const report = await window.apiClient.get(`/research/${reportId}`);
    if (!report) {
      alert("Report could not be retrieved.");
      return;
    }
    currentDossier = report;

    // Show 'New Investigation' button to allow starting fresh
    const newBtn = document.getElementById("btn-start-new-dossier");
    if (newBtn) newBtn.style.display = "inline-flex";

    // Set topic input
    const topicInput = document.getElementById("research-topic-input");
    const clearBtn = document.getElementById("btn-clear-topic");
    if (topicInput && report.topic) {
      topicInput.value = report.topic;
      if (clearBtn) clearBtn.style.display = "inline-block";
    }

    renderDossierOutput(report);

    // Scroll smoothly to output
    const resultsContainer = document.getElementById("research-results-container");
    if (resultsContainer) {
      resultsContainer.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  } catch (err) {
    console.error("[ResearchStudio] Error opening report:", err);
    alert(`Failed to load report: ${err.message}`);
  }
}

/**
 * Setup Segmented Control for Investigation Depth
 */
function setupDepthSegmentedControl() {
  const container = document.getElementById("depth-segmented-control");
  if (!container) return;

  const btns = container.querySelectorAll(".segmented-btn");
  btns.forEach(btn => {
    btn.addEventListener("click", () => {
      btns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const depth = btn.dataset.depth;
      const radios = document.querySelectorAll('input[name="research_depth"]');
      radios.forEach(r => {
        if (r.value === depth) r.checked = true;
      });
    });
  });
}

/**
 * Setup Clickable Suggested Exploration Cards
 */
function setupSuggestedCards() {
  const cards = document.querySelectorAll(".suggested-card");
  const topicInput = document.getElementById("research-topic-input");
  const clearBtn = document.getElementById("btn-clear-topic");
  const form = document.getElementById("research-form");

  cards.forEach(card => {
    card.addEventListener("click", () => {
      const topic = card.dataset.topic;
      const domain = card.dataset.domain;
      if (!topic) return;

      if (topicInput) {
        topicInput.value = topic;
        if (clearBtn) clearBtn.style.display = "inline-block";
      }

      if (domain) {
        activeDomain = domain;
        document.querySelectorAll(".domain-pill, .domain-chip").forEach(p => {
          if (p.dataset.domain === domain) p.classList.add("active");
          else p.classList.remove("active");
        });
      }

      // Submit search
      form?.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
    });
  });
}

/**
 * Setup New Search & Clear input controls
 */
function setupNewSearchButton() {
  const newBtn = document.getElementById("btn-start-new-dossier");
  const clearBtn = document.getElementById("btn-clear-topic");
  const topicInput = document.getElementById("research-topic-input");
  const emptyState = document.getElementById("research-empty");
  const resultsContainer = document.getElementById("research-results-container");

  newBtn?.addEventListener("click", () => {
    if (topicInput) topicInput.value = "";
    if (clearBtn) clearBtn.style.display = "none";
    if (resultsContainer) resultsContainer.style.display = "none";
    if (emptyState) emptyState.style.display = "block";
    newBtn.style.display = "none";
    currentDossier = null;
    document.querySelectorAll(".history-item-card").forEach(c => c.classList.remove("active"));
    topicInput?.focus();
  });

  topicInput?.addEventListener("input", () => {
    if (clearBtn) {
      clearBtn.style.display = topicInput.value.length > 0 ? "inline-block" : "none";
    }
  });

  clearBtn?.addEventListener("click", () => {
    if (topicInput) {
      topicInput.value = "";
      clearBtn.style.display = "none";
      topicInput.focus();
    }
  });
}

/**
 * Permanently Deletes a Single Saved Report
 */
async function deleteHistoryReport(reportId, title) {
  if (!confirm(`Are you sure you want to permanently delete report "${title}"?`)) return;

  try {
    await window.apiClient.delete(`/research/${reportId}`);
    await loadResearchHistory();
  } catch (err) {
    console.error("[ResearchStudio] Error deleting report:", err);
    alert(`Failed to delete report: ${err.message}`);
  }
}

/**
 * Permanently Deletes All Saved Reports
 */
async function clearAllHistory() {
  if (!confirm("Are you sure you want to delete ALL saved research dossiers? This action cannot be undone.")) return;

  try {
    await window.apiClient.delete("/research/history");
    await loadResearchHistory();
  } catch (err) {
    console.error("[ResearchStudio] Error clearing history:", err);
    alert(`Failed to clear history: ${err.message}`);
  }
}
