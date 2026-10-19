const recordForm = document.getElementById("record-form");
const recordList = document.getElementById("record-list");
const summaryBox = document.getElementById("summary-box");

const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatMessages = document.getElementById("chat-messages");
const conversationSelect = document.getElementById("conversation-select");
const newChatBtn = document.getElementById("new-chat-btn");
const deleteChatBtn = document.getElementById("delete-chat-btn");

let currentConversationId = null;

// ---------- 공통 fetch 헬퍼 ----------
async function api(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `요청 실패 (${res.status})`);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ---------- 운동 기록 CRUD ----------
async function loadRecords() {
  const records = await api("/api/data");
  recordList.innerHTML = "";
  records
    .slice()
    .reverse()
    .forEach((r) => {
      const li = document.createElement("li");
      li.innerHTML = `
        <span>
          <b>${r.date}</b> · ${r.value}분
          <span class="r-meta">${r.memo || ""}</span>
        </span>
        <button class="r-del" data-id="${r.id}">삭제</button>
      `;
      recordList.appendChild(li);
    });

  recordList.querySelectorAll(".r-del").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await api(`/api/data/${btn.dataset.id}`, { method: "DELETE" });
      await Promise.all([loadRecords(), loadSummary()]);
    });
  });
}

async function loadSummary() {
  const s = await api("/api/data/summary");
  summaryBox.innerHTML = `
    총 <b>${s.total_sessions}</b>회 · 총 <b>${s.total_minutes}</b>분 ·
    평균 <b>${s.avg_minutes_per_session}</b>분/회<br />
    최근 7일 <b>${s.sessions_last_7_days}</b>회 · 최근 30일 <b>${s.sessions_last_30_days}</b>회 ·
    주당 평균 <b>${s.avg_sessions_per_week}</b>회
  `;
}

recordForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const date = document.getElementById("input-date").value;
  const value = Number(document.getElementById("input-value").value);
  const memo = document.getElementById("input-memo").value;

  await api("/api/data", {
    method: "POST",
    body: JSON.stringify({ date, value, memo }),
  });

  recordForm.reset();
  await Promise.all([loadRecords(), loadSummary()]);
});

// ---------- 대화 관리 ----------
async function loadConversations() {
  const conversations = await api("/api/conversations");
  conversationSelect.innerHTML = "";
  conversations.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = c.title || "제목 없음";
    conversationSelect.appendChild(opt);
  });

  if (conversations.length > 0) {
    currentConversationId = conversations[0].id;
    conversationSelect.value = currentConversationId;
    renderMessages(conversations[0].messages || []);
  } else {
    currentConversationId = null;
    chatMessages.innerHTML = "";
  }
}

function renderMessages(messages) {
  chatMessages.innerHTML = "";
  messages.forEach((m) => appendMessage(m.role, m.content));
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendMessage(role, content) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = content;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

conversationSelect.addEventListener("change", async () => {
  currentConversationId = conversationSelect.value;
  const conv = await api(`/api/conversations/${currentConversationId}`);
  renderMessages(conv.messages || []);
});

newChatBtn.addEventListener("click", async () => {
  const conv = await api("/api/conversations", {
    method: "POST",
    body: JSON.stringify({ title: "새 대화" }),
  });
  await loadConversations();
  currentConversationId = conv.id;
  conversationSelect.value = conv.id;
  chatMessages.innerHTML = "";
});

deleteChatBtn.addEventListener("click", async () => {
  if (!currentConversationId) return;
  await api(`/api/conversations/${currentConversationId}`, { method: "DELETE" });
  await loadConversations();
});

// ---------- 챗봇 ----------
chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;

  appendMessage("user", message);
  chatInput.value = "";

  try {
    const res = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        conversation_id: currentConversationId,
        message,
      }),
    });
    currentConversationId = res.conversation_id;
    appendMessage("assistant", res.reply);
    await loadConversations();
    conversationSelect.value = currentConversationId;
  } catch (err) {
    appendMessage("assistant", `⚠️ 오류: ${err.message}`);
  }
});

// ---------- 초기화 ----------
(async function init() {
  try {
    await Promise.all([loadRecords(), loadSummary(), loadConversations()]);
  } catch (err) {
    summaryBox.innerHTML = `⚠️ 백엔드 연결 실패: ${err.message} (config.js의 API_BASE_URL 확인)`;
  }
})();
