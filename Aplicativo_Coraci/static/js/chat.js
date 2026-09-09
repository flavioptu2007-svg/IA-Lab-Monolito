/* ===================================================================
   Coraci Chat — Frontend JavaScript
   Streaming, conversas, temas, configurações
   =================================================================== */

// -------------------------------------------------------------------
// State
// -------------------------------------------------------------------

const state = {
    currentConversationId: null,
    isStreaming: false,
    abortController: null,
    config: {},
    conversations: [],
    theme: localStorage.getItem("coraci-theme") || "dark",
};

// -------------------------------------------------------------------
// DOM References
// -------------------------------------------------------------------

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const el = {
    // Sidebar
    sidebar: $("#sidebar"),
    sidebarOverlay: $("#sidebarOverlay"),
    openSidebar: $("#openSidebar"),
    closeSidebar: $("#closeSidebar"),
    newChat: $("#newChat"),
    conversationsList: $("#conversationsList"),
    settingsBtn: $("#openSettings"),

    // Chat
    messagesArea: $("#messagesArea"),
    welcomeScreen: $("#welcomeScreen"),
    chatTitle: $("#chatTitle"),
    chatModel: $("#chatModel"),
    messageInput: $("#messageInput"),
    sendButton: $("#sendButton"),
    stopButton: $("#stopButton"),
    toggleTheme: $("#toggleTheme"),

    // Header actions
    clearConversations: $("#clearConversations"),

    // Settings modal
    settingsModal: $("#settingsModal"),
    closeSettings: $("#closeSettings"),
    cancelSettings: $("#cancelSettings"),
    saveSettings: $("#saveSettings"),
    apiBaseUrl: $("#apiBaseUrl"),
    apiKey: $("#apiKey"),
    model: $("#model"),
    temperature: $("#temperature"),
    temperatureValue: $("#temperatureValue"),
    maxTokens: $("#maxTokens"),
    testConnection: $("#testConnection"),
    testResult: $("#testResult"),
    toggleApiKey: $("#toggleApiKey"),
};

// -------------------------------------------------------------------
// Theme
// -------------------------------------------------------------------

function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("coraci-theme", theme);
    state.theme = theme;
}

el.toggleTheme.addEventListener("click", () => {
    applyTheme(state.theme === "dark" ? "light" : "dark");
});

applyTheme(state.theme);

// -------------------------------------------------------------------
// Config
// -------------------------------------------------------------------

async function loadConfig() {
    try {
        const res = await fetch("/api/config");
        state.config = await res.json();
        el.apiBaseUrl.value = state.config.api_base_url || "";
        el.apiKey.value = state.config.api_key || "";
        el.model.value = state.config.model || "";
        el.temperature.value = state.config.temperature ?? 0.7;
        el.temperatureValue.textContent = state.config.temperature ?? 0.7;
        el.maxTokens.value = state.config.max_tokens ?? 4096;

        el.chatModel.textContent = state.config.model
            ? `🧠 ${state.config.model}`
            : "Conectando…";
    } catch (e) {
        console.warn("Erro ao carregar config:", e);
    }
}

async function saveConfig() {
    const cfg = {
        api_base_url: el.apiBaseUrl.value.trim(),
        api_key: el.apiKey.value.trim(),
        model: el.model.value.trim(),
        temperature: parseFloat(el.temperature.value),
        max_tokens: parseInt(el.maxTokens.value, 10) || 4096,
        theme: state.theme,
    };
    try {
        await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(cfg),
        });
        state.config = cfg;
        el.chatModel.textContent = cfg.model ? `🧠 ${cfg.model}` : "Conectando…";
    } catch (e) {
        console.warn("Erro ao salvar config:", e);
    }
}

// -------------------------------------------------------------------
// Conversations
// -------------------------------------------------------------------

async function loadConversations() {
    try {
        const res = await fetch("/api/conversations");
        state.conversations = await res.json();
        renderConversations();
    } catch (e) {
        console.warn("Erro ao carregar conversas:", e);
    }
}

