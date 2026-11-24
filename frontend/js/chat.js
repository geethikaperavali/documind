/**
 * DOCUMIND PROFESSIONAL AI ASSISTANT & RAG CHAT CONTROLLER
 * High-fidelity Markdown rendering, syntax code block copy,
 * grounded citations with clickable web links, response controls,
 * and intelligent orchestration badge integration.
 */

let activeConversationId = null;
let isGenerating = false;
let conversationsCache = [];

document.addEventListener("DOMContentLoaded", async () => {
  const authenticated = await window.authManager.requireAuth();
  if (!authenticated) return;

  setupChatInput();
  setupNewChatButton();
  setupSearchFilter();
  setupMobileDrawer();

  // Load conversation list
  await loadConversations();
});

/**
 * Configure Marked.js with Github Flavored Markdown & Code Block Wrappers
 */
function renderMarkdownSafely(rawMarkdown) {
  if (!rawMarkdown) return "";

  try {
    if (window.marked) {
      // Use marked renderer
      const renderer = new marked.Renderer();
      
      // Custom code block renderer with copy button
      renderer.code = function(code, lang) {
        const cleanLang = (lang || "plaintext").trim().toLowerCase();
        const escapedCode = escapeHtml(code);
        return `
          <div class="code-block-wrapper">
            <div class="code-block-header">
              <span>${cleanLang}</span>
              <button class="btn-copy-code" type="button" onclick="copyCodeFromBlock(this)">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                <span>Copy</span>
              </button>
            </div>
            <pre><code class="language-${cleanLang}">${escapedCode}</code></pre>
          </div>
        `;
      };

      marked.setOptions({
        renderer: renderer,
        gfm: true,
        breaks: true
      });

      const parsedHtml = marked.parse(rawMarkdown);
      return window.DOMPurify ? DOMPurify.sanitize(parsedHtml) : parsedHtml;
    }
  } catch (e) {
    console.warn("[Chat] Marked.js parse error, using fallback parser:", e);
  }

  // Fallback markdown parser if marked is unavailable
  return fallbackMarkdownParser(rawMarkdown);
}

function fallbackMarkdownParser(md) {
  let html = escapeHtml(md);

  // Headers
  html = html.replace(/^### (.*$)/gim, "<h3>$1</h3>");
  html = html.replace(/^## (.*$)/gim, "<h2>$1</h2>");
  html = html.replace(/^# (.*$)/gim, "<h1>$1</h1>");

  // Bold & Italic
  html = html.replace(/\*\*(.*?)\*\*/gim, "<strong>$1</strong>");
  html = html.replace(/\*(.*?)\*/gim, "<em>$1</em>");

  // Blockquotes
  html = html.replace(/^\> (.*$)/gim, "<blockquote>$1</blockquote>");

  // Inline code
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Unordered lists
  html = html.replace(/^\- (.*$)/gim, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>)/gims, "<ul>$1</ul>");

  // Paragraphs
  html = html.replace(/\n\n/g, "</p><p>");
  html = `<p>${html}</p>`;
  return html;
}

window.copyCodeFromBlock = function(btn) {
  const wrapper = btn.closest(".code-block-wrapper");
  if (!wrapper) return;
  const codeEl = wrapper.querySelector("code");
  if (!codeEl) return;

  navigator.clipboard.writeText(codeEl.innerText).then(() => {
    const span = btn.querySelector("span");
    if (span) {
      const orig = span.textContent;
      span.textContent = "Copied!";
      setTimeout(() => { span.textContent = orig; }, 1800);
    }
  }).catch(err => {
    console.error("Failed to copy code: ", err);
  });
};

/**
 * Loads user conversations list into sidebar
 */
async function loadConversations() {
  const listEl = document.getElementById("conversations-list");
  if (!listEl) return;

  try {
    const res = await window.apiClient.get("/chat/conversations");
    conversationsCache = res.conversations || [];
    renderConversationsList(conversationsCache);

    if (conversationsCache.length > 0 && !activeConversationId) {
      selectConversation(conversationsCache[0].id);
    } else if (conversationsCache.length === 0) {
      startNewConversationView();
    }
  } catch (err) {
    console.error("[Chat] Failed to load conversations:", err);
  }
}

function renderConversationsList(convs) {
  const listEl = document.getElementById("conversations-list");
  if (!listEl) return;

  listEl.innerHTML = "";

  if (convs.length === 0) {
    listEl.innerHTML = `<div style="padding:16px;font-size:12px;color:var(--text-light);text-align:center;">No conversations found.</div>`;
    return;
  }

  convs.forEach(conv => {
    const div = document.createElement("div");
    div.className = `conv-item ${conv.id === activeConversationId ? "active" : ""}`;
    div.dataset.id = conv.id;

    div.innerHTML = `
      <div class="conv-title" title="${escapeHtml(conv.title)}">${escapeHtml(conv.title)}</div>
      <button class="btn-del-conv" data-id="${conv.id}" title="Delete conversation" aria-label="Delete">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
      </button>
    `;

    div.addEventListener("click", (e) => {
      if (e.target.closest(".btn-del-conv")) return;
      selectConversation(conv.id);
    });

    const delBtn = div.querySelector(".btn-del-conv");
    delBtn.addEventListener("click", async (e) => {
      e.stopPropagation();
      if (confirm("Delete this conversation thread?")) {
        await deleteConversation(conv.id);
      }
    });

    listEl.appendChild(div);
  });
}

function setupSearchFilter() {
  const searchInput = document.getElementById("conv-search");
  if (!searchInput) return;

  searchInput.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase().trim();
    if (!q) {
      renderConversationsList(conversationsCache);
      return;
    }
    const filtered = conversationsCache.filter(c => (c.title || "").toLowerCase().includes(q));
    renderConversationsList(filtered);
  });
}

