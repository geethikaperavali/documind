/**
 * DOCUMIND AI ASSISTANT / RAG CHAT CONTROLLER
 * Manages conversations, message history, RAG queries, typing animations,
 * and grounded citation rendering.
 */

let activeConversationId = null;
let isGenerating = false;

document.addEventListener("DOMContentLoaded", async () => {
  const authenticated = await window.authManager.requireAuth();
  if (!authenticated) return;

  setupChatInput();
  setupNewChatButton();

  // Load conversation list
  await loadConversations();
});

/**
 * Loads user conversations list into sidebar
 */
async function loadConversations() {
  const listEl = document.getElementById("conversations-list");
  if (!listEl) return;

  try {
    const res = await window.apiClient.get("/chat/conversations");
    const convs = res.conversations || [];
    renderConversationsList(convs);

    if (convs.length > 0 && !activeConversationId) {
      // Select the first conversation
      selectConversation(convs[0].id);
    } else if (convs.length === 0) {
      // Start a fresh view
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
    listEl.innerHTML = `<div style="padding:16px;font-size:12px;color:var(--text-light);text-align:center;">No past conversations.</div>`;
    return;
  }

  convs.forEach(conv => {
    const div = document.createElement("div");
    div.className = `conv-item ${conv.id === activeConversationId ? "active" : ""}`;
    div.dataset.id = conv.id;

    div.innerHTML = `
      <div class="conv-title" title="${escapeHtml(conv.title)}">${escapeHtml(conv.title)}</div>
      <button class="btn-del-conv" data-id="${conv.id}" title="Delete conversation">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
      </button>
    `;

    div.addEventListener("click", (e) => {
      if (e.target.closest(".btn-del-conv")) return; // ignore if clicking delete
      selectConversation(conv.id);
    });

    const delBtn = div.querySelector(".btn-del-conv");
    delBtn.addEventListener("click", async (e) => {
      e.stopPropagation();
      if (confirm("Delete this conversation?")) {
        await deleteConversation(conv.id);
      }
    });

    listEl.appendChild(div);
  });
}

/**
 * Selects a conversation and loads its messages
 */
async function selectConversation(convId) {
  if (isGenerating) return;
  activeConversationId = convId;

  // Highlight active conversation in sidebar
  document.querySelectorAll(".conv-item").forEach(el => {
    el.classList.toggle("active", el.dataset.id === convId);
  });

  const messagesContainer = document.getElementById("chat-messages");
  if (messagesContainer) {
    messagesContainer.innerHTML = `<div style="text-align:center;padding:32px;color:var(--text-muted);">Loading conversation...</div>`;
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
    appendMessageUI(msg.role, msg.content, msg.sources);
  });

  scrollToBottom();
}

function renderWelcomeState() {
  const container = document.getElementById("chat-messages");
  if (!container) return;

  container.innerHTML = `
    <div class="empty-state" style="margin:auto 0;">
      <div class="brand-icon" style="width:48px;height:48px;font-size:22px;margin:0 auto 16px;">D</div>
      <div class="empty-title">DocuMind AI Assistant</div>
      <div class="empty-subtitle">
        Ask any question about your uploaded documents. All answers are strictly grounded in your knowledge base with source citations.
      </div>
      <div style="display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-top:16px;">
        <button class="btn btn-secondary btn-sm sample-prompt" data-prompt="Summarize the key points in my uploaded documents.">"Summarize key points"</button>
        <button class="btn btn-secondary btn-sm sample-prompt" data-prompt="What are the important dates and deadlines mentioned?">"Important dates & deadlines"</button>
        <button class="btn btn-secondary btn-sm sample-prompt" data-prompt="What are the main conclusions or recommendations?">"Conclusions & recommendations"</button>
      </div>
    </div>
  `;

  container.querySelectorAll(".sample-prompt").forEach(btn => {
    btn.addEventListener("click", () => {
      const textarea = document.getElementById("chat-textarea");
      if (textarea) {
        textarea.value = btn.dataset.prompt;
        submitQuestion();
      }
    });
  });
}

function appendMessageUI(role, content, sources = []) {
  const container = document.getElementById("chat-messages");
  if (!container) return;

  // Clear welcome state if present
  const empty = container.querySelector(".empty-state");
  if (empty) empty.remove();

  const isUser = role === "user";
  const row = document.createElement("div");
  row.className = `msg-row ${isUser ? "user" : "assistant"}`;

  const avatar = isUser
    ? `<div class="msg-avatar">You</div>`
    : `<div class="msg-avatar">AI</div>`;

  let formattedContent = escapeHtml(content)
    .replace(/\n\n/g, "</p><p>")
    .replace(/\n/g, "<br/>");
  formattedContent = `<p>${formattedContent}</p>`;

  // Build source citations box if present
  let citationsHtml = "";
  if (!isUser && sources && sources.length > 0) {
    let pills = "";
    sources.forEach(s => {
      pills += `
        <div class="citation-pill">
          <div class="citation-source-name">
            <span>📄 ${escapeHtml(s.document_name || "Document")} • Page ${s.page_number || 1}</span>
            <span style="font-size:10px;color:var(--text-light);">${Math.round((s.similarity || 0) * 100)}% match</span>
          </div>
          ${s.snippet ? `<div class="citation-snippet">"${escapeHtml(s.snippet)}"</div>` : ""}
        </div>
      `;
    });

    citationsHtml = `
      <div class="citations-box">
        <div class="citations-header">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
          <span>Grounded Sources (${sources.length})</span>
        </div>
        <div class="citation-pill-list">${pills}</div>
      </div>
    `;
  }

  row.innerHTML = `
    ${avatar}
    <div class="msg-body">
      <div class="msg-bubble">${formattedContent}</div>
      ${citationsHtml}
    </div>
  `;

  container.appendChild(row);
  scrollToBottom();
}

/**
 * Chat Input Setup (Enter to submit, Shift+Enter for new line)
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
    textarea.style.height = Math.min(textarea.scrollHeight, 140) + "px";
  });

  sendBtn.addEventListener("click", submitQuestion);
}

/**
 * Submits question to RAG backend
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

  // Show typing indicator
  isGenerating = true;
  if (sendBtn) sendBtn.disabled = true;
  showTypingIndicator();

  try {
    const payload = {
      question,
      conversation_id: activeConversationId || null,
      gemini_api_key: localStorage.getItem("documind_gemini_key") || null
    };

    const res = await window.apiClient.post("/chat/ask", payload);

    removeTypingIndicator();

    // If new conversation was created on the fly
    if (!activeConversationId && res.conversation_id) {
      activeConversationId = res.conversation_id;
      await loadConversations();
    }

    appendMessageUI("assistant", res.answer, res.sources);

  } catch (err) {
    removeTypingIndicator();
    appendMessageUI("assistant", `**Error:** ${err.message}`);
  } finally {
    isGenerating = false;
    if (sendBtn) sendBtn.disabled = false;
  }
}

function showTypingIndicator() {
  const container = document.getElementById("chat-messages");
  if (!container) return;

  const row = document.createElement("div");
  row.className = "msg-row assistant";
  row.id = "typing-row";
  row.innerHTML = `
    <div class="msg-avatar">AI</div>
    <div class="msg-body">
      <div class="typing-bubble">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>
  `;
  container.appendChild(row);
  scrollToBottom();
}

function removeTypingIndicator() {
  const typingRow = document.getElementById("typing-row");
  if (typingRow) typingRow.remove();
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
