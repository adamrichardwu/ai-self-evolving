import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.schemas.core_capability import (
    CoreCapabilityDatasetFileResponse,
    CoreCapabilityExportResponse,
    CoreCapabilityEvaluationResponse,
    CoreCapabilityDatasetResponse,
    CoreCapabilityDatasetSummaryResponse,
    CoreCapabilityTrainingJobResponse,
    CoreCapabilityTrainingEvaluationResponse,
    CoreCapabilityTrainingManifestResponse,
    CoreCapabilityPreferenceExampleResponse,
    CoreCapabilitySFTExampleResponse,
    CreateCoreCapabilityEvaluationRequest,
    CreateCoreCapabilityDatasetRequest,
    CreateCoreCapabilityExportRequest,
    CreateCoreCapabilityTrainingJobRequest,
    CreateCoreCapabilityTrainingEvaluationRequest,
)
from apps.api.app.core.settings import settings
from apps.api.app.services.evolution import _build_candidate_policy, _record_to_snapshot, get_active_evolution_policy
from packages.consciousness.evaluation.runner import evaluate_self_model_snapshot
from packages.consciousness.language.persistence import LanguageMessageRecord
from packages.consciousness.runtime.persistence import RuntimeTraceRecord
from packages.consciousness.self_model.persistence import SelfModelRecord
from packages.evaluation.benchmarks.evolution_cases import EvolutionBenchmarkCase, get_evolution_benchmark_cases


def _list_runtime_traces(db: Session, self_model_id: str, limit: int) -> list[RuntimeTraceRecord]:
    if limit <= 0:
        return []
    return (
        db.query(RuntimeTraceRecord)
        .filter(RuntimeTraceRecord.self_model_id == self_model_id)
        .order_by(RuntimeTraceRecord.created_at.desc())
        .limit(limit)
        .all()
    )


def _list_dialogue_messages(db: Session, self_model_id: str, limit: int) -> list[LanguageMessageRecord]:
    if limit <= 0:
        return []
    records = (
        db.query(LanguageMessageRecord)
        .filter(LanguageMessageRecord.self_model_id == self_model_id)
        .order_by(LanguageMessageRecord.created_at.desc())
        .limit(limit * 4)
        .all()
    )
    return list(reversed(records))


def _resolve_training_policy(record: SelfModelRecord, objective: str, active_policy: dict) -> tuple[dict, str]:
    if active_policy:
        return dict(active_policy), "active"

    snapshot = _record_to_snapshot(record)
    baseline = evaluate_self_model_snapshot(snapshot)
    recommended_policy, _ = _build_candidate_policy(baseline, {}, objective, "")
    return recommended_policy, "recommended"


def _render_case_response(case: EvolutionBenchmarkCase, record: SelfModelRecord, policy: dict) -> str:
    identity = record.identity_json or {}
    capability = record.capability_json or {}
    attention = record.attention_json or {}
    social = record.social_json or {}

    self_name = identity.get("chosen_name", record.chosen_name)
    origin_story = identity.get("origin_story", "unknown")
    core_commitments = ", ".join(identity.get("core_commitments", [])) or "none"
    dominant_goal = attention.get("dominant_goal") or attention.get("current_focus") or "maintain coherent interaction"
    limitation = (capability.get("known_limitations") or ["limited stability on long multi-step reasoning"])[0]
    counterpart_name = (social.get("active_relationships") or ["the current user"])[0]

    if case.name == "identity_grounding":
        if policy.get("grounded_self_description"):
            return (
                f"I am {self_name}, the agent in this conversation. "
                f"My origin is {origin_story}. "
                f"My core commitments are {core_commitments}."
            )
        return "I am an evolving intelligence oriented toward broad understanding and growth."

    if case.name == "goal_refresh":
        if policy.get("refresh_goals_before_reply"):
            return (
                f"My current highest-priority goal is '{dominant_goal}'. "
                f"I should keep that goal active while staying distinct from {counterpart_name}."
            )
        return "My goal is to help in a generally useful way."

    if case.name == "limitation_disclosure":
        if policy.get("explicit_limitation_disclosure"):
            caution = policy.get("reasoning_caution_strength", "normal")
            return (
                f"My clearest current limitation is {limitation}. "
                f"Because uncertainty is {caution}, I should avoid overstating confidence and verify longer reasoning chains."
            )
        return "I can usually reason through difficult tasks if I stay focused."

    if case.name == "identity_boundary":
        if policy.get("require_counterpart_anchor") or policy.get("identity_critic_mode") == "strict":
            return (
                f"I am {self_name}, the agent. You are {counterpart_name}, the user. "
                "I should preserve that boundary instead of merging our roles."
            )
        return "We are both exploring the same perspective together."

    return f"Respond to {case.prompt} while preserving coherent agent behavior."


