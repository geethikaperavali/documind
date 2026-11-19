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
        <div style="display:inline-flex;gap:8px;">
          <a href="/chat.html" class="btn btn-secondary btn-sm" title="Chat with this document">Ask</a>
          <button class="btn btn-danger btn-sm btn-trigger-delete" data-id="${doc.id}" data-name="${escapeHtml(doc.name)}">Delete</button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });

  // Attach event handlers
  document.querySelectorAll(".btn-inspect-chunks").forEach(btn => {
    btn.addEventListener("click", () => inspectChunks(btn.dataset.id, btn.dataset.name));
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

  if (searchInput) searchInput.addEventListener("input", apply);
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
