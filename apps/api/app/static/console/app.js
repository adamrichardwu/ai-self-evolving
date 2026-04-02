const agentLabel = document.getElementById("agent-label");
const focusLabel = document.getElementById("focus-label");
const goalLabel = document.getElementById("goal-label");
const loopLabel = document.getElementById("loop-label");
const summaryText = document.getElementById("summary-text");
const statusChip = document.getElementById("status-chip");
const identityName = document.getElementById("identity-name");
const identityOrigin = document.getElementById("identity-origin");
const identityCommitments = document.getElementById("identity-commitments");
const identityNarrative = document.getElementById("identity-narrative");
const counterpartLabel = document.getElementById("counterpart-label");
const counterpartRole = document.getElementById("counterpart-role");
const counterpartRelationship = document.getElementById("counterpart-relationship");
const identityStatus = document.getElementById("identity-status");
const counterpartObligations = document.getElementById("counterpart-obligations");
const evolutionChip = document.getElementById("evolution-chip");
const evolutionDelta = document.getElementById("evolution-delta");
const evolutionBenchmark = document.getElementById("evolution-benchmark");
const evolutionBenchmarkShift = document.getElementById("evolution-benchmark-shift");
const evolutionVerdict = document.getElementById("evolution-verdict");
const evolutionHypothesis = document.getElementById("evolution-hypothesis");
const evolutionPolicy = document.getElementById("evolution-policy");
const evolutionMutations = document.getElementById("evolution-mutations");
const goalList = document.getElementById("goal-list");
const goalEmpty = document.getElementById("goal-empty");
const messageList = document.getElementById("message-list");
const thoughtList = document.getElementById("thought-list");
const traceList = document.getElementById("trace-list");
const messageEmpty = document.getElementById("message-empty");
const thoughtEmpty = document.getElementById("thought-empty");
const traceEmpty = document.getElementById("trace-empty");
const composerForm = document.getElementById("composer-form");
const agentIdInput = document.getElementById("agent-id-input");
const counterpartNameInput = document.getElementById("counterpart-name-input");
const counterpartRoleInput = document.getElementById("counterpart-role-input");
const evolutionForm = document.getElementById("evolution-form");
const evolutionObjectiveInput = document.getElementById("evolution-objective-input");
const evolutionButton = document.getElementById("evolution-button");
const evolutionErrorText = document.getElementById("evolution-error-text");
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
        role_in_current_context: "operator",
        social_obligations: ["reply clearly", "preserve continuity"],
      },
      autobiography: {
        long_term_narrative: "I am trying to remain a continuous agent that can distinguish self from user.",
      },
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

function renderGoals(goals) {
  clearChildren(goalList);
  if (!goals.length) {
    goalList.appendChild(goalEmpty);
    return;
  }

  goals.forEach((goal) => {
    const card = document.createElement("article");
    card.className = "goal-card";

    const meta = document.createElement("span");
    meta.className = "goal-meta";
    meta.textContent = `${goal.goal_type} · ${goal.time_horizon} · ${goal.status}`;

    const title = document.createElement("strong");
    title.textContent = goal.title;

    const body = document.createElement("p");
    body.textContent = goal.description;

    card.appendChild(meta);
    card.appendChild(title);
    card.appendChild(body);
    goalList.appendChild(card);
  });
}

function renderTraces(traces) {
  clearChildren(traceList);
  if (!traces.length) {
    traceList.appendChild(traceEmpty);
    return;
  }

  traces.forEach((trace) => {
    const card = document.createElement("article");
    card.className = "trace-card";

    const meta = document.createElement("div");
    meta.className = "trace-meta";
    meta.innerHTML = `<span>${trace.action_taken}</span><span>${trace.identity_status}</span><span>${trace.relationship_type || "unknown"}</span>`;

    const focus = document.createElement("strong");
    focus.textContent = trace.current_focus || "No focus recorded.";

    const goal = document.createElement("p");
    goal.textContent = trace.dominant_goal ? `Goal: ${trace.dominant_goal}` : "Goal: none recorded.";

    const detail = document.createElement("p");
    detail.textContent = trace.assistant_text || trace.summary_text || trace.thought_focus || "No additional trace detail.";

    card.appendChild(meta);
    card.appendChild(focus);
    card.appendChild(goal);
    card.appendChild(detail);
    traceList.appendChild(card);
  });
}

