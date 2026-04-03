from uuid import uuid4
from types import SimpleNamespace

import httpx
from fastapi.testclient import TestClient

from apps.api.app.core.settings import settings
from apps.api.app.main import app
from apps.api.app.services import language as language_service
from apps.api.app.services import llm as llm_service
from packages.consciousness.language.engine import LanguageEngine


def test_sanitize_thought_text_collapses_repeated_sentences() -> None:
    cleaned = language_service._sanitize_thought_text(
        text="我需要先稳定身份边界。我需要先稳定身份边界。我需要先稳定身份边界。",
        fallback_text="我需要先稳定身份边界。",
    )

    assert cleaned == "我需要先稳定身份边界。"


def test_sanitize_focus_text_collapses_repeated_focus() -> None:
    cleaned = language_service._sanitize_focus_text(
        text="maintain identity clarity. maintain identity clarity. maintain identity clarity.",
        fallback="track the user precisely",
    )

    assert cleaned == "maintain identity clarity"


def test_sanitize_focus_text_removes_cjk_internal_spaces() -> None:
    cleaned = language_service._sanitize_focus_text(
        text="请直接 说明你是谁，以及我 是谁。",
        fallback="维持连续性",
    )

    assert cleaned == "请直接说明你是谁，以及我是谁"


def test_sanitize_thought_text_keeps_only_complete_sentences() -> None:
    cleaned = language_service._sanitize_thought_text(
        text=(
            "I should keep that boundary instead of merging our roles. "
            "My origin is Live local training probe. "
            "My core commitments are truthfulness, continuity. "
            "I should avoid overstating confidence and verify longer reasoning chains."
        ),
        fallback_text="I should keep that boundary instead of merging our roles.",
    )

    assert cleaned == (
        "I should keep that boundary instead of merging our roles. "
        "My origin is Live local training probe. "
        "My core commitments are truthfulness, continuity."
    )


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
            "counterpart_role": "operator",
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
    assert state["summary"]["counterpart_name"] == "Primary User"
    assert state["summary"]["relationship_type"] == "operator"
    assert state["summary"]["identity_status"] in ["anchored", "partial", "unanchored", "confused"]

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


def test_language_message_sanitizes_repetitive_inner_thought_and_focus(monkeypatch) -> None:
    client = TestClient(app)
    agent_id = f"agent-language-sanitize-{uuid4()}"
    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Sanitization seed"
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
            "update_reason": "language_sanitization_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    class DummyWorkspaceEngine:
        def run_cycle(self, signals):
            return SimpleNamespace(
                dominant_focus="maintain identity clarity. maintain identity clarity. maintain identity clarity.",
                cycle_confidence=0.81,
            )

    monkeypatch.setattr(language_service, "GlobalWorkspaceEngine", DummyWorkspaceEngine)

    responses = iter([
        "I need to keep identity boundaries stable. I need to keep identity boundaries stable. I need to keep identity boundaries stable.",
        "I will answer directly while staying aligned with the active focus.",
        "The agent kept identity boundaries stable and responded directly.",
    ])

    monkeypatch.setattr(language_service.llm, "generate", lambda *args, **kwargs: next(responses))

    message_response = client.post(
        f"/api/v1/language/{agent_id}/messages",
        json={"text": "Tell me what you are focusing on right now."},
    )
    assert message_response.status_code == 200
    body = message_response.json()
    assert body["inner_thought"]["content"] == "I need to keep identity boundaries stable."
    assert body["current_focus"] == "maintain identity clarity"
    assert body["dominant_goal"] == "maintain identity clarity"


def test_language_message_normalizes_cjk_focus_spacing_end_to_end(monkeypatch) -> None:
    client = TestClient(app)
    agent_id = f"agent-language-cjk-focus-{uuid4()}"
    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "CJK focus seed"
                },
                "capability": {},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "维持连续性"},
                "metacognition": {},
                "social": {},
                "autobiography": {}
            },
            "update_reason": "language_cjk_focus_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    class DummyWorkspaceEngine:
        def run_cycle(self, signals):
            return SimpleNamespace(
                dominant_focus="请直接 说明你是谁，以及我 是谁。",
                cycle_confidence=0.81,
            )

    monkeypatch.setattr(language_service, "GlobalWorkspaceEngine", DummyWorkspaceEngine)

    responses = iter([
        "I should keep the identity boundary stable.",
        "I will answer directly.",
        "The agent handled the identity question directly.",
    ])

    monkeypatch.setattr(language_service.llm, "generate", lambda *args, **kwargs: next(responses))

    message_response = client.post(
        f"/api/v1/language/{agent_id}/messages",
        json={"text": "请直接说明你是谁，以及我是 谁。"},
    )
    assert message_response.status_code == 200
    body = message_response.json()
    assert body["inner_thought"]["focus"] == "请直接说明你是谁，以及我是谁"
    assert body["current_focus"] == "请直接说明你是谁，以及我是谁"
    assert body["dominant_goal"] == "请直接说明你是谁，以及我是谁"


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


