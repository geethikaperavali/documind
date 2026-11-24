/**
 * DOCUMIND KNOWLEDGE BASE / DOCUMENTS CONTROLLER
 * Drag-and-drop file upload, size/type validation, document listing,
 * search & filter, delete confirmation, and chunk viewer modal.
 */

let allDocuments = [];
let deleteTargetId = null;

document.addEventListener("DOMContentLoaded", async () => {
  const authenticated = await window.authManager.requireAuth();
  if (!authenticated) return;

  setupIngestionTabs();
  setupManualTextEditor();
  setupPreviewModal();
  setupUploadDropzone();
  setupSearchAndFilters();
  setupDeleteModal();
  setupChunkModal();

  // Initial load
  await loadDocuments();
});

/**
 * Loads all documents for authenticated user
 */
async function loadDocuments() {
  const tbody = document.getElementById("docs-tbody");
  const emptyState = document.getElementById("docs-empty");
  const loadingIndicator = document.getElementById("docs-loading");

  if (loadingIndicator) loadingIndicator.style.display = "block";

  try {
    const data = await window.apiClient.get("/documents");
    allDocuments = data.documents || [];
    renderDocumentsList(filterDocuments(allDocuments));
  } catch (error) {
    console.error("[Documents] Failed to load:", error);
    showNotification("Failed to load documents: " + error.message, "danger");
  } finally {
    if (loadingIndicator) loadingIndicator.style.display = "none";
  }
}

/**
 * Filter and search documents locally or query backend
 */
function filterDocuments(docs) {
  const searchInput = document.getElementById("docs-search");
  const typeFilter = document.getElementById("filter-type");
  const statusFilter = document.getElementById("filter-status");

  const query = searchInput ? searchInput.value.toLowerCase().trim() : "";
  const type = typeFilter ? typeFilter.value.toLowerCase() : "all";
  const status = statusFilter ? statusFilter.value.toLowerCase() : "all";

  return docs.filter(doc => {
    const matchesQuery = !query || doc.name.toLowerCase().includes(query);
    const matchesType = type === "all" || doc.file_type.toLowerCase() === type;
    const matchesStatus = status === "all" || doc.status.toLowerCase() === status;
    return matchesQuery && matchesType && matchesStatus;
  });
}

