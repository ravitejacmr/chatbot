const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatLog = document.getElementById("chat-log");
const providerSelect = document.getElementById("provider");

const sendForm = document.getElementById("send-form");
const sendOutput = document.getElementById("send-output");

const deleteForm = document.getElementById("delete-form");
const deleteOutput = document.getElementById("delete-output");

const listForm = document.getElementById("list-form");
const listOutput = document.getElementById("list-output");

const appendBubble = (text, role) => {
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${role}`;
  bubble.textContent = text;
  chatLog.appendChild(bubble);
  chatLog.scrollTop = chatLog.scrollHeight;
};

const renderJson = (target, data) => {
  target.textContent = JSON.stringify(data, null, 2);
};

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;
  appendBubble(message, "user");
  chatInput.value = "";
  appendBubble("Thinking...", "bot");
  const placeholder = chatLog.lastChild;
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        provider: providerSelect.value,
      }),
    });
    const data = await response.json();
    placeholder.textContent =
      data.reply || data.error || data.detail || "No response.";
    if (data.action) {
      appendBubble(JSON.stringify(data.action, null, 2), "bot");
    }
  } catch (error) {
    placeholder.textContent = "Failed to reach the chat service.";
  }
});

sendForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    to: document.getElementById("send-to").value,
    subject: document.getElementById("send-subject").value,
    body: document.getElementById("send-body").value,
  };
  const response = await fetch("/api/email/send", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  renderJson(sendOutput, await response.json());
});

deleteForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    message_id: document.getElementById("delete-id").value,
  };
  const response = await fetch("/api/email/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  renderJson(deleteOutput, await response.json());
});

const refreshList = async (query = "") => {
  const params = new URLSearchParams();
  if (query) params.append("query", query);
  const response = await fetch(`/api/email/list?${params.toString()}`);
  const data = await response.json();
  listOutput.innerHTML = "";
  (data.emails || []).forEach((email) => {
    const item = document.createElement("li");
    item.className = "email-item";
    item.innerHTML = `
      <h4>${email.subject}</h4>
      <p><strong>From:</strong> ${email.from}</p>
      <p>${email.snippet}</p>
      <small>ID: ${email.id}</small>
    `;
    listOutput.appendChild(item);
  });
  if (data.warning) {
    const warn = document.createElement("li");
    warn.className = "email-item";
    warn.textContent = data.warning;
    listOutput.appendChild(warn);
  }
};

listForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  refreshList(document.getElementById("list-query").value);
});

refreshList();
