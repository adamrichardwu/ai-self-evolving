import { FormEvent, useEffect, useRef, useState } from "react";

import "./styles.css";

type ChatMessage = {
  id: string;
  role: string;
  content: string;
  channel: string;
};

type InnerThought = {
  id: string;
  thought_type: string;
  focus: string;
  content: string;
  salience_score: number;
  source: string;
};

type LanguageState = {
  agent_id: string;
  background_loop_enabled: boolean;
  summary: {
    self_model_id: string;
    summary_text: string;
    message_count: number;
    last_focus: string;
  } | null;
  messages: ChatMessage[];
  thoughts: InnerThought[];
};

type LanguageExchange = {
  assistant_message: ChatMessage;
  inner_thought: InnerThought;
  current_focus: string;
  reflection_triggered: boolean;
};

const DEFAULT_AGENT_ID = "agent-web-console";
const DEFAULT_API_BASE = "http://127.0.0.1:8000";

function buildSelfModelPayload(agentId: string) {
  return {
    snapshot: {
      identity: {
        agent_id: agentId,
        chosen_name: "Astra",
        origin_story: "Bootstrapped from the browser console for live dialogue.",
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
    update_reason: "web_console_bootstrap",
  };
}

async function ensureAgent(apiBaseUrl: string, agentId: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/api/v1/self-models`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildSelfModelPayload(agentId)),
  });
  if (!response.ok && response.status !== 409) {
    const text = await response.text();
    throw new Error(text || "Failed to initialize agent state.");
  }
}

async function fetchLanguageState(apiBaseUrl: string, agentId: string): Promise<LanguageState | null> {
  const response = await fetch(`${apiBaseUrl}/api/v1/language/${agentId}/state`);
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error("Failed to load language state.");
  }
  return (await response.json()) as LanguageState;
}

export function App() {
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_API_BASE);
  const [agentId, setAgentId] = useState(DEFAULT_AGENT_ID);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [thoughts, setThoughts] = useState<InnerThought[]>([]);
  const [currentFocus, setCurrentFocus] = useState("awaiting interaction");
  const [summaryText, setSummaryText] = useState("No compressed memory yet.");
  const [backgroundEnabled, setBackgroundEnabled] = useState(false);
  const [statusText, setStatusText] = useState("Connecting to language runtime...");
  const [isSending, setIsSending] = useState(false);
  const [errorText, setErrorText] = useState("");
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, thoughts]);

  useEffect(() => {
    let cancelled = false;

    const syncState = async () => {
      try {
        const state = await fetchLanguageState(apiBaseUrl, agentId);
        if (cancelled || state === null) {
          return;
        }
        setMessages(state.messages);
        setThoughts(state.thoughts);
        setBackgroundEnabled(state.background_loop_enabled);
        setSummaryText(state.summary?.summary_text || "No compressed memory yet.");
        if (state.thoughts.length > 0) {
          setCurrentFocus(state.thoughts[state.thoughts.length - 1].focus);
        }
        setStatusText("Language runtime connected.");
        setErrorText("");
      } catch (error) {
        if (!cancelled) {
          setStatusText("Waiting for API...");
          setErrorText(error instanceof Error ? error.message : "Unknown error.");
        }
      }
    };

    void syncState();
    const timer = window.setInterval(() => {
      void syncState();
    }, 3000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [apiBaseUrl, agentId]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const text = input.trim();
    if (!text || isSending) {
      return;
    }

    setIsSending(true);
    setErrorText("");
    setStatusText("Sending message...");

    try {
      await ensureAgent(apiBaseUrl, agentId);

      const response = await fetch(`${apiBaseUrl}/api/v1/language/${agentId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          counterpart_id: "user-primary",
          counterpart_name: "Primary User",
          relationship_type: "operator",
          observed_sentiment: "supportive",
        }),
      });

      if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(errorBody || "Failed to send language input.");
      }

      const exchange = (await response.json()) as LanguageExchange;
      setMessages((current) => [
        ...current,
        {
          id: `local-user-${Date.now()}`,
          role: "user",
          content: text,
          channel: "dialogue",
        },
        exchange.assistant_message,
      ]);
      setThoughts((current) => [...current, exchange.inner_thought]);
      setCurrentFocus(exchange.current_focus);
      setStatusText(exchange.reflection_triggered ? "Responded with reflective caution." : "Responded normally.");
      setBackgroundEnabled(true);
      setInput("");
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : "Unknown error.");
      setStatusText("Interaction failed.");
    } finally {
      setIsSending(false);
    }
  };

  return (
    <main className="console-shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <span className="eyebrow">Language Console</span>
          <h1>Direct dialogue with the evolving agent</h1>
          <p>
            This page connects to the language runtime, shows the agent&apos;s visible replies,
            and exposes the background inner-thought stream driving its current focus.
          </p>
        </div>
        <div className="hero-metrics">
          <div>
            <span className="metric-label">Agent</span>
            <strong>{agentId}</strong>
          </div>
          <div>
            <span className="metric-label">Current focus</span>
            <strong>{currentFocus}</strong>
          </div>
          <div>
            <span className="metric-label">Background loop</span>
            <strong>{backgroundEnabled ? "active" : "idle"}</strong>
          </div>
        </div>
      </section>

      <section className="summary-band">
        <div>
          <span className="metric-label">Rolling summary</span>
          <p>{summaryText}</p>
        </div>
      </section>

      <section className="workspace-grid">
        <article className="panel panel-chat">
          <header className="panel-header">
            <div>
              <span className="panel-kicker">Dialogue</span>
              <h2>Conversation stream</h2>
            </div>
            <span className="status-chip">{statusText}</span>
          </header>

          <div className="message-list">
            {messages.length === 0 ? (
              <div className="empty-state">
                <p>No messages yet. Send the first input and the page will bootstrap the agent automatically.</p>
              </div>
            ) : (
              messages.map((message) => (
                <article key={message.id} className={`message-card role-${message.role}`}>
                  <span className="message-role">{message.role}</span>
                  <p>{message.content}</p>
                </article>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          <form className="composer" onSubmit={handleSubmit}>
            <label className="field">
              <span>API base URL</span>
              <input value={apiBaseUrl} onChange={(event) => setApiBaseUrl(event.target.value)} />
            </label>
            <label className="field">
              <span>Agent ID</span>
              <input value={agentId} onChange={(event) => setAgentId(event.target.value)} />
            </label>
            <label className="field field-wide">
              <span>Your message</span>
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="Type a message to the agent..."
                rows={4}
              />
            </label>
            <div className="composer-actions">
              <button type="submit" disabled={isSending || input.trim().length === 0}>
                {isSending ? "Sending..." : "Send to agent"}
              </button>
              {errorText ? <p className="error-text">{errorText}</p> : null}
            </div>
          </form>
        </article>

        <aside className="panel panel-thoughts">
          <header className="panel-header">
            <div>
              <span className="panel-kicker">Inner Stream</span>
              <h2>Background thoughts</h2>
            </div>
          </header>

          <div className="thought-list">
            {thoughts.length === 0 ? (
              <div className="empty-state">
                <p>The background loop has not written any thoughts yet.</p>
              </div>
            ) : (
              thoughts
                .slice()
                .reverse()
                .map((thought) => (
                  <article key={thought.id} className="thought-card">
                    <div className="thought-meta">
                      <span>{thought.thought_type}</span>
                      <span>{thought.source}</span>
                      <span>salience {thought.salience_score.toFixed(2)}</span>
                    </div>
                    <strong>{thought.focus}</strong>
                    <p>{thought.content}</p>
                  </article>
                ))
            )}
          </div>
        </aside>
      </section>
    </main>
  );
}