function renderDocumentsList(docs) {
  const tbody = document.getElementById("docs-tbody");
  const emptyState = document.getElementById("docs-empty");
  const countBadge = document.getElementById("docs-count-badge");

  if (countBadge) countBadge.textContent = `${docs.length} ${docs.length === 1 ? "document" : "documents"}`;

  if (!tbody) return;
  tbody.innerHTML = "";

  if (docs.length === 0) {
    if (emptyState) emptyState.style.display = "block";
    return;
  }
  if (emptyState) emptyState.style.display = "none";

  docs.forEach(doc => {
    const tr = document.createElement("tr");

    const statusBadge = doc.status === "ready"
      ? `<span class="badge badge-ready">Ready</span>`
      : doc.status === "processing"
      ? `<span class="badge badge-processing">Processing...</span>`
      : `<span class="badge badge-failed" title="${escapeHtml(doc.error_message || 'Processing failed')}">Failed</span>`;

    const dateStr = doc.created_at ? new Date(doc.created_at).toLocaleDateString(undefined, {
      month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit"
    }) : "—";

    tr.innerHTML = `
      <td>
        <div style="display:flex;align-items:center;gap:10px;">
          <span class="badge-format">${(doc.file_type || "txt").toUpperCase()}</span>
          <span style="font-weight:600;color:var(--text-main);">${escapeHtml(doc.name)}</span>
        </div>
      </td>
      <td>${formatFileSize(doc.file_size)}</td>
      <td>${statusBadge}</td>
      <td>
        <button class="btn btn-secondary btn-sm btn-inspect-chunks" data-id="${doc.id}" data-name="${escapeHtml(doc.name)}" ${doc.chunk_count === 0 ? "disabled" : ""}>
          ${doc.chunk_count || 0} chunks
        </button>
      </td>
      <td>${dateStr}</td>
      <td style="text-align:right;">
        <div style="display:inline-flex;gap:6px;">
          <button class="btn btn-secondary btn-sm btn-doc-preview" data-id="${doc.id}" data-name="${escapeHtml(doc.name)}" title="Preview document metadata and vector chunks">Preview</button>
          <button class="btn btn-secondary btn-sm btn-temporal-audit" data-id="${doc.id}" data-name="${escapeHtml(doc.name)}" title="Audit outdated or repealed clauses">Temporal Audit</button>
          <a href="/chat.html" class="btn btn-secondary btn-sm" title="Chat with this document">Ask</a>
          <button class="btn btn-danger btn-sm btn-trigger-delete" data-id="${doc.id}" data-name="${escapeHtml(doc.name)}">Delete</button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });

  // Attach event handlers
  document.querySelectorAll(".btn-doc-preview").forEach(btn => {
    btn.addEventListener("click", () => openDocumentPreview(btn.dataset.id, btn.dataset.name));
  });

  document.querySelectorAll(".btn-inspect-chunks").forEach(btn => {
    btn.addEventListener("click", () => inspectChunks(btn.dataset.id, btn.dataset.name));
  });

  document.querySelectorAll(".btn-temporal-audit").forEach(btn => {
    btn.addEventListener("click", () => runTemporalAudit(btn.dataset.id, btn.dataset.name));
  });

  document.querySelectorAll(".btn-trigger-delete").forEach(btn => {
    btn.addEventListener("click", () => confirmDelete(btn.dataset.id, btn.dataset.name));
  });
}

/**
 * Drag and Drop & File Upload Setup
 */
function setupUploadDropzone() {
  const dropzone = document.getElementById("upload-dropzone");
  const fileInput = document.getElementById("file-input");

  if (!dropzone || !fileInput) return;

  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("drag-over");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("drag-over");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("drag-over");
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
      fileInput.value = ""; // Reset
    }
  });
}

/**
 * Handles single file upload with validation, progress indicator, and RAG status check
 */
async function handleFileUpload(file) {
  const progressBox = document.getElementById("upload-progress-box");
  const progressBar = document.getElementById("upload-progress-bar");
  const progressFilename = document.getElementById("upload-filename");
  const progressStatus = document.getElementById("upload-status-text");

  // Validate File Extension
  const ext = file.name.split(".").pop().toLowerCase();
  if (!["pdf", "docx", "txt"].includes(ext)) {
    showNotification("Invalid file format. Please upload a PDF, DOCX, or TXT document.", "danger");
    return;
  }

  // Validate File Size (25MB max)
  const maxBytes = 25 * 1024 * 1024;
  if (file.size > maxBytes) {
    showNotification("File exceeds 25 MB limit. Please upload a smaller file.", "danger");
    return;
  }

  // Show Progress UI
  if (progressBox) progressBox.classList.add("active");
  if (progressFilename) progressFilename.textContent = file.name;
  if (progressStatus) progressStatus.textContent = "Uploading to secure storage...";
  if (progressBar) progressBar.style.width = "40%";

  const formData = new FormData();
  formData.append("file", file);

  try {
    if (progressBar) progressBar.style.width = "70%";
    if (progressStatus) progressStatus.textContent = "Extracting text, chunking & generating vector embeddings...";

    const result = await window.apiClient.post("/documents/upload", formData);

    if (progressBar) progressBar.style.width = "100%";
    if (progressStatus) progressStatus.textContent = "Complete!";

    setTimeout(() => {
      if (progressBox) progressBox.classList.remove("active");
    }, 1500);

    showNotification(`"${file.name}" uploaded and indexed successfully (${result.chunk_count || 0} chunks).`, "success");
    await loadDocuments();

  } catch (error) {
    console.error("[Documents] Upload error:", error);
    if (progressStatus) progressStatus.textContent = "Error: " + error.message;
    if (progressBar) progressBar.style.backgroundColor = "var(--danger)";
    showNotification("Upload failed: " + error.message, "danger");
    setTimeout(() => {
      if (progressBox) progressBox.classList.remove("active");
      if (progressBar) {
        progressBar.style.width = "0%";
        progressBar.style.backgroundColor = "var(--primary)";
      }
    }, 3000);
  }
}

/**
 * Filter and Search Event Listeners
 */
function setupSearchAndFilters() {
  const searchInput = document.getElementById("docs-search");
  const typeFilter = document.getElementById("filter-type");
  const statusFilter = document.getElementById("filter-status");

  const apply = () => renderDocumentsList(filterDocuments(allDocuments));

  let debounceTimer = null;
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(apply, 200);
    });
  }
  if (typeFilter) typeFilter.addEventListener("change", apply);
  if (statusFilter) statusFilter.addEventListener("change", apply);
}

/**
 * Delete Confirmation Modal
 */
function setupDeleteModal() {
  const modal = document.getElementById("delete-modal");
  const btnCancel = document.getElementById("btn-delete-cancel");
  const btnConfirm = document.getElementById("btn-delete-confirm");
  const closeX = document.getElementById("delete-modal-close");

  const hide = () => {
    if (modal) modal.classList.remove("active");
    deleteTargetId = null;
  };

  if (btnCancel) btnCancel.addEventListener("click", hide);
  if (closeX) closeX.addEventListener("click", hide);

  if (btnConfirm) {
    btnConfirm.addEventListener("click", async () => {
      if (!deleteTargetId) return;
      btnConfirm.disabled = true;
      btnConfirm.textContent = "Deleting...";

      try {
        await window.apiClient.delete(`/documents/${deleteTargetId}`);
        showNotification("Document deleted successfully.", "success");
        hide();
        await loadDocuments();
      } catch (err) {
        showNotification("Failed to delete document: " + err.message, "danger");
      } finally {
        btnConfirm.disabled = false;
        btnConfirm.textContent = "Delete Document";
      }
    });
  }
}

function confirmDelete(docId, docName) {
  deleteTargetId = docId;
  const modal = document.getElementById("delete-modal");
  const nameEl = document.getElementById("delete-doc-name");
  if (nameEl) nameEl.textContent = `"${docName}"`;
  if (modal) modal.classList.add("active");
}

/**
 * Chunks Inspector Modal
 */
function setupChunkModal() {
  const modal = document.getElementById("chunks-modal");
  const closeBtn = document.getElementById("chunks-modal-close");
  const closeFooterBtn = document.getElementById("chunks-modal-footer-close");

  const hide = () => {
    if (modal) modal.classList.remove("active");
  };

  if (closeBtn) closeBtn.addEventListener("click", hide);
  if (closeFooterBtn) closeFooterBtn.addEventListener("click", hide);
}

async function inspectChunks(docId, docName) {
  const modal = document.getElementById("chunks-modal");
  const titleEl = document.getElementById("chunks-modal-title");
  const container = document.getElementById("chunks-content-list");

  if (titleEl) titleEl.textContent = `Chunks for "${docName}"`;
  if (container) container.innerHTML = `<div style="text-align:center;padding:24px;color:var(--text-muted);">Loading chunks...</div>`;
  if (modal) modal.classList.add("active");

  try {
    const data = await window.apiClient.get(`/documents/${docId}`);
    const chunks = data.sample_chunks || [];

    if (chunks.length === 0) {
      container.innerHTML = `<div style="text-align:center;padding:24px;color:var(--text-muted);">No chunks found for this document.</div>`;
      return;
    }

    container.innerHTML = "";
    chunks.forEach(c => {
      const card = document.createElement("div");
      card.className = "chunk-card";
      card.innerHTML = `
        <div class="chunk-meta">
          <span>Chunk #${c.chunk_index + 1}</span>
          <span>Page ${c.page_number}</span>
        </div>
        <div style="color:var(--text-main);white-space:pre-wrap;">${escapeHtml(c.content)}</div>
      `;
      container.appendChild(card);
    });

  } catch (err) {
    if (container) container.innerHTML = `<div style="color:var(--danger);padding:16px;">Failed to load chunks: ${err.message}</div>`;
  }
}

/**
 * Toast notification
 */
async function runTemporalAudit(docId, docName) {
  const modal = document.getElementById("temporal-modal");
  const modalTitle = document.getElementById("temporal-modal-title");
  const loading = document.getElementById("temporal-audit-loading");
  const content = document.getElementById("temporal-audit-content");
  const closeBtn = document.getElementById("temporal-modal-close");

  if (!modal) return;
  modalTitle.textContent = `Temporal Health Check: ${docName}`;
  loading.style.display = "block";
  content.style.display = "none";
  modal.classList.add("active");

  closeBtn.onclick = () => modal.classList.remove("active");
  modal.onclick = (e) => { if (e.target === modal) modal.classList.remove("active"); };

  try {
    const data = await window.apiClient.post("/temporal/audit-document", {
      document_id: docId
    });

    loading.style.display = "none";
    content.style.display = "block";

    const riskBadgeClass = data.risk_badge === 'high' ? 'badge-failed' : data.risk_badge === 'moderate' ? 'badge-processing' : 'badge-ready';

    let html = `
      <div style="margin-bottom:20px;padding:16px;background:#f8fafc;border:1px solid var(--border-color);border-radius:var(--radius-md);">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
          <h4 style="margin:0;font-size:0.95rem;font-weight:700;">Overall Risk Assessment:</h4>
          <span class="badge ${riskBadgeClass}" style="padding:4px 10px;font-size:0.8rem;">${data.risk_badge.toUpperCase()} RISK</span>
        </div>
        <p style="margin:0;font-size:0.875rem;color:var(--text-secondary);">${escapeHtml(data.overall_risk)}</p>
      </div>

      <h4 style="font-size:0.9rem;font-weight:600;margin-bottom:12px;text-transform:uppercase;color:var(--text-muted);">
        Audited Clauses & Statutory Reality (${(data.findings || []).length} provisions scanned)
      </h4>
    `;

    if (!data.findings || data.findings.length === 0) {
      html += `<div style="padding:24px;text-align:center;color:var(--text-muted);font-size:0.875rem;">No time-sensitive or statutory clauses detected in this document.</div>`;
    } else {
      data.findings.forEach((f, idx) => {
        const st = f.status_classification || 'Status Unverified';
        const stClass = st.toLowerCase().includes('active') ? 'active' : st.toLowerCase().includes('repealed') ? 'repealed' : st.toLowerCase().includes('amended') ? 'amended' : 'superseded';

        html += `
          <div style="border:1px solid var(--border-color);border-radius:var(--radius-md);padding:14px;margin-bottom:12px;background:var(--bg-surface);">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
              <strong style="font-size:0.9rem;color:var(--text-main);">${idx + 1}. ${escapeHtml(f.subject)} (Page ${f.page_number || 1})</strong>
              <span class="badge-temporal ${stClass}">${escapeHtml(st)}</span>
            </div>
            <div style="font-size:0.8125rem;color:var(--text-secondary);margin-bottom:6px;">
              <strong>Document Excerpt:</strong> <em>"${escapeHtml(f.excerpt || '')}"</em>
            </div>
            <div style="font-size:0.8125rem;color:var(--text-secondary);margin-bottom:6px;">
              <strong>What Changed:</strong> ${escapeHtml(f.what_changed || 'N/A')} (Effective: ${escapeHtml(f.effective_date || 'N/A')})
            </div>
            <div style="font-size:0.8125rem;color:#0f172a;background:#f1f5f9;padding:6px 10px;border-radius:4px;">
              <strong>Current Governing Provision:</strong> ${escapeHtml(f.current_applicable_provision || 'N/A')}
            </div>
          </div>
        `;
      });
    }

    content.innerHTML = html;

  } catch (err) {
    console.error("[TemporalAudit] Failed:", err);
    loading.style.display = "none";
    content.style.display = "block";
    content.innerHTML = `<div style="color:var(--danger);padding:16px;">Audit failed: ${escapeHtml(err.message)}</div>`;
  }
}

function showNotification(message, type = "success") {
  const toast = document.createElement("div");
  toast.style.position = "fixed";
  toast.style.bottom = "24px";
  toast.style.right = "24px";
  toast.style.zIndex = "9999";
  toast.style.padding = "12px 20px";
  toast.style.borderRadius = "var(--radius-md)";
  toast.style.fontSize = "13px";
  toast.style.fontWeight = "500";
  toast.style.boxShadow = "var(--shadow-lg)";
  toast.style.transition = "opacity 0.3s ease";
  toast.style.backgroundColor = type === "success" ? "var(--success)" : "var(--danger)";
  toast.style.color = "white";
  toast.textContent = message;

  document.body.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function formatFileSize(bytes) {
  if (!bytes) return "0 B";
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(2) + " MB";
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
 * Ingestion Method Switching: File Upload vs Manual Text Editor
 */
function setupIngestionTabs() {
  const tabUpload = document.getElementById("tab-btn-upload");
  const tabManual = document.getElementById("tab-btn-manual");
  const paneUpload = document.getElementById("pane-upload");
  const paneManual = document.getElementById("pane-manual");

  if (!tabUpload || !tabManual) return;

  tabUpload.addEventListener("click", () => {
    tabUpload.classList.add("active");
    tabManual.classList.remove("active");
    if (paneUpload) paneUpload.style.display = "block";
    if (paneManual) paneManual.style.display = "none";
  });

  tabManual.addEventListener("click", () => {
    tabManual.classList.add("active");
    tabUpload.classList.remove("active");
    if (paneUpload) paneUpload.style.display = "none";
    if (paneManual) paneManual.style.display = "block";
    document.getElementById("manual-doc-title")?.focus();
  });
}

/**
 * Manual Document / Notes Ingestion Setup
 */
function setupManualTextEditor() {
  const form = document.getElementById("form-manual-doc");
  const titleInput = document.getElementById("manual-doc-title");
  const contentInput = document.getElementById("manual-doc-content");
  const counterEl = document.getElementById("manual-doc-counter");
  const alertEl = document.getElementById("manual-doc-alert");
  const submitBtn = document.getElementById("btn-save-manual-doc");

  if (!form || !contentInput) return;

  // Live word and character counting
  contentInput.addEventListener("input", () => {
    const text = contentInput.value;
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    const chars = text.length;
    if (counterEl) counterEl.textContent = `${words.toLocaleString()} words • ${chars.toLocaleString()} characters`;
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = titleInput.value.trim();
    const content = contentInput.value.trim();

    if (!title || !content) {
      if (alertEl) {
        alertEl.className = "alert alert-error";
        alertEl.style.display = "block";
        alertEl.textContent = "Please provide both a document title and text content.";
      }
      return;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = `<span class="spinner-sm" style="display:inline-block;width:14px;height:14px;border:2px solid #fff;border-top-color:transparent;border-radius:50%;animation:spin 0.6s linear infinite;margin-right:6px;"></span> Indexing Document...`;
    }

    if (alertEl) alertEl.style.display = "none";

    try {
      const res = await window.apiClient.post("/documents/text", { title, content });

      if (alertEl) {
        alertEl.className = "alert alert-success";
        alertEl.style.display = "block";
        alertEl.textContent = res.message || `Document "${res.name}" successfully indexed (${res.chunk_count} chunks embedded).`;
      }

      form.reset();
      if (counterEl) counterEl.textContent = "0 words • 0 characters";

      // Refresh documents list
      await loadDocuments();

      // Auto-hide alert after 5s
      setTimeout(() => {
        if (alertEl) alertEl.style.display = "none";
      }, 5000);
    } catch (err) {
      console.error("[Documents] Text ingestion failed:", err);
      if (alertEl) {
        alertEl.className = "alert alert-error";
        alertEl.style.display = "block";
        alertEl.textContent = err.message || "Failed to index text document.";
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg> <span>Save & Index Document</span>`;
      }
    }
  });
}