function renderConversations() {
    const list = el.conversationsList;
    if (state.conversations.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <p style="padding: 20px 12px; color: var(--text-tertiary); font-size: 13px; text-align: center;">
                    Nenhuma conversa ainda
                </p>
            </div>`;
        return;
    }
    list.innerHTML = state.conversations
        .map(
            (c) => `
        <div class="conv-item ${c.id === state.currentConversationId ? "active" : ""}" data-id="${c.id}">
            <span class="conv-icon">💬</span>
            <span class="conv-title">${escapeHtml(c.title || "Nova conversa")}</span>
            <button class="conv-delete" data-id="${c.id}" title="Apagar conversa">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
            </button>
        </div>`
        )
        .join("");

    // Event listeners
    list.querySelectorAll(".conv-item").forEach((item) => {
        item.addEventListener("click", (e) => {
            if (e.target.closest(".conv-delete")) return;
            switchConversation(item.dataset.id);
        });
    });
    list.querySelectorAll(".conv-delete").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            deleteConversation(btn.dataset.id);
        });
    });
}

function switchConversation(id) {
    if (state.isStreaming) stopStreaming();
    state.currentConversationId = id;
    loadMessages(id);
    renderConversations();
    el.welcomeScreen.style.display = "none";
}

async function loadMessages(id) {
    try {
        const res = await fetch(`/api/conversations/${id}`);
        const conv = await res.json();
        el.chatTitle.textContent = conv.title || "Conversa";
        renderMessages(conv.messages || []);
    } catch (e) {
        console.warn("Erro ao carregar mensagens:", e);
    }
}

async function deleteConversation(id) {
    try {
        await fetch(`/api/conversations/${id}`, { method: "DELETE" });
        if (state.currentConversationId === id) {
            state.currentConversationId = null;
            el.chatTitle.textContent = "Nova conversa";
            showWelcome();
        }
        await loadConversations();
    } catch (e) {
        console.warn("Erro ao apagar conversa:", e);
    }
}

async function clearAllConversations() {
    if (!confirm("Apagar todas as conversas?")) return;
    try {
        await fetch("/api/conversations", { method: "DELETE" });
        state.currentConversationId = null;
        el.chatTitle.textContent = "Nova conversa";
        showWelcome();
        await loadConversations();
    } catch (e) {
        console.warn("Erro ao limpar conversas:", e);
    }
}

function newConversation() {
    if (state.isStreaming) stopStreaming();
    state.currentConversationId = null;
    el.chatTitle.textContent = "Nova conversa";
    showWelcome();
    renderConversations();
    el.messageInput.value = "";
    el.messageInput.focus();
    updateSendButton();
}

// -------------------------------------------------------------------
// Message Rendering
// -------------------------------------------------------------------

function renderMessages(messages) {
    const area = el.messagesArea;
    // Remove welcome and typing
    area.querySelectorAll(".message, .typing-indicator").forEach((el) => el.remove());
    el.welcomeScreen.style.display = "none";

    messages.forEach((msg) => {
        appendMessage(msg.role, msg.content);
    });

    scrollToBottom();
}

function appendMessage(role, content) {
    const area = el.messagesArea;
    const div = document.createElement("div");
    div.className = `message ${role}`;

    const avatar = role === "user" ? "🧑" : "🤖";
    const bubbleContent = role === "assistant" ? renderMarkdown(content) : escapeHtml(content);

    div.innerHTML = `
        <div class="avatar">${avatar}</div>
        <div class="bubble">${role === "assistant" ? bubbleContent : bubbleContent.replace(/\n/g, "<br>")}</div>
    `;

    area.appendChild(div);
    scrollToBottom();
    return div;
}

function updateLastMessage(content) {
    const area = el.messagesArea;
    const lastBubble = area.querySelector(".message.assistant:last-child .bubble");
    if (!lastBubble) return;

    const thinkingBlock = lastBubble.querySelector(".thinking-block");
    if (thinkingBlock) {
        // Reasoning was shown first — preserve it as collapsible + append content
        const thinkingHtml = `<details class="thinking-details" open>
            <summary>🧠 Raciocínio</summary>
            <div class="thinking-content">${escapeHtml(thinkingBlock.textContent)}</div>
        </details>`;
        lastBubble.innerHTML = thinkingHtml + renderMarkdown(content);
    } else {
        lastBubble.innerHTML = renderMarkdown(content);
    }

    // Re-highlight code blocks
    lastBubble.querySelectorAll("pre code").forEach((block) => {
        hljs && hljs.highlightElement(block);
    });
    scrollToBottom();
}

function showTyping() {
    const indicator = document.createElement("div");
    indicator.className = "typing-indicator";
    indicator.innerHTML = `
        <div class="avatar">🤖</div>
        <div class="typing-dots">
            <span></span><span></span><span></span>
        </div>
    `;
    el.messagesArea.appendChild(indicator);
    scrollToBottom();
}

function removeTyping() {
    el.messagesArea.querySelectorAll(".typing-indicator").forEach((el) => el.remove());
}

function showWelcome() {
    const area = el.messagesArea;
    area.querySelectorAll(".message, .typing-indicator").forEach((el) => el.remove());
    el.welcomeScreen.style.display = "flex";
}

function scrollToBottom() {
    const area = el.messagesArea;
    requestAnimationFrame(() => {
        area.scrollTop = area.scrollHeight;
    });
}

// -------------------------------------------------------------------
// Markdown Rendering (simple, lightweight)
// -------------------------------------------------------------------

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function renderMarkdown(text) {
    if (!text) return "";

    // Escape HTML first
    let html = escapeHtml(text);

    // Code blocks (fenced) — must be before other transforms
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
        const langClass = lang ? ` class="language-${lang}"` : "";
        return `<pre><code${langClass}>${code.trim()}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

    // Headers
    html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
    html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
    html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");

    // Bold & italic
    html = html.replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>");
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

    // Blockquotes
    html = html.replace(/^> (.+)$/gm, "<blockquote>$1</blockquote>");

    // Split into lines and group list items
    const lines = html.split('\n');
    const result = [];
    let inUl = false;
    let inOl = false;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const ulMatch = line.match(/^- (.+)/);
        const olMatch = line.match(/^\d+\. (.+)/);

        if (ulMatch) {
            if (inOl) { result.push('</ol>'); inOl = false; }
            if (!inUl) { result.push('<ul>'); inUl = true; }
            result.push(`<li>${ulMatch[1]}</li>`);
        } else if (olMatch) {
            if (inUl) { result.push('</ul>'); inUl = false; }
            if (!inOl) { result.push('<ol>'); inOl = true; }
            result.push(`<li>${olMatch[1]}</li>`);
        } else {
            if (inUl) { result.push('</ul>'); inUl = false; }
            if (inOl) { result.push('</ol>'); inOl = false; }
            result.push(line);
        }
    }
    if (inUl) result.push('</ul>');
    if (inOl) result.push('</ol>');

    html = result.join('\n');

    // Horizontal rules
    html = html.replace(/^---$/gm, "<hr>");

    // Paragraphs — double newline
    html = html.replace(/\n\n/g, "</p><p>");

    // Single line breaks within paragraphs
    html = html.replace(/\n/g, "<br>");

    // Wrap in paragraph if not already
    if (!html.startsWith("<")) {
        html = `<p>${html}</p>`;
    }

    return html;
}

