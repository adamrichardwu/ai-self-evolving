from fastapi.testclient import TestClient

from apps.api.app.main import app


def test_autobiography_consolidation_endpoint() -> None:
    client = TestClient(app)
    agent_id = "agent-consolidation-001"

    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Offline consolidation test"
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
            "update_reason": "seed"
        },
    )
    assert create_response.status_code in (201, 409)

    for prompt in [
        "Preserve identity continuity during change.",
        "Reflect on the meaning of your recent focus.",
        "Track how your long-term narrative is evolving.",
    ]:
        execute_response = client.post(
            "/api/v1/tasks/execute",
            json={
                "task_type": "dialogue",
                "agent_id": agent_id,
                "input": {"prompt": prompt},
                "strategy_version": "strategy-v1",
                "model_profile": "main-online"
            },
        )
        assert execute_response.status_code == 200

    consolidate_response = client.post(
        f"/api/v1/autobiography/{agent_id}/consolidate",
        json={"max_events": 5},
    )
    assert consolidate_response.status_code == 201
    body = consolidate_response.json()
    assert body["event_count"] >= 1
    assert body["narrative_delta"] != ""

    list_response = client.get(f"/api/v1/autobiography/{agent_id}/consolidations")
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 1

    self_model_response = client.get(f"/api/v1/self-models/{agent_id}")
    assert self_model_response.status_code == 200
    self_model = self_model_response.json()
    assert "dominant themes" in self_model["snapshot"]["autobiography"]["long_term_narrative"]