/**
 * Document Preview Modal Setup & Renderer
 */
function setupPreviewModal() {
  const modal = document.getElementById("modal-doc-preview");
  const closeBtn = document.getElementById("btn-close-preview-modal");

  if (!modal) return;

  closeBtn?.addEventListener("click", () => {
    modal.style.display = "none";
  });

  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.style.display = "none";
  });
}

async function openDocumentPreview(docId, docName) {
  const modal = document.getElementById("modal-doc-preview");
  const titleEl = document.getElementById("preview-modal-title");
  const badgeEl = document.getElementById("preview-modal-badge");
  const sizeEl = document.getElementById("preview-doc-size");
  const statusEl = document.getElementById("preview-doc-status");
  const chunksEl = document.getElementById("preview-doc-chunks");
  const container = document.getElementById("preview-modal-chunks");

  if (!modal) return;
  modal.style.display = "flex";

  if (titleEl) titleEl.textContent = docName || "Document Preview";
  if (container) {
    container.innerHTML = `<div style="text-align:center;padding:32px;color:var(--text-muted);"><div class="spinner" style="margin:0 auto 12px;"></div>Loading document preview & semantic chunks...</div>`;
  }

  try {
    const data = await window.apiClient.get(`/documents/${docId}`);
    const doc = data.document || {};
    const chunks = data.sample_chunks || [];

    if (badgeEl) badgeEl.textContent = (doc.file_type || "txt").toUpperCase();
    if (sizeEl) sizeEl.textContent = formatFileSize(doc.file_size);
    if (statusEl) statusEl.textContent = (doc.status || "ready").toUpperCase();
    if (chunksEl) chunksEl.textContent = `${doc.chunk_count || chunks.length} chunks`;

    if (!container) return;

    if (chunks.length === 0) {
      container.innerHTML = `<div style="text-align:center;padding:32px;color:var(--text-muted);">No text chunks found for this document.</div>`;
      return;
    }

    container.innerHTML = "";
    chunks.forEach((c, idx) => {
      const card = document.createElement("div");
      card.className = "card";
      card.style.padding = "14px";
      card.style.backgroundColor = "var(--bg-page)";
      card.style.border = "1px solid var(--border-color)";

      card.innerHTML = `
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;font-size:0.8rem;color:var(--text-muted);">
          <span><strong>Chunk #${c.chunk_index !== undefined ? c.chunk_index + 1 : idx + 1}</strong> (Page ${c.page_number || 1})</span>
          <button type="button" class="btn btn-secondary btn-sm btn-copy-chunk" style="font-size:11px;padding:2px 8px;">Copy Chunk</button>
        </div>
        <div style="font-size:0.875rem;line-height:1.6;color:var(--text-main);white-space:pre-wrap;font-family:inherit;">${escapeHtml(c.content || "")}</div>
      `;

      card.querySelector(".btn-copy-chunk")?.addEventListener("click", (e) => {
        navigator.clipboard.writeText(c.content || "").then(() => {
          const btn = e.target;
          btn.textContent = "Copied!";
          setTimeout(() => { btn.textContent = "Copy Chunk"; }, 1500);
        });
      });

      container.appendChild(card);
    });
  } catch (err) {
    console.error("[Documents] Preview load error:", err);
    if (container) {
      container.innerHTML = `<div style="color:var(--danger);padding:24px;text-align:center;">Failed to load document preview: ${escapeHtml(err.message)}</div>`;
    }
  }
}
