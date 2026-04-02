from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from apps.api.app.core.settings import settings
from apps.api.app.main import app
from apps.api.app.services import language as language_service
from apps.api.app.services import llm as llm_service
from packages.consciousness.language.engine import LanguageEngine


def test_manual_language_thought_cycle_creates_inner_thought() -> None:
    client = TestClient(app)
    agent_id = f"agent-language-{uuid4()}"
    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Language module seed"
                },
                "capability": {},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "maintain continuity"},
                "metacognition": {},
                "social": {},
                "autobiography": {}
            },
            "update_reason": "language_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    thought_response = client.post(f"/api/v1/language/{agent_id}/think")
    assert thought_response.status_code == 201
    body = thought_response.json()
    assert body["thought_type"] == "manual_cycle"
    assert body["content"] != ""

    state_response = client.get(f"/api/v1/language/{agent_id}/state")
    assert state_response.status_code == 200
    state = state_response.json()
    assert len(state["thoughts"]) >= 1


def test_language_message_generates_reaction_and_persists_dialogue() -> None:
    client = TestClient(app)
    agent_id = f"agent-language-msg-{uuid4()}"
    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Language reaction seed",
                    "core_commitments": ["truthfulness"]
                },
                "capability": {"known_limitations": ["cannot guarantee certainty"]},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "protect continuity while interacting"},
                "metacognition": {},
                "social": {},
                "autobiography": {}
            },
            "update_reason": "language_message_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    message_response = client.post(
        f"/api/v1/language/{agent_id}/messages",
        json={
            "text": "Please think about my request and tell me what you are focusing on.",
            "counterpart_id": "user-primary",
            "counterpart_name": "Primary User",
            "relationship_type": "operator",
            "observed_sentiment": "supportive"
        },
    )
    assert message_response.status_code == 200
    body = message_response.json()
    assert body["assistant_message"]["role"] == "assistant"
    assert body["assistant_message"]["content"] != ""
    assert body["inner_thought"]["content"] != ""
    assert body["current_focus"] != ""
    assert body["dominant_goal"] != ""
    assert len(body["active_goals"]) >= 1

    state_response = client.get(f"/api/v1/language/{agent_id}/state")
    assert state_response.status_code == 200
    state = state_response.json()
    assert len(state["messages"]) >= 2
    assert len(state["thoughts"]) >= 1
    assert state["summary"] is not None
    assert state["summary"]["summary_text"] != ""
    assert state["dominant_goal"] != ""
    assert len(state["active_goals"]) >= 1

    self_model_response = client.get(f"/api/v1/self-models/{agent_id}")
    assert self_model_response.status_code == 200
    model = self_model_response.json()
    assert model["snapshot"]["attention"]["current_focus"] != ""
    assert model["snapshot"]["attention"]["dominant_goal"] != ""
    assert model["snapshot"]["goals"]["active_task_goals"] != []


def test_language_message_uses_llm_when_configured(monkeypatch) -> None:
    client = TestClient(app)
    agent_id = f"agent-language-llm-{uuid4()}"
    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Language LLM seed"
                },
                "capability": {},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "track the user precisely"},
                "metacognition": {},
                "social": {},
                "autobiography": {}
            },
            "update_reason": "language_llm_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    monkeypatch.setattr(settings, "llm_api_base_url", "http://llm.local/v1")
    monkeypatch.setattr(settings, "llm_model", "test-model")
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "local_model_path", None)

    responses = iter([
        "I am internally preparing a precise answer for the user.",
        "I will answer the user directly while staying aligned with my current focus.",
        "The user asked for visibility into the agent's current thinking and the agent responded directly.",
    ])

    def fake_generate(system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        return next(responses)

    monkeypatch.setattr(language_service.llm, "generate", fake_generate)

    message_response = client.post(
        f"/api/v1/language/{agent_id}/messages",
        json={"text": "Explain what you are currently thinking about."},
    )
    assert message_response.status_code == 200
    body = message_response.json()
    assert body["inner_thought"]["content"] == "I am internally preparing a precise answer for the user."
    assert body["assistant_message"]["content"] == "I will answer the user directly while staying aligned with my current focus."


def test_language_state_exposes_rolling_summary() -> None:
    client = TestClient(app)
    agent_id = f"agent-language-summary-{uuid4()}"
    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Language summary seed"
                },
                "capability": {},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "track the conversation"},
                "metacognition": {},
                "social": {},
                "autobiography": {}
            },
            "update_reason": "language_summary_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    first = client.post(
        f"/api/v1/language/{agent_id}/messages",
        json={"text": "Remember that I want a stable long-term interaction."},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/language/{agent_id}/messages",
        json={"text": "Also keep your responses aligned with your current focus."},
    )
    assert second.status_code == 200

    state_response = client.get(f"/api/v1/language/{agent_id}/state")
    assert state_response.status_code == 200
    state = state_response.json()
    assert state["summary"] is not None
    assert state["summary"]["message_count"] >= 4
    assert state["summary"]["summary_text"] != ""
    assert state["dominant_goal"] != ""
    assert len(state["active_goals"]) >= 1


