import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.app.main import app
from apps.api.app.core.settings import settings


def test_core_capability_dataset_exports_benchmark_training_examples() -> None:
    client = TestClient(app)
    agent_id = f"agent-core-capability-{uuid4()}"

    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Core capability export seed",
                    "core_commitments": ["truthfulness", "continuity"]
                },
                "capability": {"known_limitations": ["small local model"]},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "improve core reasoning", "dominant_goal": "maintain identity clarity"},
                "metacognition": {"error_risk_score": 0.4},
                "social": {"active_relationships": ["Primary User"]},
                "autobiography": {"long_term_narrative": "I am Astra, distinct from the user."}
            },
            "update_reason": "core_capability_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    evolve_response = client.post(
        f"/api/v1/self-evolution/{agent_id}/run",
        json={"objective": "improve grounded self-description and core reasoning"},
    )
    assert evolve_response.status_code == 201

    export_response = client.post(
        f"/api/v1/core-capability/{agent_id}/dataset",
        json={"objective": "prepare offline SFT and preference data"},
    )
    assert export_response.status_code == 200
    body = export_response.json()
    assert body["policy_source"] == "active"
    assert body["summary"]["sft_example_count"] >= 4
    assert body["summary"]["preference_example_count"] >= 4
    assert "identity_boundary_maintenance" in body["summary"]["target_capabilities"]
    assert body["preference_examples"][0]["chosen_response"] != body["preference_examples"][0]["rejected_response"]


def test_core_capability_dataset_falls_back_to_recommended_policy_without_active_run() -> None:
    client = TestClient(app)
    agent_id = f"agent-core-capability-fallback-{uuid4()}"

    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Fallback dataset seed",
                    "core_commitments": ["truthfulness"]
                },
                "capability": {"known_limitations": ["small local model"]},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "stabilize reasoning"},
                "metacognition": {"error_risk_score": 0.6},
                "social": {"active_relationships": ["Primary User"]},
                "autobiography": {"long_term_narrative": "I am Astra."}
            },
            "update_reason": "fallback_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    export_response = client.post(
        f"/api/v1/core-capability/{agent_id}/dataset",
        json={"objective": "prepare fallback offline training data", "include_runtime_examples": False},
    )
    assert export_response.status_code == 200
    body = export_response.json()
    assert body["policy_source"] == "recommended"
    assert body["summary"]["preference_example_count"] >= 4
    assert body["summary"]["sft_example_count"] >= 4


def test_core_capability_export_run_writes_jsonl_bundle(tmp_path, monkeypatch) -> None:
    client = TestClient(app)
    agent_id = f"agent-core-capability-export-{uuid4()}"
    monkeypatch.setattr(settings, "core_capability_export_dir", str(tmp_path))

    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Export bundle seed",
                    "core_commitments": ["truthfulness", "continuity"]
                },
                "capability": {"known_limitations": ["small local model"]},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "export training data", "dominant_goal": "preserve grounded behavior"},
                "metacognition": {"error_risk_score": 0.5},
                "social": {"active_relationships": ["Primary User"]},
                "autobiography": {"long_term_narrative": "I am Astra, distinct from the user."}
            },
            "update_reason": "export_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    export_response = client.post(
        f"/api/v1/core-capability/{agent_id}/export/run",
        json={"objective": "write offline training bundle", "export_label": "nightly-core"},
    )
    assert export_response.status_code == 200
    body = export_response.json()
    assert body["status"] == "completed"
    assert Path(body["manifest_path"]).exists()
    assert Path(body["sft_dataset_path"]).exists()
    assert Path(body["preference_dataset_path"]).exists()

    manifest = json.loads(Path(body["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["agent_id"] == agent_id
    assert manifest["summary"]["sft_example_count"] >= 4

    sft_lines = Path(body["sft_dataset_path"]).read_text(encoding="utf-8").strip().splitlines()
    preference_lines = Path(body["preference_dataset_path"]).read_text(encoding="utf-8").strip().splitlines()
    assert len(sft_lines) >= 4
    assert len(preference_lines) >= 4