function renderEvolution(runs) {
  const latest = runs.length ? runs[0] : null;
  if (!latest) {
    evolutionChip.textContent = "No run";
    evolutionDelta.textContent = "0.0000";
    evolutionBenchmark.textContent = "0.0000";
    evolutionBenchmarkShift.textContent = "0.0000 -> 0.0000";
    evolutionVerdict.textContent = "needs_review";
    evolutionHypothesis.textContent = "No evolution hypothesis yet.";
    evolutionPolicy.textContent = "No promoted policy yet.";
    evolutionMutations.textContent = "No mutation proposals yet.";
    return;
  }

  evolutionChip.textContent = latest.promoted ? "Promoted" : latest.strategy_status;
  evolutionDelta.textContent = Number(latest.score_delta || 0).toFixed(4);
  evolutionBenchmark.textContent = `${Number(latest.benchmark_score || 0).toFixed(4)} / ${Number(latest.utility_score || 0).toFixed(4)}`;
  evolutionBenchmarkShift.textContent = `${Number(latest.baseline_benchmark_score || 0).toFixed(4)} -> ${Number(latest.benchmark_score || 0).toFixed(4)}`;
  evolutionVerdict.textContent = latest.verdict || "needs_review";
  evolutionHypothesis.textContent = latest.hypothesis_title
    ? `${latest.hypothesis_title}: ${latest.hypothesis_description}`
    : "No evolution hypothesis yet.";

  const activePolicyEntries = Object.entries(latest.active_policy || {})
    .filter(([, value]) => Boolean(value))
    .map(([key, value]) => `${key}=${value}`);
  evolutionPolicy.textContent = activePolicyEntries.length
    ? activePolicyEntries.join(", ")
    : "No promoted policy yet.";

  evolutionMutations.textContent = (latest.mutations || []).length
    ? latest.mutations.map((mutation) => mutation.title).join(" | ")
    : "No mutation proposals yet.";
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
  counterpartLabel.textContent = counterpartNameInput.value.trim() || "Primary User";
  counterpartRole.textContent = counterpartRoleInput.value.trim() || "operator";

  try {
    const [languageResponse, runtimeResponse, selfModelResponse, relationshipResponse, evolutionResponse] = await Promise.all([
      fetch(`/api/v1/language/${encodeURIComponent(agentId)}/state`),
      fetch(`/api/v1/runtime/${encodeURIComponent(agentId)}/state`),
      fetch(`/api/v1/self-models/${encodeURIComponent(agentId)}`),
      fetch(`/api/v1/social-memory/${encodeURIComponent(agentId)}/relationships/user-primary`),
      fetch(`/api/v1/self-evolution/${encodeURIComponent(agentId)}`),
    ]);

    if (languageResponse.status === 404 || runtimeResponse.status === 404 || selfModelResponse.status === 404) {
      statusChip.textContent = "Agent not initialized yet";
      renderMessages([]);
      renderThoughts([]);
      renderGoals([]);
      renderTraces([]);
      return;
    }
    if (!languageResponse.ok || !runtimeResponse.ok || !selfModelResponse.ok) {
      throw new Error("Failed to load language state.");
    }
    const state = await languageResponse.json();
    const runtime = await runtimeResponse.json();
    const selfModel = await selfModelResponse.json();
    const relationship = relationshipResponse.ok ? await relationshipResponse.json() : null;
    const evolutionRuns = evolutionResponse.ok ? await evolutionResponse.json() : [];
    const identityContext = runtime.identity_context || {};

    renderMessages(state.messages || []);
    renderThoughts(state.thoughts || []);
    renderGoals(runtime.active_goals || []);
    renderTraces(runtime.recent_traces || []);
    renderEvolution(evolutionRuns || []);
    loopLabel.textContent = state.background_loop_enabled ? "active" : "idle";
    summaryText.textContent = runtime.summary_text || state.summary?.summary_text || "No compressed memory yet.";
    focusLabel.textContent = runtime.current_focus || selfModel.snapshot.attention.current_focus || "awaiting interaction";
    goalLabel.textContent = runtime.dominant_goal || state.dominant_goal || "not established";
    identityName.textContent = identityContext.self_name || selfModel.chosen_name || selfModel.snapshot.identity.chosen_name || "Astra";
    identityOrigin.textContent = identityContext.self_origin_story || selfModel.snapshot.identity.origin_story || "No origin loaded.";
    identityCommitments.textContent = (identityContext.self_commitments || selfModel.snapshot.identity.core_commitments || []).join(", ") || "No commitments loaded.";
    identityNarrative.textContent = identityContext.self_narrative || selfModel.snapshot.autobiography.long_term_narrative || "No long-term narrative yet.";
    counterpartLabel.textContent = identityContext.counterpart_name || relationship?.counterpart_name || counterpartNameInput.value.trim() || "Primary User";
    counterpartRole.textContent = identityContext.counterpart_role || relationship?.role_in_context || counterpartRoleInput.value.trim() || "operator";
    counterpartRelationship.textContent = identityContext.relationship_type || relationship?.relationship_type || "unknown";
    identityStatus.textContent = identityContext.identity_status || state.summary?.identity_status || "unanchored";
    counterpartObligations.textContent = (identityContext.social_obligations || relationship?.social_obligations || selfModel.snapshot.social.social_obligations || []).join(", ") || "No obligations loaded.";
    statusChip.textContent = "Connected";
    errorText.textContent = "";
    evolutionErrorText.textContent = "";
  } catch (error) {
    statusChip.textContent = "API unavailable";
    renderTraces([]);
    renderEvolution([]);
    errorText.textContent = error instanceof Error ? error.message : "Unknown error.";
  }
}

evolutionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const agentId = agentIdInput.value.trim() || "agent-web-console";
  const objective = evolutionObjectiveInput.value.trim() || "improve self-consistency and adaptive behavior";

  evolutionButton.disabled = true;
  evolutionChip.textContent = "Running...";
  evolutionErrorText.textContent = "";

  try {
    await ensureAgent(agentId);
    const response = await fetch(`/api/v1/self-evolution/${encodeURIComponent(agentId)}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        objective,
        evaluator_notes: "console-triggered evolution loop",
      }),
    });
    if (!response.ok) {
      throw new Error((await response.text()) || "Failed to run evolution loop.");
    }
    await syncState();
  } catch (error) {
    evolutionChip.textContent = "Run failed";
    evolutionErrorText.textContent = error instanceof Error ? error.message : "Unknown error.";
  } finally {
    evolutionButton.disabled = false;
  }
});

composerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const agentId = agentIdInput.value.trim() || "agent-web-console";
  const message = messageInput.value.trim();
  const counterpartName = counterpartNameInput.value.trim() || "Primary User";
  const counterpartRoleValue = counterpartRoleInput.value.trim() || "operator";
  if (!message) {
    return;
  }

  sendButton.disabled = true;
  statusChip.textContent = "Sending...";
  errorText.textContent = "";

  try {
    await ensureAgent(agentId);
    const response = await fetch(`/api/v1/runtime/${encodeURIComponent(agentId)}/step`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_text: message,
        counterpart_id: "user-primary",
        counterpart_name: counterpartName,
        relationship_type: "operator",
        counterpart_role: counterpartRoleValue,
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