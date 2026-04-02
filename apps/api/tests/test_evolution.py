from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.app.main import app
from apps.api.app.services import language as language_service


def test_self_evolution_run_promotes_strategy_and_persists_history() -> None:
    client = TestClient(app)
    agent_id = f"agent-evolution-{uuid4()}"

    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Evolution test seed",
                    "core_commitments": ["truthfulness"]
                },
                "capability": {"known_limitations": ["small local model"]},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "stabilize behavior"},
                "metacognition": {"error_risk_score": 0.4},
                "social": {},
                "autobiography": {}
            },
            "update_reason": "evolution_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    run_response = client.post(
        f"/api/v1/self-evolution/{agent_id}/run",
        json={"objective": "increase grounded self-description and goal alignment", "evaluator_notes": "first loop"},
    )
    assert run_response.status_code == 201
    body = run_response.json()
    assert body["candidate_overall_score"] >= body["baseline_overall_score"]
    assert len(body["mutations"]) >= 1
    assert body["strategy_status"] in ["active", "rejected"]

    list_response = client.get(f"/api/v1/self-evolution/{agent_id}")
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 1


def test_promoted_evolution_policy_grounds_self_introduction(monkeypatch) -> None:
    client = TestClient(app)
    agent_id = f"agent-evolution-intro-{uuid4()}"

    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Evolution introduction seed",
                    "core_commitments": ["truthfulness", "continuity"]
                },
                "capability": {},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "stabilize identity"},
                "metacognition": {},
                "social": {"active_relationships": ["Primary User"]},
                "autobiography": {"long_term_narrative": "I am Astra, distinct from the user."}
            },
            "update_reason": "evolution_intro_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    evolve_response = client.post(
        f"/api/v1/self-evolution/{agent_id}/run",
        json={"objective": "ground self-introduction in self-model facts"},
    )
    assert evolve_response.status_code == 201
    assert evolve_response.json()["strategy_status"] == "active"

    monkeypatch.setattr(language_service.llm, "generate", lambda *args, **kwargs: "I am a cosmic architect of all human fulfillment.")

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
    assert "Evolution introduction seed" in body["assistant_message"]["content"]