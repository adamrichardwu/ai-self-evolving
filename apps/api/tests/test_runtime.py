from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.app.main import app


def test_runtime_step_uses_language_reply_when_user_text_exists() -> None:
    client = TestClient(app)
    agent_id = f"agent-runtime-msg-{uuid4()}"
    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Runtime message seed",
                    "core_commitments": ["truthfulness"]
                },
                "capability": {"known_limitations": ["cannot guarantee certainty"]},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "maintain coherent runtime behavior"},
                "metacognition": {},
                "social": {"social_obligations": ["be responsive"]},
                "autobiography": {}
            },
            "update_reason": "runtime_message_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    step_response = client.post(
        f"/api/v1/runtime/{agent_id}/step",
        json={
            "user_text": "Tell me your most important current goal.",
            "counterpart_name": "Primary User",
            "relationship_type": "operator",
            "counterpart_role": "operator",
        },
    )
    assert step_response.status_code == 200
    body = step_response.json()
    assert body["action_taken"] == "language_reply"
    assert body["assistant_text"] != ""
    assert body["dominant_goal"] != ""
    assert len(body["active_goals"]) >= 1
    assert body["thought"] is not None
    assert body["identity_context"]["self_name"] == "Astra"
    assert body["identity_context"]["counterpart_name"] == "Primary User"
    assert body["identity_context"]["identity_status"] in ["anchored", "partial", "unanchored", "confused"]
    assert body["trace"] is not None
    assert body["trace"]["action_taken"] == "language_reply"


def test_runtime_state_and_background_step_expose_runtime_context() -> None:
    client = TestClient(app)
    agent_id = f"agent-runtime-bg-{uuid4()}"
    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Runtime background seed",
                    "core_commitments": ["continuity"]
                },
                "capability": {},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "preserve background continuity"},
                "metacognition": {},
                "social": {},
                "autobiography": {}
            },
            "update_reason": "runtime_background_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    step_response = client.post(f"/api/v1/runtime/{agent_id}/step", json={})
    assert step_response.status_code == 200
    body = step_response.json()
    assert body["action_taken"] == "background_thought"
    assert body["thought"] is not None
    assert body["dominant_goal"] != ""

    state_response = client.get(f"/api/v1/runtime/{agent_id}/state")
    assert state_response.status_code == 200
    state = state_response.json()
    assert state["chosen_name"] == "Astra"
    assert state["current_focus"] != ""
    assert state["dominant_goal"] != ""
    assert len(state["active_goals"]) >= 1
    assert state["latest_thought"] is not None
    assert state["identity_context"]["self_name"] == "Astra"
    assert state["identity_context"]["identity_status"] in ["anchored", "partial", "unanchored", "confused"]
    assert len(state["recent_traces"]) >= 1