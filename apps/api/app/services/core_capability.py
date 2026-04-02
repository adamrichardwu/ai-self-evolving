import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.schemas.core_capability import (
    CoreCapabilityExportResponse,
    CoreCapabilityDatasetResponse,
    CoreCapabilityDatasetSummaryResponse,
    CoreCapabilityPreferenceExampleResponse,
    CoreCapabilitySFTExampleResponse,
    CreateCoreCapabilityDatasetRequest,
    CreateCoreCapabilityExportRequest,
)
from apps.api.app.core.settings import settings
from apps.api.app.services.evolution import _build_candidate_policy, _record_to_snapshot, get_active_evolution_policy
from packages.consciousness.evaluation.runner import evaluate_self_model_snapshot
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
            include_runtime_examples=request.include_runtime_examples,
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

    manifest = {
        "export_id": export_id,
        "agent_id": dataset.agent_id,
        "chosen_name": dataset.chosen_name,
        "objective": dataset.objective,
        "policy_source": dataset.policy_source,
        "active_policy": dataset.active_policy,
        "summary": dataset.summary.model_dump(),
        "created_at": timestamp,
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
    )


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