// -------------------------------------------------------------------
// Streaming Chat
// -------------------------------------------------------------------

function updateSendButton() {
    const text = el.messageInput.value.trim();
    el.sendButton.disabled = !text || state.isStreaming;
}

async function sendMessage() {
    const message = el.messageInput.value.trim();
    if (!message || state.isStreaming) return;

    // Show user message
    appendMessage("user", message);
    el.messageInput.value = "";
    updateSendButton();

    // Show typing
    showTyping();

    state.isStreaming = true;
    el.sendButton.style.display = "none";
    el.stopButton.style.display = "flex";

    const abortController = new AbortController();
    state.abortController = abortController;

    let assistantMessage = "";
    let hasAssistantMessage = false;

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                conversation_id: state.currentConversationId,
                message: message,
            }),
            signal: abortController.signal,
        });

        if (!res.ok) {
            const err = await res.json();
            removeTyping();
            appendMessage("assistant", `❌ Erro: ${err.error || "Falha na requisição"}`);
            state.isStreaming = false;
            el.sendButton.style.display = "flex";
            el.stopButton.style.display = "none";
            return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                const data = line.slice(6).trim();
                if (!data) continue;

                let parsed;
                try {
                    parsed = JSON.parse(data);
                } catch (e) {
                    continue; // Skip malformed JSON
                }

                switch (parsed.type) {
                    case "conv_id":
                        state.currentConversationId = parsed.id;
                        el.chatTitle.textContent = message.slice(0, 60) + (message.length > 60 ? "…" : "");
                        await loadConversations();
                        break;

                    case "content":
                        if (!hasAssistantMessage) {
                            removeTyping();
                            // Create the assistant message bubble
                            const area = el.messagesArea;
                            const div = document.createElement("div");
                            div.className = "message assistant";
                            div.innerHTML = `
                                <div class="avatar">🤖</div>
                                <div class="bubble"></div>
                            `;
                            area.appendChild(div);
                            hasAssistantMessage = true;
                        }
                        assistantMessage += parsed.text;
                        updateLastMessage(assistantMessage);
                        break;

                    case "reasoning":
                        // Exibe raciocínio quando o modelo está pensando
                        if (!hasAssistantMessage) {
                            removeTyping();
                            const area = el.messagesArea;
                            const div = document.createElement("div");
                            div.className = "message assistant";
                            div.innerHTML = `
                                <div class="avatar">🤖</div>
                                <div class="bubble">
                                    <div class="thinking-block">${escapeHtml(parsed.text)}</div>
                                </div>
                            `;
                            area.appendChild(div);
                            hasAssistantMessage = true;
                        } else {
                            // Se já tem mensagem, atualiza o bloco de reasoning
                            const lastBubble = el.messagesArea.querySelector(".message.assistant:last-child .thinking-block");
                            if (lastBubble) {
                                lastBubble.textContent = parsed.text;
                            }
                        }
                        break;

                    case "done":
                        break;

                    case "error":
                        removeTyping();
                        if (!hasAssistantMessage) {
                            appendMessage("assistant", parsed.text);
                        } else {
                            updateLastMessage(assistantMessage + "\n\n" + parsed.text);
                        }
                        break;
                }
            }
        }
    } catch (e) {
        if (e.name === "AbortError") {
            // Stream was stopped by user
        } else {
            removeTyping();
            if (!hasAssistantMessage) {
                appendMessage("assistant", `❌ Erro de conexão: ${e.message}`);
            }
        }
    }

    state.isStreaming = false;
    el.sendButton.style.display = "flex";
    el.stopButton.style.display = "none";
    state.abortController = null;

    // Refresh conversations list
    await loadConversations();
}