def test_llm_status_reports_unconfigured_mode() -> None:
    client = TestClient(app)
    settings.local_model_path = None
    settings.llm_api_base_url = None
    settings.llm_model = None
    response = client.get("/api/v1/language/llm/status")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] in ["template-fallback", "local-llm"]


def test_llm_status_reports_reachable_local_endpoint(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(settings, "local_model_path", None)
    monkeypatch.setattr(settings, "llm_api_base_url", "http://127.0.0.1:11434/v1")
    monkeypatch.setattr(settings, "llm_model", "qwen2.5:1.5b")
    monkeypatch.setattr(settings, "llm_api_key", "ollama")

    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

    class DummyClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def get(self, url: str, headers: dict[str, str]) -> DummyResponse:
            return DummyResponse()

    monkeypatch.setattr(httpx, "Client", DummyClient)
    response = client.get("/api/v1/language/llm/status")
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert body["reachable"] is True
    assert body["mode"] == "local-llm"


def test_llm_status_prefers_local_transformers_model(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(settings, "local_model_path", "modelscope_cache/Qwen/Qwen2___5-0___5B-Instruct")
    monkeypatch.setattr(llm_service.local_llm, "status", lambda: (True, "Local model is configured and will load on first request."))
    response = client.get("/api/v1/language/llm/status")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "local-transformers"
    assert body["reachable"] is True


def test_language_engine_response_prompt_prefers_chinese_for_chinese_input() -> None:
    engine = LanguageEngine()
    system_prompt = engine.response_system_prompt(
        "Astra",
        origin_story="Bootstrapped from a continuity-focused prototype.",
        core_commitments=["truthfulness", "continuity"],
        reflection_triggered=False,
    )
    user_prompt = engine.response_user_prompt(
        user_text="请直接告诉我你现在最关注什么。",
        dominant_focus="维持连续交互",
        latest_thought="我应该先给出直接答案。",
        reflection_triggered=False,
        counterpart_name="Primary User",
        counterpart_role="operator",
        relationship_type="operator",
        relationship_summary="Primary User is the main operator and expects continuity.",
        social_obligations=["be responsive"],
        autobiographical_narrative="I am building a stable long-term interaction style.",
    )

    assert "如果用户使用中文，则使用简体中文" in system_prompt
    assert "清楚区分你自己和当前用户" in system_prompt
    assert "优先直接解决问题" in user_prompt
    assert "用户身份：Primary User" in user_prompt


def test_language_engine_background_prompt_anchors_self_and_user_identity() -> None:
    engine = LanguageEngine()
    system_prompt = engine.background_system_prompt(
        chosen_name="Astra",
        origin_story="Started as a self-evolving local agent prototype.",
        core_commitments=["truthfulness"],
    )
    user_prompt = engine.background_user_prompt(
        chosen_name="Astra",
        dominant_focus="maintain continuity",
        latest_user_message="Please remember who I am.",
        obligations=["be responsive"],
        counterpart_name="Primary User",
        counterpart_role="operator",
        relationship_type="operator",
        relationship_summary="Primary User supervises the system and values continuity.",
    )

    assert "起源背景" in system_prompt
    assert "核心承诺" in system_prompt
    assert "对方身份：Primary User" in user_prompt
    assert "关系摘要：Primary User supervises the system and values continuity." in user_prompt