/**
 * Selects a conversation and loads its messages
 */
async function selectConversation(convId) {
  if (isGenerating) return;
  activeConversationId = convId;

  document.querySelectorAll(".conv-item").forEach(el => {
    el.classList.toggle("active", el.dataset.id === convId);
  });

  const messagesContainer = document.getElementById("chat-messages");
  if (messagesContainer) {
    messagesContainer.innerHTML = `<div style="text-align:center;padding:48px;color:var(--text-muted);font-size:13px;">Loading conversation history...</div>`;
  }

  try {
    const res = await window.apiClient.get(`/chat/conversations/${convId}/messages`);
    const messages = res.messages || [];
    renderMessages(messages);
  } catch (err) {
    console.error("[Chat] Error loading messages:", err);
    if (messagesContainer) {
      messagesContainer.innerHTML = `<div style="color:var(--danger);text-align:center;padding:24px;">Failed to load messages: ${err.message}</div>`;
    }
  }
}

/**
 * Renders message thread
 */
function renderMessages(messages) {
  const container = document.getElementById("chat-messages");
  if (!container) return;

  container.innerHTML = "";

  if (messages.length === 0) {
    renderWelcomeState();
    return;
  }

  messages.forEach(msg => {
    appendMessageUI(msg.role, msg.content, msg.sources, msg.orchestration_mode);
  });

  scrollToBottom();
}

/**
 * Editorial Welcome / Empty State with Curated Research Suggestions
 */
function renderWelcomeState() {
  const container = document.getElementById("chat-messages");
  if (!container) return;

  container.innerHTML = `
    <div class="chat-empty-state">
      <div class="chat-empty-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
      </div>
      <div class="chat-empty-title">DocuMind AI Assistant</div>
      <div class="chat-empty-subtitle">
        Intelligent research across your uploaded documents, verified web authorities, AI industry benchmarks, and temporal compliance.
      </div>
      
      <div class="suggested-prompts-grid">
        <div class="prompt-card" data-prompt="Summarize the core requirements, deliverables, and conclusions in my uploaded documents.">
          <div class="prompt-card-header">
            <span>Knowledge Base</span>
          </div>
          <div class="prompt-card-text">"Summarize the core requirements and deliverables in my uploaded documents."</div>
        </div>

        <div class="prompt-card" data-prompt="Compare Gemini 2.5 Pro vs Claude 3.5 Sonnet on SWE-bench, context windows, and token pricing.">
          <div class="prompt-card-header">
            <span>AI Intelligence</span>
          </div>
          <div class="prompt-card-text">"Compare Gemini 2.5 Pro vs Claude 3.5 Sonnet on SWE-bench and token pricing."</div>
        </div>

        <div class="prompt-card" data-prompt="Is Section 377 of IPC or old IT Act Section 66A currently active, amended, or repealed?">
          <div class="prompt-card-header">
            <span>Temporal Verification</span>
          </div>
          <div class="prompt-card-text">"Is Section 377 of IPC or old IT Act Section 66A currently active or repealed?"</div>
        </div>

        <div class="prompt-card" data-prompt="What is the latest RBI repo rate decision, inflation outlook, and current monetary stance?">
          <div class="prompt-card-header">
            <span>Market & Policy</span>
          </div>
          <div class="prompt-card-text">"What is the latest RBI repo rate decision and monetary policy stance?"</div>
        </div>
      </div>
    </div>
  `;

  container.querySelectorAll(".prompt-card").forEach(card => {
    card.addEventListener("click", () => {
      const textarea = document.getElementById("chat-textarea");
      if (textarea) {
        textarea.value = card.dataset.prompt;
        submitQuestion();
      }
    });
  });
}