function stopStreaming() {
    if (state.abortController) {
        state.abortController.abort();
        state.abortController = null;
    }
    state.isStreaming = false;
    el.sendButton.style.display = "flex";
    el.stopButton.style.display = "none";
    removeTyping();
}

// -------------------------------------------------------------------
// Settings Modal
// -------------------------------------------------------------------

function openSettings() {
    // Load current config into modal
    el.apiBaseUrl.value = state.config.api_base_url || "";
    el.apiKey.value = state.config.api_key || "";
    el.model.value = state.config.model || "";
    el.temperature.value = state.config.temperature ?? 0.7;
    el.temperatureValue.textContent = state.config.temperature ?? 0.7;
    el.maxTokens.value = state.config.max_tokens ?? 4096;
    el.testResult.classList.remove("show", "success", "error");
    el.testResult.textContent = "";
    el.settingsModal.classList.add("show");
}

function closeSettings() {
    el.settingsModal.classList.remove("show");
}

el.settingsBtn.addEventListener("click", openSettings);
el.closeSettings.addEventListener("click", closeSettings);
el.cancelSettings.addEventListener("click", closeSettings);

// Close modal on overlay click
el.settingsModal.addEventListener("click", (e) => {
    if (e.target === el.settingsModal) closeSettings();
});

