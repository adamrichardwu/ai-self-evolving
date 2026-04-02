from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.app.main import app


def test_refresh_goals_creates_persistent_goal_stack() -> None:
    client = TestClient(app)
    agent_id = f"agent-goals-{uuid4()}"
    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Goals module seed",
                    "core_commitments": ["truthfulness"]
                },
                "capability": {"known_limitations": ["cannot maintain perfect certainty"]},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "preserve coherent interaction"},
                "metacognition": {},
                "social": {"social_obligations": ["be responsive"]},
                "autobiography": {}
            },
            "update_reason": "goals_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    first_refresh = client.post(f"/api/v1/goals/{agent_id}/refresh")
    assert first_refresh.status_code == 201
    body = first_refresh.json()
    assert body["dominant_goal"] != ""
    assert len(body["goals"]) >= 3

    second_refresh = client.post(f"/api/v1/goals/{agent_id}/refresh")
    assert second_refresh.status_code == 201
    second_body = second_refresh.json()
    active_goals = [goal for goal in second_body["goals"] if goal["status"] == "active"]
    assert len(active_goals) >= 3

    list_response = client.get(f"/api/v1/goals/{agent_id}?active_only=true")
    assert list_response.status_code == 200
    goals = list_response.json()
    assert len(goals) == len(active_goals)

    self_model_response = client.get(f"/api/v1/self-models/{agent_id}")
    assert self_model_response.status_code == 200
    snapshot = self_model_response.json()["snapshot"]
    assert snapshot["goals"]["active_task_goals"] != []
    assert snapshot["attention"]["dominant_goal"] != ""


def test_goal_checkpoint_updates_goal_status() -> None:
    client = TestClient(app)
    agent_id = f"agent-goal-checkpoint-{uuid4()}"
    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Goal checkpoint seed",
                    "core_commitments": ["continuity"]
                },
                "capability": {},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "finish the current plan"},
                "metacognition": {},
                "social": {},
                "autobiography": {}
            },
            "update_reason": "goal_checkpoint_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    refresh_response = client.post(f"/api/v1/goals/{agent_id}/refresh")
    assert refresh_response.status_code == 201
    goal_id = refresh_response.json()["goals"][0]["id"]

    checkpoint_response = client.post(
        f"/api/v1/goals/{agent_id}/{goal_id}/checkpoints",
        json={
            "event_type": "completed_step",
            "summary": "The agent finished the current objective and recorded the outcome.",
            "score_delta": 0.4,
            "status": "completed",
        },
    )
    assert checkpoint_response.status_code == 201
    checkpoint = checkpoint_response.json()
    assert checkpoint["goal_id"] == goal_id

    goals_response = client.get(f"/api/v1/goals/{agent_id}")
    assert goals_response.status_code == 200
    goals = goals_response.json()
    completed_goal = next(goal for goal in goals if goal["id"] == goal_id)
    assert completed_goal["status"] == "completed"
    assert completed_goal["progress_score"] == 1.0