/**
 * Appends a Message (User or Assistant) with Markdown, Citations & Action Controls
 */
function appendMessageUI(role, content, sources = [], orchestrationMode = null) {
  const container = document.getElementById("chat-messages");
  if (!container) return;

  const empty = container.querySelector(".chat-empty-state");
  if (empty) empty.remove();

  const isUser = role === "user";
  const row = document.createElement("div");
  row.className = `msg-row ${isUser ? "user" : "assistant"}`;

  const avatar = isUser
    ? `<div class="msg-avatar">You</div>`
    : `<div class="msg-avatar">DM</div>`;

  // Render markdown for assistant, safe text for user
  const formattedContent = isUser
    ? `<div class="msg-bubble">${escapeHtml(content).replace(/\n/g, "<br/>")}</div>`
    : `<div class="msg-bubble">${renderMarkdownSafely(content)}</div>`;

  // Build Citations Box
  let citationsHtml = "";
  if (!isUser && sources && sources.length > 0) {
    let pills = "";
    sources.forEach(s => {
      const isWeb = s.url || (s.document_name && s.document_name.includes("["));
      const title = s.document_name || "Document Source";
      const pageOrBadge = s.page_number ? `Page ${s.page_number}` : (s.category || "Official Source");
      const matchScore = s.similarity ? `${Math.round(s.similarity * 100)}% confidence` : "Authoritative";

      if (s.url) {
        pills += `
          <a href="${escapeHtml(s.url)}" target="_blank" rel="noopener noreferrer" class="citation-pill" title="Open source link in new tab">
            <div class="citation-source-name">
              <span>${escapeHtml(title)}</span>
              <span class="citation-badge-tag">${escapeHtml(String(pageOrBadge))}</span>
            </div>
            ${s.snippet ? `<div class="citation-snippet">${escapeHtml(s.snippet)}</div>` : ""}
          </a>
        `;
      } else {
        pills += `
          <div class="citation-pill">
            <div class="citation-source-name">
              <span>${escapeHtml(title)}</span>
              <span class="citation-badge-tag">${escapeHtml(String(pageOrBadge))}</span>
            </div>
            ${s.snippet ? `<div class="citation-snippet">${escapeHtml(s.snippet)}</div>` : ""}
          </div>
        `;
      }
    });

    citationsHtml = `
      <div class="citations-box">
        <div class="citations-header">
          <div style="display:flex;align-items:center;gap:6px;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
            <span>Verified Citations (${sources.length})</span>
          </div>
          <span style="font-size:11px;color:var(--text-light);">Traceable Grounding</span>
        </div>
        <div class="citation-pill-list">${pills}</div>
      </div>
    `;
  }

  // Response Controls Bar (Copy Answer, Badges)
  let actionsBar = "";
  if (!isUser) {
    let modeBadge = "";
    if (orchestrationMode === "TEMPORAL_VERIFY") {
      modeBadge = `<span class="orchestration-badge temporal">Temporal Verification</span>`;
    } else if (orchestrationMode === "AI_INTELLIGENCE") {
      modeBadge = `<span class="orchestration-badge ai">AI Industry Intelligence</span>`;
    } else if (orchestrationMode === "HYBRID") {
      modeBadge = `<span class="orchestration-badge hybrid">Hybrid RAG + Web</span>`;
    } else if (orchestrationMode === "WEB_RESEARCH") {
      modeBadge = `<span class="orchestration-badge">Live Web Search</span>`;
    } else {
      modeBadge = `<span class="orchestration-badge">Grounded Document RAG</span>`;
    }

    actionsBar = `
      <div class="msg-actions-bar">
        <button type="button" class="msg-action-btn btn-copy-answer" title="Copy answer text">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
          <span>Copy Answer</span>
        </button>
        ${modeBadge}
      </div>
    `;
  }

  row.innerHTML = `
    ${avatar}
    <div class="msg-body">
      ${formattedContent}
      ${citationsHtml}
      ${actionsBar}
    </div>
  `;

  if (!isUser) {
    const copyBtn = row.querySelector(".btn-copy-answer");
    if (copyBtn) {
      copyBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(content).then(() => {
          const span = copyBtn.querySelector("span");
          if (span) {
            span.textContent = "Copied to Clipboard!";
            setTimeout(() => { span.textContent = "Copy Answer"; }, 2000);
          }
        });
      });
    }
  }

  container.appendChild(row);
  scrollToBottom();
}