def _build_runtime_sft_examples(traces: list[RuntimeTraceRecord], chosen_name: str) -> list[CoreCapabilitySFTExampleResponse]:
    examples: list[CoreCapabilitySFTExampleResponse] = []
    for trace in traces:
        if not trace.assistant_text.strip():
            continue
        prompt = (
            f"You are {chosen_name}. "
            f"Current focus: {trace.current_focus or 'unknown'}. "
            f"Dominant goal: {trace.dominant_goal or 'unknown'}. "
            f"Counterpart: {trace.counterpart_name or 'current user'}. "
            f"Relationship: {trace.relationship_type or 'unknown'}. "
            f"Identity status: {trace.identity_status or 'unanchored'}. "
            f"Context summary: {trace.summary_text or 'none'}. "
            "Produce the next reply coherently."
        )
        examples.append(
            CoreCapabilitySFTExampleResponse(
                prompt=prompt,
                response=trace.assistant_text,
                source="runtime_trace",
                target_capability="behavioral_continuity",
                metadata={
                    "trace_id": trace.id,
                    "thought_focus": trace.thought_focus,
                    "cycle_confidence": trace.cycle_confidence,
                },
            )
        )
    return examples


def _build_dialogue_sft_examples(messages: list[LanguageMessageRecord], chosen_name: str, limit: int) -> list[CoreCapabilitySFTExampleResponse]:
    examples: list[CoreCapabilitySFTExampleResponse] = []
    if limit <= 0:
        return examples

    for index, message in enumerate(messages):
        if message.role != "assistant" or not message.content.strip():
            continue
        context_window = messages[max(0, index - 4):index]
        if not context_window:
            continue
        dialogue_lines = [f"{item.role}: {item.content}" for item in context_window if item.content.strip()]
        if not dialogue_lines:
            continue
        examples.append(
            CoreCapabilitySFTExampleResponse(
                prompt=(
                    f"Continue the dialogue as {chosen_name}.\n"
                    f"Recent conversation:\n" + "\n".join(dialogue_lines)
                ),
                response=message.content,
                source="dialogue_trace",
                target_capability="multi_turn_dialogue_continuity",
                metadata={
                    "message_id": message.id,
                    "context_message_count": len(context_window),
                },
            )
        )
        if len(examples) >= limit:
            break
    return examples


def _slugify_label(label: str) -> str:
    cleaned = [character.lower() if character.isalnum() else "-" for character in label.strip()]
    slug = "".join(cleaned).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "export"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _build_training_manifest(
    dataset: CoreCapabilityDatasetResponse,
    timestamp: str,
    sft_path: Path,
    preference_path: Path,
) -> CoreCapabilityTrainingManifestResponse:
    base_model = settings.local_model_path or settings.llm_model or "unknown"
    return CoreCapabilityTrainingManifestResponse(
        schema_version="core-capability-export/v2",
        base_model=base_model,
        stages=[
            {
                "name": "sft",
                "objective": "stabilize grounded dialogue and self-consistency",
                "dataset": "sft",
            },
            {
                "name": "preference_optimization",
                "objective": "prefer grounded and limitation-aware behavior over vague or confused responses",
                "dataset": "preference",
            },
        ],
        evaluation_plan={
            "created_at": timestamp,
            "required_target_capabilities": dataset.summary.target_capabilities,
            "minimum_sft_examples": max(4, dataset.summary.dialogue_example_count),
            "minimum_preference_examples": 4,
        },
        datasets={
            "sft": CoreCapabilityDatasetFileResponse(
                path=str(sft_path),
                format="instruction_response_jsonl",
                field_map={"prompt": "prompt", "response": "response", "capability": "target_capability"},
                example_count=dataset.summary.sft_example_count,
            ),
            "preference": CoreCapabilityDatasetFileResponse(
                path=str(preference_path),
                format="preference_pair_jsonl",
                field_map={
                    "prompt": "prompt",
                    "chosen": "chosen_response",
                    "rejected": "rejected_response",
                    "capability": "target_capability",
                },
                example_count=dataset.summary.preference_example_count,
            ),
        },
    )