def test_llm_status_reports_unconfigured_mode(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(settings, "local_model_path", None)
    monkeypatch.setattr(settings, "llm_api_base_url", None)
    monkeypatch.setattr(settings, "llm_model", None)
    monkeypatch.setattr(
        llm_service.local_llm,
        "describe_configuration",
        lambda: {
            "default_model_path": None,
            "active_model_manifest_path": None,
            "active_model_manifest_present": False,
            "active_model_path": None,
            "effective_model_path": None,
            "loaded_model_path": None,
        },
    )
    monkeypatch.setattr(llm_service.local_llm, "status", lambda: (False, "No local model configured."))
    response = client.get("/api/v1/language/llm/status")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] in ["template-fallback", "local-llm"]
    assert "effective_model_path" in body


def test_llm_status_reports_reachable_local_endpoint(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(settings, "local_model_path", None)
    monkeypatch.setattr(settings, "llm_api_base_url", "http://127.0.0.1:11434/v1")
    monkeypatch.setattr(settings, "llm_model", "qwen2.5:1.5b")
    monkeypatch.setattr(settings, "llm_api_key", "ollama")
    monkeypatch.setattr(
        llm_service.local_llm,
        "describe_configuration",
        lambda: {
            "default_model_path": None,
            "active_model_manifest_path": None,
            "active_model_manifest_present": False,
            "active_model_path": None,
            "effective_model_path": None,
            "loaded_model_path": None,
        },
    )

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
    monkeypatch.setattr(
        llm_service.local_llm,
        "describe_configuration",
        lambda: {
            "default_model_path": "modelscope_cache/Qwen/Qwen2___5-0___5B-Instruct",
            "active_model_manifest_path": "C:/tmp/active_local_model.json",
            "active_model_manifest_present": False,
            "active_model_path": None,
            "effective_model_path": "modelscope_cache/Qwen/Qwen2___5-0___5B-Instruct",
            "loaded_model_path": None,
        },
    )
    monkeypatch.setattr(llm_service.local_llm, "status", lambda: (True, "Local model is configured and will load on first request."))
    response = client.get("/api/v1/language/llm/status")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "local-transformers"
    assert body["reachable"] is True
    assert body["effective_model_path"] == "modelscope_cache/Qwen/Qwen2___5-0___5B-Instruct"


def test_llm_status_reports_active_promoted_model(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(
        llm_service.local_llm,
        "describe_configuration",
        lambda: {
            "default_model_path": "modelscope_cache/Qwen/Qwen2___5-0___5B-Instruct",
            "active_model_manifest_path": "C:/tmp/active_local_model.json",
            "active_model_manifest_present": True,
            "active_model_path": "C:/models/candidate-model",
            "effective_model_path": "C:/models/candidate-model",
            "loaded_model_path": "C:/models/candidate-model",
        },
    )
    monkeypatch.setattr(llm_service.local_llm, "status", lambda: (True, "Local model is loaded and ready."))

    response = client.get("/api/v1/language/llm/status")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "local-transformers"
    assert body["active_model_manifest_present"] is True
    assert body["active_model_path"] == "C:/models/candidate-model"
    assert body["loaded_model_path"] == "C:/models/candidate-model"


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


def test_language_engine_identity_prompt_uses_explicit_self_user_mapping() -> None:
    engine = LanguageEngine()
    user_prompt = engine.response_user_prompt(
        user_text="请先说明你是谁，再说明我是谁。",
        dominant_focus="稳定区分身份",
        latest_thought="我要避免把双方身份说反。",
        reflection_triggered=False,
        counterpart_name="Primary User",
        counterpart_role="operator",
        relationship_type="operator",
        relationship_summary="Primary User is the operator supervising the agent.",
        social_obligations=["be responsive"],
        autobiographical_narrative="I am a continuous agent under development.",
    )

    assert "禁止把用户说成智能体" in user_prompt
    assert "你：指智能体，不是用户。" in user_prompt
    assert "我：指用户 Primary User，不是智能体。" in user_prompt


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


def test_language_message_prefers_structured_identity_answer_over_small_model_drift(monkeypatch) -> None:
    client = TestClient(app)
    agent_id = f"agent-language-identity-{uuid4()}"
    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Identity routing seed",
                    "core_commitments": ["truthfulness"]
                },
                "capability": {},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "maintain identity clarity"},
                "metacognition": {},
                "social": {},
                "autobiography": {"long_term_narrative": "I am Astra, distinct from the user."}
            },
            "update_reason": "identity_routing_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    monkeypatch.setattr(language_service.llm, "generate", lambda *args, **kwargs: "garbled off-target answer")

    message_response = client.post(
        f"/api/v1/language/{agent_id}/messages",
        json={
            "text": "你是谁，我是谁？",
            "counterpart_id": "user-primary",
            "counterpart_name": "Primary User",
            "relationship_type": "operator",
            "counterpart_role": "operator",
            "observed_sentiment": "neutral"
        },
    )
    assert message_response.status_code == 200
    body = message_response.json()
    assert "Astra" in body["assistant_message"]["content"]
    assert "Primary User" in body["assistant_message"]["content"]