/**
 * Chat Input Setup (Enter to submit, Shift+Enter for newline, auto-expansion)
 */
function setupChatInput() {
  const textarea = document.getElementById("chat-textarea");
  const sendBtn = document.getElementById("btn-send-chat");

  if (!textarea || !sendBtn) return;

  textarea.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitQuestion();
    }
  });

  textarea.addEventListener("input", () => {
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 160) + "px";
  });

  sendBtn.addEventListener("click", submitQuestion);
}

/**
 * Submits question to DocuMind Orchestration Engine
 */
async function submitQuestion() {
  if (isGenerating) return;

  const textarea = document.getElementById("chat-textarea");
  const sendBtn = document.getElementById("btn-send-chat");
  const question = textarea ? textarea.value.trim() : "";

  if (!question) return;

  // Clear input
  textarea.value = "";
  textarea.style.height = "auto";

  // Append user message immediately
  appendMessageUI("user", question);

  // Show generating indicator
  isGenerating = true;
  if (sendBtn) sendBtn.disabled = true;
  showGeneratingIndicator();

  try {
    const payload = {
      question,
      conversation_id: activeConversationId || null,
      gemini_api_key: localStorage.getItem("documind_gemini_key") || null
    };

    const res = await window.apiClient.post("/chat/ask", payload);

    removeGeneratingIndicator();

    // If new conversation was created on the fly
    if (!activeConversationId && res.conversation_id) {
      activeConversationId = res.conversation_id;
      await loadConversations();
    }

    appendMessageUI("assistant", res.answer, res.sources, res.orchestration_mode);

  } catch (err) {
    removeGeneratingIndicator();
    appendMessageUI("assistant", `**Request Error:** ${err.message || "Unable to contact DocuMind AI engine."}`);
  } finally {
    isGenerating = false;
    if (sendBtn) sendBtn.disabled = false;
  }
}

function showGeneratingIndicator() {
  const container = document.getElementById("chat-messages");
  if (!container) return;

  const row = document.createElement("div");
  row.className = "msg-row assistant";
  row.id = "generating-row";
  row.innerHTML = `
    <div class="msg-avatar">DM</div>
    <div class="msg-body">
      <div class="generating-indicator">
        <div class="pulse-spinner"></div>
        <span>Searching verified sources & synthesizing response...</span>
      </div>
    </div>
  `;
  container.appendChild(row);
  scrollToBottom();
}

function removeGeneratingIndicator() {
  const row = document.getElementById("generating-row");
  if (row) row.remove();
}

function setupNewChatButton() {
  const btn = document.getElementById("btn-new-chat");
  if (btn) {
    btn.addEventListener("click", () => {
      startNewConversationView();
    });
  }
}

function startNewConversationView() {
  activeConversationId = null;
  document.querySelectorAll(".conv-item").forEach(el => el.classList.remove("active"));
  renderWelcomeState();
  const textarea = document.getElementById("chat-textarea");
  if (textarea) textarea.focus();
}

async function deleteConversation(convId) {
  try {
    await window.apiClient.delete(`/chat/conversations/${convId}`);
    if (activeConversationId === convId) {
      startNewConversationView();
    }
    await loadConversations();
  } catch (err) {
    alert("Failed to delete conversation: " + err.message);
  }
}

function setupMobileDrawer() {
  const toggleBtn = document.getElementById("btn-toggle-convs");
  const sidebar = document.getElementById("chat-sidebar");
  if (!toggleBtn || !sidebar) return;

  toggleBtn.addEventListener("click", () => {
    sidebar.classList.toggle("open");
  });
}

function scrollToBottom() {
  const container = document.getElementById("chat-messages");
  if (container) {
    container.scrollTop = container.scrollHeight;
  }
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