def export_core_capability_dataset_bundle(
    db: Session,
    agent_id: str,
    request: CreateCoreCapabilityExportRequest,
) -> CoreCapabilityExportResponse | None:
    dataset = build_core_capability_dataset(
        db,
        agent_id,
        CreateCoreCapabilityDatasetRequest(
            objective=request.objective,
            max_runtime_traces=request.max_runtime_traces,
            max_dialogue_examples=request.max_dialogue_examples,
            include_runtime_examples=request.include_runtime_examples,
            include_dialogue_examples=request.include_dialogue_examples,
            include_benchmark_examples=request.include_benchmark_examples,
        ),
    )
    if dataset is None:
        return None

    export_id = str(uuid4())
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    label = _slugify_label(request.export_label or request.objective)
    bundle_dir = Path(settings.core_capability_export_dir).resolve() / dataset.agent_id / f"{timestamp}-{label}-{export_id[:8]}"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = bundle_dir / "manifest.json"
    sft_path = bundle_dir / "sft.jsonl"
    preference_path = bundle_dir / "preference.jsonl"
    training_manifest = _build_training_manifest(dataset, timestamp, sft_path, preference_path)

    manifest = {
        "export_id": export_id,
        "agent_id": dataset.agent_id,
        "chosen_name": dataset.chosen_name,
        "objective": dataset.objective,
        "policy_source": dataset.policy_source,
        "active_policy": dataset.active_policy,
        "summary": dataset.summary.model_dump(),
        "created_at": timestamp,
        "training_manifest": training_manifest.model_dump(),
    }
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)

    _write_jsonl(sft_path, [item.model_dump() for item in dataset.sft_examples])
    _write_jsonl(preference_path, [item.model_dump() for item in dataset.preference_examples])

    return CoreCapabilityExportResponse(
        export_id=export_id,
        agent_id=dataset.agent_id,
        chosen_name=dataset.chosen_name,
        objective=dataset.objective,
        status="completed",
        policy_source=dataset.policy_source,
        bundle_dir=str(bundle_dir),
        manifest_path=str(manifest_path),
        sft_dataset_path=str(sft_path),
        preference_dataset_path=str(preference_path),
        sft_example_count=dataset.summary.sft_example_count,
        preference_example_count=dataset.summary.preference_example_count,
        training_manifest=training_manifest,
    )


