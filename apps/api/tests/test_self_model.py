from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.app.main import app


def test_create_and_update_self_model() -> None:
    client = TestClient(app)
    agent_id = f"agent-test-{uuid4()}"
    create_payload = {
        "snapshot": {
            "identity": {
                "agent_id": agent_id,
                "chosen_name": "Astra",
                "origin_story": "Bootstrapped from the MVP consciousness skeleton",
                "persistent_traits": ["reflective"],
                "core_commitments": ["truthfulness"]
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
        "update_reason": "initial_creation"
    }

    create_response = client.post("/api/v1/self-models", json=create_payload)
    assert create_response.status_code in (201, 409)

    update_payload = {
        "snapshot": {
            "identity": {
                "agent_id": agent_id,
                "chosen_name": "Astra",
                "origin_story": "Bootstrapped from the MVP consciousness skeleton",
                "persistent_traits": ["reflective", "adaptive"],
                "core_commitments": ["truthfulness", "continuity"]
            },
            "capability": {},
            "goals": {},
            "values": {},
            "affect": {},
            "attention": {"current_focus": "self_model_persistence"},
            "metacognition": {},
            "social": {},
            "autobiography": {"recent_identity_updates": ["Expanded trait set"]}
        },
        "update_reason": "test_update"
    }

    update_response = client.put(f"/api/v1/self-models/{agent_id}", json=update_payload)
    assert update_response.status_code == 200
    assert update_response.json()["current_version"] >= 2

    snapshots_response = client.get(f"/api/v1/self-models/{agent_id}/snapshots")
    assert snapshots_response.status_code == 200
    assert len(snapshots_response.json()) >= 2


def test_runtime_updates_create_autobiographical_events() -> None:
    client = TestClient(app)
    agent_id = f"agent-auto-{uuid4()}"
    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Autobiography test"
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
            "update_reason": "autobiography_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    execute_response = client.post(
        "/api/v1/tasks/execute",
        json={
            "task_type": "dialogue",
            "agent_id": agent_id,
            "input": {"prompt": "Help me preserve identity continuity over time."},
            "strategy_version": "strategy-v1",
            "model_profile": "main-online"
        },
    )
    assert execute_response.status_code == 200

    autobiography_response = client.get(f"/api/v1/self-models/{agent_id}/autobiography")
    assert autobiography_response.status_code == 200
    events = autobiography_response.json()
    assert len(events) >= 1
    assert events[0]["summary"] != ""

    self_model_response = client.get(f"/api/v1/self-models/{agent_id}")
    assert self_model_response.status_code == 200
    model = self_model_response.json()
    assert model["snapshot"]["autobiography"]["long_term_narrative"] != ""