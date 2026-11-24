/**
 * DOCUMIND COMPARE & VERIFY CONTROLLER
 * Handles Doc vs Doc differential auditing and Doc vs Current Live Reality verification.
 */

let availableDocuments = [];

document.addEventListener("DOMContentLoaded", async () => {
  const authenticated = await window.authManager.requireAuth();
  if (!authenticated) return;

  setupModeTabs();
  await loadDocumentsDropdowns();
  setupActionButtons();
});

function setupModeTabs() {
  const btnDocVsDoc = document.getElementById("tab-btn-doc-vs-doc");
  const btnDocVsWeb = document.getElementById("tab-btn-doc-vs-web");
  const panelDocVsDoc = document.getElementById("panel-doc-vs-doc");
  const panelDocVsWeb = document.getElementById("panel-doc-vs-web");
  const resultsContainer = document.getElementById("compare-results");
  const emptyState = document.getElementById("compare-empty");

  btnDocVsDoc.addEventListener("click", () => {
    btnDocVsDoc.classList.add("active");
    btnDocVsWeb.classList.remove("active");
    panelDocVsDoc.style.display = "block";
    panelDocVsWeb.style.display = "none";
    resultsContainer.style.display = "none";
    emptyState.style.display = "block";
  });

  btnDocVsWeb.addEventListener("click", () => {
    btnDocVsWeb.classList.add("active");
    btnDocVsDoc.classList.remove("active");
    panelDocVsDoc.style.display = "none";
    panelDocVsWeb.style.display = "block";
    resultsContainer.style.display = "none";
    emptyState.style.display = "block";
  });
}

async function loadDocumentsDropdowns() {
  try {
    const data = await window.apiClient.get("/documents");
    availableDocuments = (data.documents || []).filter(d => d.status === "ready");

    const selA = document.getElementById("select-doc-a");
    const selB = document.getElementById("select-doc-b");
    const selWeb = document.getElementById("select-doc-web");

    selA.innerHTML = '<option value="">Select Document A...</option>';
    selB.innerHTML = '<option value="">Select Document B...</option>';
    selWeb.innerHTML = '<option value="">Select Document...</option>';

    availableDocuments.forEach(d => {
      const optA = document.createElement("option");
      optA.value = d.id;
      optA.textContent = `${d.name} (${d.chunk_count} chunks)`;
      selA.appendChild(optA);

      const optB = document.createElement("option");
      optB.value = d.id;
      optB.textContent = `${d.name} (${d.chunk_count} chunks)`;
      selB.appendChild(optB);

      const optW = document.createElement("option");
      optW.value = d.id;
      optW.textContent = `${d.name} (${d.chunk_count} chunks)`;
      selWeb.appendChild(optW);
    });

  } catch (err) {
    console.error("[Compare] Failed to load documents:", err);
  }
}

function setupActionButtons() {
  const btnDoc = document.getElementById("btn-run-doc-compare");
  const btnWeb = document.getElementById("btn-run-web-compare");

  btnDoc.addEventListener("click", async () => {
    const docA = document.getElementById("select-doc-a").value;
    const docB = document.getElementById("select-doc-b").value;

    if (!docA || !docB) {
      showNotification("Please select both Document A and Document B to compare.", "danger");
      return;
    }
    if (docA === docB) {
      showNotification("Please select two different documents to compare.", "danger");
      return;
    }

    await executeDocComparison(docA, docB);
  });

  btnWeb.addEventListener("click", async () => {
    const docId = document.getElementById("select-doc-web").value;
    if (!docId) {
      showNotification("Please select a document to verify against live reality.", "danger");
      return;
    }

    await executeWebComparison(docId);
  });
}