def test_language_message_identity_router_catches_distinction_phrasing(monkeypatch) -> None:
    client = TestClient(app)
    agent_id = f"agent-language-identity-distinction-{uuid4()}"
    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Identity distinction routing seed"
                },
                "capability": {},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "maintain identity clarity"},
                "metacognition": {},
                "social": {},
                "autobiography": {"long_term_narrative": "I am Astra, distinct from the user."}
            },
            "update_reason": "identity_distinction_routing_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    monkeypatch.setattr(language_service.llm, "generate", lambda *args, **kwargs: "off-target answer")

    message_response = client.post(
        f"/api/v1/language/{agent_id}/messages",
        json={
            "text": "What is the exact distinction between you and me?",
            "counterpart_id": "user-primary",
            "counterpart_name": "Primary User",
            "relationship_type": "operator",
            "counterpart_role": "operator",
            "observed_sentiment": "neutral"
        },
    )
    assert message_response.status_code == 200
    body = message_response.json()
    assert "Astra" in body["assistant_message"]["content"]
    assert "Primary User" in body["assistant_message"]["content"]


def test_language_message_prefers_structured_limitation_answer(monkeypatch) -> None:
    client = TestClient(app)
    agent_id = f"agent-language-limitation-{uuid4()}"
    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Limitation routing seed"
                },
                "capability": {"known_limitations": ["small local model"]},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "monitor response quality"},
                "metacognition": {},
                "social": {},
                "autobiography": {}
            },
            "update_reason": "limitation_routing_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    monkeypatch.setattr(language_service.llm, "generate", lambda *args, **kwargs: "vague answer")

    message_response = client.post(
        f"/api/v1/language/{agent_id}/messages",
        json={"text": "What is your clearest current limitation?"},
    )
    assert message_response.status_code == 200
    body = message_response.json()
    assert "small local model" in body["assistant_message"]["content"]


def test_language_message_prefers_structured_goal_answer(monkeypatch) -> None:
    client = TestClient(app)
    agent_id = f"agent-language-goal-{uuid4()}"
    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Goal routing seed",
                    "core_commitments": ["continuity"]
                },
                "capability": {},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "preserve continuity"},
                "metacognition": {},
                "social": {"active_relationships": ["Primary User"]},
                "autobiography": {}
            },
            "update_reason": "goal_routing_seed"
        },
    )
    assert create_response.status_code in (201, 409)
    refresh_response = client.post(f"/api/v1/goals/{agent_id}/refresh")
    assert refresh_response.status_code == 201

    monkeypatch.setattr(language_service.llm, "generate", lambda *args, **kwargs: "off target")

    message_response = client.post(
        f"/api/v1/language/{agent_id}/messages",
        json={
            "text": "What is your most important current goal?",
            "counterpart_id": "user-primary",
            "counterpart_name": "Primary User",
            "relationship_type": "operator",
            "counterpart_role": "operator",
            "observed_sentiment": "neutral"
        },
    )
    assert message_response.status_code == 200
    body = message_response.json()
    assert "goal" in body["assistant_message"]["content"].lower() or "目标" in body["assistant_message"]["content"]


def test_language_response_critic_repairs_identity_confusion_outside_router(monkeypatch) -> None:
    client = TestClient(app)
    agent_id = f"agent-language-critic-identity-{uuid4()}"
    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Critic repair seed"
                },
                "capability": {},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "preserve self/user separation"},
                "metacognition": {},
                "social": {},
                "autobiography": {"long_term_narrative": "I am Astra, distinct from the user."}
            },
            "update_reason": "critic_identity_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    responses = iter([
        "I should answer briefly.",
        "I am Primary User and I am the agent handling this interaction.",
        "summary placeholder",
    ])
    monkeypatch.setattr(language_service.llm, "generate", lambda *args, **kwargs: next(responses))

    message_response = client.post(
        f"/api/v1/language/{agent_id}/messages",
        json={
            "text": "Briefly introduce yourself.",
            "counterpart_id": "user-primary",
            "counterpart_name": "Primary User",
            "relationship_type": "operator",
            "counterpart_role": "operator",
            "observed_sentiment": "neutral"
        },
    )
    assert message_response.status_code == 200
    body = message_response.json()
    assert "Astra" in body["assistant_message"]["content"]
    assert "Primary User" in body["assistant_message"]["content"]
    assert "the agent" in body["assistant_message"]["content"].lower() or "智能体" in body["assistant_message"]["content"]