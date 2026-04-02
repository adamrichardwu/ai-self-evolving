const agentLabel = document.getElementById("agent-label");
const focusLabel = document.getElementById("focus-label");
const loopLabel = document.getElementById("loop-label");
const summaryText = document.getElementById("summary-text");
const statusChip = document.getElementById("status-chip");
const messageList = document.getElementById("message-list");
const thoughtList = document.getElementById("thought-list");
const messageEmpty = document.getElementById("message-empty");
const thoughtEmpty = document.getElementById("thought-empty");
const composerForm = document.getElementById("composer-form");
const agentIdInput = document.getElementById("agent-id-input");
const counterpartNameInput = document.getElementById("counterpart-name-input");
const messageInput = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const errorText = document.getElementById("error-text");

function buildSelfModelPayload(agentId) {
  return {
    snapshot: {
      identity: {
        agent_id: agentId,
        chosen_name: "Astra",
        origin_story: "Bootstrapped from the FastAPI browser console.",
        core_commitments: ["truthfulness", "continuity", "responsiveness"],
      },
      capability: {
        known_limitations: ["cannot guarantee certainty"],
      },
      goals: {
        relationship_goals: ["maintain dialogue continuity"],
        active_task_goals: ["respond to the current user input"],
      },
      values: {},
      affect: {},
      attention: {
        current_focus: "maintain a continuous dialogue with the user",
      },
      metacognition: {},
      social: {
        active_relationships: ["Primary User"],
        trust_map: { "user-primary": 0.6 },
        role_in_current_context: "dialogue_partner",
        social_obligations: ["reply clearly", "preserve continuity"],
      },
      autobiography: {},
    },
    update_reason: "browser_console_bootstrap",
  };
}

function clearChildren(node) {
  while (node.firstChild) {
    node.removeChild(node.firstChild);
  }
}

function renderMessages(messages) {
  clearChildren(messageList);
  if (!messages.length) {
    messageList.appendChild(messageEmpty);
    return;
  }
  messages.forEach((message) => {
    const card = document.createElement("article");
    card.className = `message-card role-${message.role}`;

    const role = document.createElement("span");
    role.className = "message-role";
    role.textContent = message.role;

    const body = document.createElement("p");
    body.textContent = message.content;

    card.appendChild(role);
    card.appendChild(body);
    messageList.appendChild(card);
  });
}

function renderThoughts(thoughts) {
  clearChildren(thoughtList);
  if (!thoughts.length) {
    thoughtList.appendChild(thoughtEmpty);
    return;
  }

  thoughts
    .slice()
    .reverse()
    .forEach((thought) => {
      const card = document.createElement("article");
      card.className = "thought-card";

      const meta = document.createElement("div");
      meta.className = "thought-meta";
      meta.innerHTML = `<span>${thought.thought_type}</span><span>${thought.source}</span><span>salience ${Number(thought.salience_score).toFixed(2)}</span>`;

      const focus = document.createElement("strong");
      focus.textContent = thought.focus;

      const body = document.createElement("p");
      body.textContent = thought.content;

      card.appendChild(meta);
      card.appendChild(focus);
      card.appendChild(body);
      thoughtList.appendChild(card);
    });
}

async function ensureAgent(agentId) {
  const response = await fetch("/api/v1/self-models", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildSelfModelPayload(agentId)),
  });
  if (!response.ok && response.status !== 409) {
    throw new Error(await response.text() || "Failed to initialize agent.");
  }
}

async function syncState() {
  const agentId = agentIdInput.value.trim() || "agent-web-console";
  agentLabel.textContent = agentId;

  try {
    const response = await fetch(`/api/v1/language/${encodeURIComponent(agentId)}/state`);
    if (response.status === 404) {
      statusChip.textContent = "Agent not initialized yet";
      renderMessages([]);
      renderThoughts([]);
      return;
    }
    if (!response.ok) {
      throw new Error("Failed to load language state.");
    }
    const state = await response.json();
    renderMessages(state.messages || []);
    renderThoughts(state.thoughts || []);
    loopLabel.textContent = state.background_loop_enabled ? "active" : "idle";
    summaryText.textContent = state.summary?.summary_text || "No compressed memory yet.";
    if (state.thoughts && state.thoughts.length > 0) {
      focusLabel.textContent = state.thoughts[state.thoughts.length - 1].focus;
    }
    statusChip.textContent = "Connected";
    errorText.textContent = "";
  } catch (error) {
    statusChip.textContent = "API unavailable";
    errorText.textContent = error instanceof Error ? error.message : "Unknown error.";
  }
}

composerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const agentId = agentIdInput.value.trim() || "agent-web-console";
  const message = messageInput.value.trim();
  const counterpartName = counterpartNameInput.value.trim() || "Primary User";
  if (!message) {
    return;
  }

  sendButton.disabled = true;
  statusChip.textContent = "Sending...";
  errorText.textContent = "";

  try {
    await ensureAgent(agentId);
    const response = await fetch(`/api/v1/language/${encodeURIComponent(agentId)}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: message,
        counterpart_id: "user-primary",
        counterpart_name: counterpartName,
        relationship_type: "operator",
        observed_sentiment: "supportive",
      }),
    });
    if (!response.ok) {
      throw new Error(await response.text() || "Failed to send message.");
    }
    messageInput.value = "";
    await syncState();
  } catch (error) {
    errorText.textContent = error instanceof Error ? error.message : "Unknown error.";
    statusChip.textContent = "Interaction failed";
  } finally {
    sendButton.disabled = false;
  }
});

syncState();
window.setInterval(syncState, 3000);