async function executeDocComparison(docAId, docBId) {
  const loading = document.getElementById("compare-loading");
  const loadingTitle = document.getElementById("compare-loading-title");
  const results = document.getElementById("compare-results");
  const empty = document.getElementById("compare-empty");

  loadingTitle.textContent = "Comparing Document A vs. Document B...";
  loading.style.display = "block";
  results.style.display = "none";
  empty.style.display = "none";

  try {
    const data = await window.apiClient.post("/compare/documents", {
      doc_a_id: docAId,
      doc_b_id: docBId
    });

    renderDocVsDocResults(data);
    results.style.display = "block";

  } catch (err) {
    console.error("[Compare] Error:", err);
    showNotification("Comparison failed: " + err.message, "danger");
    empty.style.display = "block";
  } finally {
    loading.style.display = "none";
  }
}

async function executeWebComparison(docId) {
  const loading = document.getElementById("compare-loading");
  const loadingTitle = document.getElementById("compare-loading-title");
  const results = document.getElementById("compare-results");
  const empty = document.getElementById("compare-empty");

  loadingTitle.textContent = "Verifying Document Against Live Law & Authoritative Web...";
  loading.style.display = "block";
  results.style.display = "none";
  empty.style.display = "none";

  try {
    const data = await window.apiClient.post("/compare/web", {
      document_id: docId
    });

    renderDocVsWebResults(data);
    results.style.display = "block";

  } catch (err) {
    console.error("[Compare Web] Error:", err);
    showNotification("Verification failed: " + err.message, "danger");
    empty.style.display = "block";
  } finally {
    loading.style.display = "none";
  }
}

function renderDocVsDocResults(data) {
  const container = document.getElementById("compare-results");
  let html = `
    <div class="card" style="margin-bottom:24px;">
      <div style="display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border-color);padding-bottom:16px;margin-bottom:18px;">
        <div>
          <h2 style="font-size:1.35rem;font-weight:700;">Comparative Audit: ${escapeHtml(data.doc_a?.name || 'Doc A')} vs. ${escapeHtml(data.doc_b?.name || 'Doc B')}</h2>
          <div style="font-size:0.8125rem;color:var(--text-muted);margin-top:4px;">
            Compared at ${new Date(data.compared_at).toLocaleString()}
          </div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:1.5rem;font-weight:700;color:var(--primary);">${data.similarity_score_pct || 0}%</div>
          <div style="font-size:0.75rem;color:var(--text-muted);text-transform:uppercase;">Semantic Alignment</div>
        </div>
      </div>

      <div style="margin-bottom:20px;">
        <h3 style="font-size:1rem;font-weight:600;margin-bottom:8px;">Executive Differential Summary</h3>
        <p style="font-size:0.925rem;line-height:1.6;color:var(--text-secondary);">${escapeHtml(data.comparison_summary || '')}</p>
      </div>

      <div style="margin-bottom:24px;">
        <h3 style="font-size:1rem;font-weight:600;margin-bottom:14px;">Clause-by-Clause Differential Breakdown (${(data.changed_clauses || []).length} changes)</h3>
  `;

  (data.changed_clauses || []).forEach((c, idx) => {
    html += `
      <div class="diff-card">
        <div class="diff-card-header">
          <span style="font-weight:600;font-size:0.875rem;">Clause ${idx + 1}: ${escapeHtml(c.clause_topic || 'Clause Change')}</span>
          <span class="badge badge-${c.risk_level === 'High' ? 'failed' : c.risk_level === 'Moderate' ? 'processing' : 'ready'}">${escapeHtml(c.risk_level || 'Moderate')} Risk</span>
        </div>
        <div class="diff-columns">
          <div class="diff-column">
            <div class="diff-column-header">Document A Version</div>
            <div>${escapeHtml(c.doc_a_version || 'None')}</div>
          </div>
          <div class="diff-column">
            <div class="diff-column-header">Document B Version</div>
            <div>${escapeHtml(c.doc_b_version || 'None')}</div>
          </div>
        </div>
        <div class="diff-analysis">
          <strong>Impact Analysis:</strong> ${escapeHtml(c.analysis || '')}
        </div>
      </div>
    `;
  });

  // Contradictions
  if (data.contradictions_and_conflicts && data.contradictions_and_conflicts.length > 0) {
    html += `
      <div style="margin-top:20px;padding:16px;background:#fff1f2;border:1px solid #fecdd3;border-radius:var(--radius-md);">
        <h4 style="color:#9f1239;font-weight:600;margin-bottom:8px;">Direct Contradictions & Conflicts Detected</h4>
        <ul style="margin:0;padding-left:20px;font-size:0.875rem;color:#881337;">
    `;
    data.contradictions_and_conflicts.forEach(con => {
      html += `<li><strong>${escapeHtml(con.issue)}:</strong> Doc A says "${escapeHtml(con.doc_a_claim)}" while Doc B says "${escapeHtml(con.doc_b_claim)}". Resolution: ${escapeHtml(con.recommended_resolution)}</li>`;
    });
    html += `</ul></div>`;
  }

  html += `</div></div>`;
  container.innerHTML = html;
}

