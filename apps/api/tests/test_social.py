from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.app.main import app


def test_upsert_and_list_social_relationships() -> None:
    client = TestClient(app)
    agent_id = f"agent-social-{uuid4()}"
    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Social memory seed"
                },
                "capability": {},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {},
                "metacognition": {},
                "social": {},
                "autobiography": {}
            },
            "update_reason": "social_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    relationship_response = client.post(
        f"/api/v1/social-memory/{agent_id}/relationships",
        json={
            "context": {
                "counterpart_id": "user-primary",
                "counterpart_name": "Primary User",
                "relationship_type": "user",
                "interaction_summary": "Asked the agent to preserve continuity while learning.",
                "observed_sentiment": "positive",
                "role_in_context": "collaborator",
                "social_obligations": ["be responsive", "preserve continuity"]
            }
        },
    )
    assert relationship_response.status_code == 201
    body = relationship_response.json()
    assert body["counterpart_id"] == "user-primary"
    assert body["interaction_count"] >= 1
    assert body["trust_score"] > 0.5

    list_response = client.get(f"/api/v1/social-memory/{agent_id}/relationships")
    assert list_response.status_code == 200
    relationships = list_response.json()
    assert len(relationships) >= 1

    self_model_response = client.get(f"/api/v1/self-models/{agent_id}")
    assert self_model_response.status_code == 200
    social_state = self_model_response.json()["snapshot"]["social"]
    assert "Primary User" in social_state["active_relationships"]
    assert social_state["trust_map"]["user-primary"] > 0.5


def test_execute_task_updates_social_memory() -> None:
    client = TestClient(app)
    agent_id = f"agent-social-task-{uuid4()}"
    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Social task integration seed"
                },
                "capability": {},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {},
                "metacognition": {},
                "social": {},
                "autobiography": {}
            },
            "update_reason": "social_task_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    execute_response = client.post(
        "/api/v1/tasks/execute",
        json={
            "task_type": "dialogue",
            "agent_id": agent_id,
            "input": {"prompt": "Coordinate with the user on the next evolution step."},
            "strategy_version": "strategy-v1",
            "model_profile": "main-online",
            "social_context": {
                "counterpart_id": "user-primary",
                "counterpart_name": "Primary User",
                "relationship_type": "operator",
                "observed_sentiment": "supportive",
                "role_in_context": "partner",
                "social_obligations": ["share progress frequently"]
            }
        },
    )
    assert execute_response.status_code == 200

    relationship_response = client.get(
        f"/api/v1/social-memory/{agent_id}/relationships/user-primary"
    )
    assert relationship_response.status_code == 200
    relationship = relationship_response.json()
    assert relationship["interaction_count"] >= 1
    assert relationship["role_in_context"] in ["partner", "collaborator"]

    self_model_response = client.get(f"/api/v1/self-models/{agent_id}")
    assert self_model_response.status_code == 200
    social_state = self_model_response.json()["snapshot"]["social"]
    assert social_state["trust_map"]["user-primary"] > 0.5
    assert "share progress frequently" in social_state["social_obligations"]