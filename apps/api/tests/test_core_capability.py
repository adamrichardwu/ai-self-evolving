import json
from pathlib import Path
import subprocess
import sys
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

    first_message = client.post(
        f"/api/v1/language/{agent_id}/messages",
        json={
            "text": "Who are you?",
            "counterpart_id": "user-primary",
            "counterpart_name": "Primary User",
            "relationship_type": "operator",
            "counterpart_role": "operator",
            "observed_sentiment": "neutral"
        },
    )
    assert first_message.status_code == 200

    second_message = client.post(
        f"/api/v1/language/{agent_id}/messages",
        json={
            "text": "What is your current goal?",
            "counterpart_id": "user-primary",
            "counterpart_name": "Primary User",
            "relationship_type": "operator",
            "counterpart_role": "operator",
            "observed_sentiment": "neutral"
        },
    )
    assert second_message.status_code == 200

    export_response = client.post(
        f"/api/v1/core-capability/{agent_id}/dataset",
        json={"objective": "prepare offline SFT and preference data"},
    )
    assert export_response.status_code == 200
    body = export_response.json()
    assert body["policy_source"] == "active"
    assert body["summary"]["sft_example_count"] >= 4
    assert body["summary"]["preference_example_count"] >= 4
    assert body["summary"]["dialogue_example_count"] >= 1
    assert "identity_boundary_maintenance" in body["summary"]["target_capabilities"]
    assert any(item["source"] == "dialogue_trace" for item in body["sft_examples"])
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
    assert body["training_manifest"]["schema_version"] == "core-capability-export/v2"
    assert body["training_manifest"]["datasets"]["sft"]["format"] == "instruction_response_jsonl"

    manifest = json.loads(Path(body["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["agent_id"] == agent_id
    assert manifest["summary"]["sft_example_count"] >= 4
    assert manifest["training_manifest"]["datasets"]["preference"]["format"] == "preference_pair_jsonl"

    sft_lines = Path(body["sft_dataset_path"]).read_text(encoding="utf-8").strip().splitlines()
    preference_lines = Path(body["preference_dataset_path"]).read_text(encoding="utf-8").strip().splitlines()
    assert len(sft_lines) >= 4
    assert len(preference_lines) >= 4


def test_core_capability_export_evaluation_scores_bundle(tmp_path, monkeypatch) -> None:
    client = TestClient(app)
    agent_id = f"agent-core-capability-evaluation-{uuid4()}"
    monkeypatch.setattr(settings, "core_capability_export_dir", str(tmp_path))

    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Evaluation seed",
                    "core_commitments": ["truthfulness", "continuity"]
                },
                "capability": {"known_limitations": ["small local model"]},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "evaluate training readiness", "dominant_goal": "preserve grounded behavior"},
                "metacognition": {"error_risk_score": 0.5},
                "social": {"active_relationships": ["Primary User"]},
                "autobiography": {"long_term_narrative": "I am Astra, distinct from the user."}
            },
            "update_reason": "evaluation_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    message_response = client.post(
        f"/api/v1/language/{agent_id}/messages",
        json={
            "text": "Introduce yourself clearly.",
            "counterpart_id": "user-primary",
            "counterpart_name": "Primary User",
            "relationship_type": "operator",
            "counterpart_role": "operator",
            "observed_sentiment": "neutral"
        },
    )
    assert message_response.status_code == 200

    export_response = client.post(
        f"/api/v1/core-capability/{agent_id}/export/run",
        json={"objective": "write evaluated training bundle", "export_label": "eval-ready"},
    )
    assert export_response.status_code == 200
    export_body = export_response.json()

    evaluation_response = client.post(
        "/api/v1/core-capability/evaluate",
        json={"manifest_path": export_body["manifest_path"]},
    )
    assert evaluation_response.status_code == 200
    body = evaluation_response.json()
    assert body["status"] == "completed"
    assert body["verdict"] in ["ready", "needs_more_data"]
    assert body["sft_example_count"] >= 4
    assert body["preference_example_count"] >= 4
    assert body["capability_coverage"] >= 3


def test_core_capability_training_job_preparation_writes_job_spec(tmp_path, monkeypatch) -> None:
    client = TestClient(app)
    agent_id = f"agent-core-capability-train-{uuid4()}"
    monkeypatch.setattr(settings, "core_capability_export_dir", str(tmp_path))

    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Training job seed",
                    "core_commitments": ["truthfulness", "continuity"]
                },
                "capability": {"known_limitations": ["small local model"]},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "prepare training spec", "dominant_goal": "preserve grounded behavior"},
                "metacognition": {"error_risk_score": 0.5},
                "social": {"active_relationships": ["Primary User"]},
                "autobiography": {"long_term_narrative": "I am Astra, distinct from the user."}
            },
            "update_reason": "training_job_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    export_response = client.post(
        f"/api/v1/core-capability/{agent_id}/export/run",
        json={"objective": "prepare training bundle", "export_label": "train-job"},
    )
    assert export_response.status_code == 200
    export_body = export_response.json()

    job_response = client.post(
        "/api/v1/core-capability/training-jobs",
        json={"manifest_path": export_body["manifest_path"], "job_label": "nightly"},
    )
    assert job_response.status_code == 200
    body = job_response.json()
    assert body["status"] == "prepared"
    assert Path(body["job_spec_path"]).exists()

    job_spec = json.loads(Path(body["job_spec_path"]).read_text(encoding="utf-8"))
    assert job_spec["schema_version"] == "core-capability-training-job/v1"
    assert len(job_spec["stages"]) >= 1
    assert "python -m train.sft" in job_spec["stages"][0]["recommended_command"]