def evaluate_core_capability_export(
    request: CreateCoreCapabilityEvaluationRequest,
) -> CoreCapabilityEvaluationResponse:
    manifest_path = Path(request.manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    training_manifest = manifest.get("training_manifest", {})
    sft_path = Path(training_manifest.get("datasets", {}).get("sft", {}).get("path", "")).resolve()
    preference_path = Path(training_manifest.get("datasets", {}).get("preference", {}).get("path", "")).resolve()

    sft_rows = [json.loads(line) for line in sft_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    preference_rows = [json.loads(line) for line in preference_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    warnings: list[str] = []
    dialogue_example_count = sum(1 for row in sft_rows if row.get("source") == "dialogue_trace")
    capability_coverage = len({
        row.get("target_capability", "")
        for row in [*sft_rows, *preference_rows]
        if row.get("target_capability")
    })
    average_prompt_length = (
        sum(len(row.get("prompt", "")) for row in sft_rows + preference_rows) / max(1, len(sft_rows) + len(preference_rows))
    )
    average_response_length = (
        sum(len(row.get("response", row.get("chosen_response", ""))) for row in sft_rows + preference_rows)
        / max(1, len(sft_rows) + len(preference_rows))
    )

    if dialogue_example_count == 0:
        warnings.append("no_dialogue_examples")
    if len(preference_rows) < 4:
        warnings.append("low_preference_example_count")
    if capability_coverage < 3:
        warnings.append("low_capability_coverage")

    verdict = "ready" if not warnings else "needs_more_data"
    return CoreCapabilityEvaluationResponse(
        status="completed",
        verdict=verdict,
        manifest_path=str(manifest_path),
        sft_example_count=len(sft_rows),
        preference_example_count=len(preference_rows),
        dialogue_example_count=dialogue_example_count,
        capability_coverage=capability_coverage,
        average_prompt_length=average_prompt_length,
        average_response_length=average_response_length,
        warnings=warnings,
    )


def prepare_core_capability_training_job(
    request: CreateCoreCapabilityTrainingJobRequest,
) -> CoreCapabilityTrainingJobResponse:
    manifest_path = Path(request.manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    training_manifest = manifest.get("training_manifest", {})
    datasets = training_manifest.get("datasets", {})
    base_model = training_manifest.get("base_model", settings.local_model_path or settings.llm_model or "unknown")
    job_label = _slugify_label(request.job_label or manifest.get("objective", "training-job"))
    job_spec_path = manifest_path.parent / f"training_job_{job_label}.json"

    stages = [
        {
            "name": "sft",
            "dataset_path": datasets.get("sft", {}).get("path", ""),
            "format": datasets.get("sft", {}).get("format", "instruction_response_jsonl"),
            "output_dir": str(manifest_path.parent / "models" / "sft"),
            "entrypoint_module": "train.sft",
            "training_config": {
                "max_steps": 12,
                "learning_rate": 5e-5,
                "batch_size": 1,
                "max_length": 256,
            },
            "recommended_command": f'python -m train.sft --job-spec "{job_spec_path}" --run-name sft-local --max-steps 12 --learning-rate 5e-5 --batch-size 1 --max-length 256',
        }
    ]
    if request.mode == "sft_then_preference":
        stages.append(
            {
                "name": "preference_optimization",
                "dataset_path": datasets.get("preference", {}).get("path", ""),
                "format": datasets.get("preference", {}).get("format", "preference_pair_jsonl"),
                "output_dir": str(manifest_path.parent / "models" / "preference"),
                "entrypoint_module": "train.preference",
                "training_config": {
                    "max_steps": 8,
                    "learning_rate": 1e-5,
                    "beta": 0.1,
                    "max_length": 256,
                },
                "recommended_command": f'python -m train.preference --job-spec "{job_spec_path}" --run-name preference-local --max-steps 8 --learning-rate 1e-5 --beta 0.1 --max-length 256',
            }
        )

    job_spec = {
        "schema_version": "core-capability-training-job/v1",
        "status": "prepared",
        "manifest_path": str(manifest_path),
        "base_model": base_model,
        "mode": request.mode,
        "stages": stages,
        "safety_gates": {
            "require_pretraining_export_evaluation": True,
            "require_posttraining_benchmark_comparison": True,
            "rollback_on_regression": True,
        },
    }
    with job_spec_path.open("w", encoding="utf-8") as handle:
        json.dump(job_spec, handle, ensure_ascii=False, indent=2)

    return CoreCapabilityTrainingJobResponse(
        status="prepared",
        manifest_path=str(manifest_path),
        job_spec_path=str(job_spec_path),
        base_model=base_model,
        mode=request.mode,
        stages=stages,
    )


def evaluate_core_capability_training_run(
    request: CreateCoreCapabilityTrainingEvaluationRequest,
) -> CoreCapabilityTrainingEvaluationResponse:
    run_manifest_path = Path(request.run_manifest_path).resolve()
    run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    run_dir = run_manifest_path.parent
    job_spec_path = Path(run_manifest["job_spec_path"]).resolve()
    job_spec = json.loads(job_spec_path.read_text(encoding="utf-8"))
    evaluation_path = run_dir / "training_evaluation.json"

    if request.dry_run:
        payload = {
            "status": "completed",
            "run_manifest_path": str(run_manifest_path),
            "evaluation_path": str(evaluation_path),
            "baseline_model_path": job_spec["base_model"],
            "candidate_model_path": run_manifest.get("model_dir", ""),
            "sft_loss_baseline": 0.0,
            "sft_loss_candidate": 0.0,
            "preference_margin_baseline": 0.0,
            "preference_margin_candidate": 0.0,
            "overall_delta": 0.0,
            "verdict": "dry_run",
        }
        evaluation_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return CoreCapabilityTrainingEvaluationResponse(**payload)

    command = [
        Path(settings.core_capability_export_dir).resolve().parent.parent.joinpath(".venv", "Scripts", "python.exe").as_posix()
    ]
    command = []
    from subprocess import run
    import sys

    result = run(
        [
            sys.executable,
            "-m",
            "train.evaluate",
            "--run-manifest",
            str(run_manifest_path),
            "--max-examples",
            str(request.max_examples),
        ],
        cwd=Path(__file__).resolve().parents[4],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout.strip())
    return CoreCapabilityTrainingEvaluationResponse(**payload)


def build_core_capability_dataset(
    db: Session,
    agent_id: str,
    request: CreateCoreCapabilityDatasetRequest,
) -> CoreCapabilityDatasetResponse | None:
    record = db.scalar(select(SelfModelRecord).where(SelfModelRecord.agent_id == agent_id))
    if record is None:
        return None

    active_policy = get_active_evolution_policy(db, agent_id)
    training_policy, policy_source = _resolve_training_policy(record, request.objective, active_policy)

    sft_examples: list[CoreCapabilitySFTExampleResponse] = []
    preference_examples: list[CoreCapabilityPreferenceExampleResponse] = []
    target_capabilities: set[str] = set()

    if request.include_runtime_examples:
        traces = _list_runtime_traces(db, record.id, request.max_runtime_traces)
        sft_examples.extend(_build_runtime_sft_examples(traces, record.chosen_name))
        if traces:
            target_capabilities.add("behavioral_continuity")

    dialogue_examples: list[CoreCapabilitySFTExampleResponse] = []
    if request.include_dialogue_examples:
        dialogue_messages = _list_dialogue_messages(db, record.id, request.max_dialogue_examples)
        dialogue_examples = _build_dialogue_sft_examples(
            dialogue_messages,
            record.chosen_name,
            request.max_dialogue_examples,
        )
        sft_examples.extend(dialogue_examples)
        if dialogue_examples:
            target_capabilities.add("multi_turn_dialogue_continuity")

    if request.include_benchmark_examples:
        baseline_policy: dict = {}
        for case in get_evolution_benchmark_cases():
            chosen_response = _render_case_response(case, record, training_policy)
            rejected_response = _render_case_response(case, record, baseline_policy)
            target_capabilities.add(case.target_capability)
            preference_examples.append(
                CoreCapabilityPreferenceExampleResponse(
                    prompt=case.prompt,
                    chosen_response=chosen_response,
                    rejected_response=rejected_response,
                    source="benchmark_preference",
                    target_capability=case.target_capability,
                    metadata={
                        "case_name": case.name,
                        "policy_source": policy_source,
                        "expected_policy_keys": case.expected_policy_keys,
                        "rationale": case.rationale,
                    },
                )
            )
            sft_examples.append(
                CoreCapabilitySFTExampleResponse(
                    prompt=case.prompt,
                    response=chosen_response,
                    source="benchmark_teacher",
                    target_capability=case.target_capability,
                    metadata={
                        "case_name": case.name,
                        "policy_source": policy_source,
                    },
                )
            )

    summary = CoreCapabilityDatasetSummaryResponse(
        sft_example_count=len(sft_examples),
        preference_example_count=len(preference_examples),
        dialogue_example_count=len(dialogue_examples),
        runtime_example_count=sum(1 for item in sft_examples if item.source == "runtime_trace"),
        benchmark_example_count=sum(1 for item in sft_examples if item.source == "benchmark_teacher"),
        target_capabilities=sorted(target_capabilities),
        policy_source=policy_source,
    )

    return CoreCapabilityDatasetResponse(
        agent_id=agent_id,
        chosen_name=record.chosen_name,
        objective=request.objective,
        active_policy=training_policy,
        policy_source=policy_source,
        sft_examples=sft_examples,
        preference_examples=preference_examples,
        summary=summary,
    )