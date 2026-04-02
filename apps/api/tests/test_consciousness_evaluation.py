from fastapi.testclient import TestClient

from apps.api.app.main import app


def test_create_consciousness_evaluation_from_self_model() -> None:
    client = TestClient(app)
    agent_id = "agent-eval-001"

    create_model_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Consciousness evaluation test",
                    "persistent_traits": ["reflective", "curious"],
                    "core_commitments": ["truthfulness", "continuity"]
                },
                "capability": {},
                "goals": {
                    "learning_goals": ["improve self-modeling"],
                    "active_task_goals": ["complete evaluation"]
                },
                "values": {},
                "affect": {},
                "attention": {},
                "metacognition": {"contradiction_score": 0.2},
                "social": {"active_relationships": ["user"]},
                "autobiography": {
                    "recovered_failures": ["resolved identity conflict"],
                    "long_term_narrative": "Growing toward stable long-term identity"
                }
            },
            "update_reason": "evaluation_seed"
        },
    )
    assert create_model_response.status_code in (201, 409)

    create_eval_response = client.post(
        "/api/v1/consciousness-evaluations",
        json={"agent_id": agent_id, "evaluation_type": "baseline", "evaluator_notes": "initial pass"},
    )
    assert create_eval_response.status_code == 201
    body = create_eval_response.json()
    assert body["evaluation_type"] == "baseline"
    assert body["overall_score"] >= 0.0

    list_eval_response = client.get(f"/api/v1/consciousness-evaluations/{agent_id}")
    assert list_eval_response.status_code == 200
    assert len(list_eval_response.json()) >= 1