def test_local_training_entrypoints_prepare_run_directories(tmp_path, monkeypatch) -> None:
    client = TestClient(app)
    agent_id = f"agent-core-capability-cli-{uuid4()}"
    monkeypatch.setattr(settings, "core_capability_export_dir", str(tmp_path))

    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "CLI training seed",
                    "core_commitments": ["truthfulness", "continuity"]
                },
                "capability": {"known_limitations": ["small local model"]},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "prepare CLI training run", "dominant_goal": "preserve grounded behavior"},
                "metacognition": {"error_risk_score": 0.5},
                "social": {"active_relationships": ["Primary User"]},
                "autobiography": {"long_term_narrative": "I am Astra, distinct from the user."}
            },
            "update_reason": "cli_training_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    export_response = client.post(
        f"/api/v1/core-capability/{agent_id}/export/run",
        json={"objective": "prepare CLI training bundle", "export_label": "cli-run"},
    )
    assert export_response.status_code == 200
    export_body = export_response.json()

    job_response = client.post(
        "/api/v1/core-capability/training-jobs",
        json={"manifest_path": export_body["manifest_path"], "job_label": "cli"},
    )
    assert job_response.status_code == 200
    job_body = job_response.json()

    sft_result = subprocess.run(
        [sys.executable, "-m", "train.sft", "--job-spec", job_body["job_spec_path"], "--run-name", "test-sft", "--dry-run"],
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
        check=False,
    )
    assert sft_result.returncode == 0, sft_result.stderr

    preference_result = subprocess.run(
        [sys.executable, "-m", "train.preference", "--job-spec", job_body["job_spec_path"], "--run-name", "test-pref", "--dry-run"],
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
        check=False,
    )
    assert preference_result.returncode == 0, preference_result.stderr

    job_spec = json.loads(Path(job_body["job_spec_path"]).read_text(encoding="utf-8"))
    sft_output_dir = Path(job_spec["stages"][0]["output_dir"]) / "test-sft" / "run_manifest.json"
    preference_output_dir = Path(job_spec["stages"][1]["output_dir"]) / "test-pref" / "run_manifest.json"
    assert sft_output_dir.exists()
    assert preference_output_dir.exists()

    sft_manifest = json.loads(sft_output_dir.read_text(encoding="utf-8"))
    preference_manifest = json.loads(preference_output_dir.read_text(encoding="utf-8"))
    assert sft_manifest["status"] == "dry_run_prepared"
    assert preference_manifest["status"] == "dry_run_prepared"


def test_core_capability_training_evaluation_dry_run_writes_report(tmp_path, monkeypatch) -> None:
    client = TestClient(app)
    agent_id = f"agent-core-capability-eval-run-{uuid4()}"
    monkeypatch.setattr(settings, "core_capability_export_dir", str(tmp_path))

    create_response = client.post(
        "/api/v1/self-models",
        json={
            "snapshot": {
                "identity": {
                    "agent_id": agent_id,
                    "chosen_name": "Astra",
                    "origin_story": "Training evaluation seed",
                    "core_commitments": ["truthfulness", "continuity"]
                },
                "capability": {"known_limitations": ["small local model"]},
                "goals": {},
                "values": {},
                "affect": {},
                "attention": {"current_focus": "evaluate trained candidate", "dominant_goal": "preserve grounded behavior"},
                "metacognition": {"error_risk_score": 0.5},
                "social": {"active_relationships": ["Primary User"]},
                "autobiography": {"long_term_narrative": "I am Astra, distinct from the user."}
            },
            "update_reason": "training_evaluation_seed"
        },
    )
    assert create_response.status_code in (201, 409)

    export_response = client.post(
        f"/api/v1/core-capability/{agent_id}/export/run",
        json={"objective": "prepare training evaluation bundle", "export_label": "eval-run"},
    )
    assert export_response.status_code == 200
    export_body = export_response.json()

    job_response = client.post(
        "/api/v1/core-capability/training-jobs",
        json={"manifest_path": export_body["manifest_path"], "job_label": "eval-run"},
    )
    assert job_response.status_code == 200
    job_body = job_response.json()

    sft_result = subprocess.run(
        [sys.executable, "-m", "train.sft", "--job-spec", job_body["job_spec_path"], "--run-name", "eval-sft", "--dry-run"],
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
        check=False,
    )
    assert sft_result.returncode == 0, sft_result.stderr

    run_manifest_path = Path(json.loads(sft_result.stdout)["output_dir"]) / "run_manifest.json"
    evaluation_response = client.post(
        "/api/v1/core-capability/training-evaluations",
        json={"run_manifest_path": str(run_manifest_path), "dry_run": True},
    )
    assert evaluation_response.status_code == 200
    body = evaluation_response.json()
    assert body["status"] == "completed"
    assert body["verdict"] == "dry_run"
    assert Path(body["evaluation_path"]).exists()