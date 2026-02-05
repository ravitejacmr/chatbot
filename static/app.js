const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatLog = document.getElementById("chat-log");
const providerSelect = document.getElementById("provider");

const appendBubble = (text, role) => {
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${role}`;
  bubble.textContent = text;
  chatLog.appendChild(bubble);
  chatLog.scrollTop = chatLog.scrollHeight;
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
    if (data.detail && !data.reply) {
      appendBubble(`Error detail: ${data.detail}`, "bot");
    }
  } catch (error) {
    placeholder.textContent = "Failed to reach the chat service.";
  }
});
