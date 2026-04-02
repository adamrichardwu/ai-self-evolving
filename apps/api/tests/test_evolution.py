from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.app.main import app
from apps.api.app.services import language as language_service
from apps.api.app.services.evolution import _to_run_response
from packages.evolution.persistence import EvolutionRunRecord


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
    assert body["baseline_benchmark_score"] >= 0.0
    assert body["benchmark_score"] > 0.0
    assert body["utility_score"] >= 0.0
    assert body["verdict"] in ["promote", "needs_review"]
    assert len(body["benchmark_results"]) >= 1
    assert "baseline_score" in body["benchmark_results"][0]
    assert "candidate_score" in body["benchmark_results"][0]

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


def test_self_evolution_run_uses_benchmark_verdict_for_promotion() -> None:
    client = TestClient(app)
    agent_id = f"agent-evolution-benchmark-{uuid4()}"

    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Benchmark evolution seed",
                    "core_commitments": ["truthfulness", "continuity"]
                },
                "capability": {"known_limitations": ["small local model"]},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "stabilize behavior"},
                "metacognition": {"error_risk_score": 0.5},
                "social": {"active_relationships": ["Primary User"]},
                "autobiography": {"long_term_narrative": "I am Astra, distinct from the user."}
            },
            "update_reason": "benchmark_evolution_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    run_response = client.post(
        f"/api/v1/self-evolution/{agent_id}/run",
        json={"objective": "strengthen self-description, goal alignment, and limitation-aware answers"},
    )
    assert run_response.status_code == 201
    body = run_response.json()
    assert body["verdict"] == "promote"
    assert body["promoted"] is True
    assert body["benchmark_score"] >= 0.72
    assert body["benchmark_score"] > body["baseline_benchmark_score"]


def test_evolution_response_supports_legacy_benchmark_result_format() -> None:
    record = EvolutionRunRecord(
        id="legacy-run-001",
        self_model_id="self-model-legacy",
        version=1,
        objective="legacy compatibility",
        strategy_status="active",
        promoted=True,
        rollback_required=False,
        baseline_overall_score=0.4,
        candidate_overall_score=0.5,
        score_delta=0.1,
        baseline_benchmark_score=0.0,
        benchmark_score=1.0,
        utility_score=0.7,
        verdict="promote",
        hypothesis_title="Legacy benchmark migration",
        hypothesis_description="Ensure older stored benchmark payloads still deserialize.",
        variant_id="variant-legacy",
        active_policy_json={"grounded_self_description": True},
        mutations_json=[],
        benchmark_results_json=[
            {
                "name": "identity_grounding",
                "passed": True,
                "score": 1.0,
                "rationale": "Legacy format without explicit baseline/candidate fields.",
            }
        ],
        evaluator_notes="legacy compatibility",
    )

    response = _to_run_response(record)
    assert len(response.benchmark_results) == 1
    assert response.benchmark_results[0].candidate_passed is True
    assert response.benchmark_results[0].candidate_score == 1.0
    assert response.benchmark_results[0].baseline_score == 0.0