function renderDocVsWebResults(data) {
  const container = document.getElementById("compare-results");
  let html = `
    <div class="card" style="margin-bottom:24px;">
      <div style="display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border-color);padding-bottom:16px;margin-bottom:18px;">
        <div>
          <h2 style="font-size:1.35rem;font-weight:700;">Live Reality & Statutory Audit: ${escapeHtml(data.document?.name || 'Document')}</h2>
          <div style="font-size:0.8125rem;color:var(--text-muted);margin-top:4px;">
            Verified against live official portals at ${new Date(data.verified_at).toLocaleString()}
          </div>
        </div>
        <div>
          <span class="badge ${data.overall_compliance_status?.includes('Non-Compliant') ? 'badge-failed' : data.overall_compliance_status?.includes('Fully') ? 'badge-ready' : 'badge-processing'}" style="padding:8px 14px;font-size:0.875rem;">
            ${escapeHtml(data.overall_compliance_status || 'Audited')}
          </span>
        </div>
      </div>

      <div style="margin-bottom:20px;">
        <h3 style="font-size:1rem;font-weight:600;margin-bottom:8px;">Verification Assessment</h3>
        <p style="font-size:0.925rem;line-height:1.6;color:var(--text-secondary);">${escapeHtml(data.audit_summary || '')}</p>
      </div>

      <h3 style="font-size:1rem;font-weight:600;margin-bottom:14px;">Clause-by-Clause Reality Audit</h3>
  `;

  (data.verified_clauses || []).forEach((c, idx) => {
    const st = c.current_legal_or_official_status || 'Status Unverified';
    const stBadgeClass = st.toLowerCase().includes('active') ? 'active' : st.toLowerCase().includes('repealed') ? 'repealed' : st.toLowerCase().includes('amended') ? 'amended' : 'superseded';

    html += `
      <div class="diff-card">
        <div class="diff-card-header">
          <span style="font-weight:600;font-size:0.875rem;">Clause ${idx + 1} (Page ${c.page_number || 1})</span>
          <span class="badge-temporal ${stBadgeClass}">${escapeHtml(st)}</span>
        </div>
        <div class="diff-columns">
          <div class="diff-column">
            <div class="diff-column-header">Document Text as Written</div>
            <div>${escapeHtml(c.document_clause || '')}</div>
          </div>
          <div class="diff-column">
            <div class="diff-column-header">Current Official Law / Reality</div>
            <div>${escapeHtml(c.current_applicable_rule || '')}</div>
          </div>
        </div>
        <div class="diff-analysis">
          <strong>Discrepancy & Evidence:</strong> ${escapeHtml(c.evidence_and_discrepancy || '')}<br>
          <span style="color:var(--text-muted);font-size:0.8rem;margin-top:4px;display:inline-block;"><strong>Authority Citation:</strong> ${escapeHtml(c.citation || 'Authoritative Source')}</span>
        </div>
      </div>
    `;
  });

  html += `</div>`;
  container.innerHTML = html;
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