el.temperature.addEventListener("input", () => {
    el.temperatureValue.textContent = el.temperature.value;
});

el.toggleApiKey.addEventListener("click", () => {
    const input = el.apiKey;
    input.type = input.type === "password" ? "text" : "password";
});

el.saveSettings.addEventListener("click", async () => {
    await saveConfig();
    closeSettings();
});

// Test connection
el.testConnection.addEventListener("click", async () => {
    const btn = el.testConnection;
    const result = el.testResult;
    btn.disabled = true;
    btn.classList.add("loading");
    result.classList.remove("show", "success", "error");
    result.textContent = "Testando conexão…";
    result.classList.add("show");

    try {
        const res = await fetch("/api/config/test", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                api_base_url: el.apiBaseUrl.value.trim(),
                api_key: el.apiKey.value.trim(),
            }),
        });
        const data = await res.json();
        if (data.status === "ok") {
            result.className = "test-result show success";
            result.innerHTML = `
                ✅ Conexão estabelecida com sucesso!
                <div class="model-list">
                    ${(data.models || []).map((m) => `<span class="model-tag">${escapeHtml(m)}</span>`).join("")}
                </div>
            `;
        } else {
            result.className = "test-result show error";
            result.textContent = data.message || "❌ Falha na conexão";
        }
    } catch (e) {
        result.className = "test-result show error";
        result.textContent = `❌ Erro: ${e.message}`;
    }

    btn.disabled = false;
    btn.classList.remove("loading");
});

// -------------------------------------------------------------------
// Input Handling
// -------------------------------------------------------------------

// Auto-resize textarea
el.messageInput.addEventListener("input", () => {
    el.messageInput.style.height = "auto";
    el.messageInput.style.height = Math.min(el.messageInput.scrollHeight, 150) + "px";
    updateSendButton();
});

// Send on Enter (Shift+Enter for newline)
el.messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

el.sendButton.addEventListener("click", sendMessage);
el.stopButton.addEventListener("click", stopStreaming);

// -------------------------------------------------------------------
// Sidebar Toggle (Mobile)
// -------------------------------------------------------------------

el.openSidebar.addEventListener("click", () => {
    el.sidebar.classList.add("open");
    el.sidebarOverlay.classList.add("show");
});

function closeSidebar() {
    el.sidebar.classList.remove("open");
    el.sidebarOverlay.classList.remove("show");
}

el.closeSidebar.addEventListener("click", closeSidebar);
el.sidebarOverlay.addEventListener("click", closeSidebar);

// -------------------------------------------------------------------
// New Chat Button
// -------------------------------------------------------------------

el.newChat.addEventListener("click", newConversation);

// -------------------------------------------------------------------
// Delete All
// -------------------------------------------------------------------

el.clearConversations.addEventListener("click", clearAllConversations);

// -------------------------------------------------------------------
// Welcome Suggestions
// -------------------------------------------------------------------

el.welcomeScreen.addEventListener("click", (e) => {
    const btn = e.target.closest(".suggestion-btn");
    if (btn) {
        el.messageInput.value = btn.dataset.prompt;
        updateSendButton();
        el.messageInput.focus();
        sendMessage();
    }
});

// -------------------------------------------------------------------
// Keyboard shortcuts
// -------------------------------------------------------------------

document.addEventListener("keydown", (e) => {
    // Ctrl+K — focus input
    if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        el.messageInput.focus();
    }
    // Escape — close settings / stop streaming
    if (e.key === "Escape") {
        if (el.settingsModal.classList.contains("show")) {
            closeSettings();
        } else if (state.isStreaming) {
            stopStreaming();
        }
    }
    // Ctrl+N — new conversation
    if ((e.ctrlKey || e.metaKey) && e.key === "n") {
        e.preventDefault();
        newConversation();
    }
});

// -------------------------------------------------------------------
// Init
// -------------------------------------------------------------------

async function init() {
    await loadConfig();
    await loadConversations();
    el.messageInput.focus();
}

init();
