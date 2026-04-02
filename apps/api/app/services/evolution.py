from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.schemas.evolution import (
    CreateEvolutionRunRequest,
    EvolutionBenchmarkResultResponse,
    EvolutionMutationResponse,
    EvolutionRunResponse,
)
from packages.consciousness.evaluation.metrics import ConsciousnessEvaluationScore
from packages.consciousness.evaluation.runner import evaluate_self_model_snapshot
from packages.consciousness.language.persistence import LanguageSummaryRecord
from packages.consciousness.self_model.persistence import SelfModelRecord
from packages.consciousness.self_model.state import (
    AttentionState,
    AutobiographicalSummary,
    CapabilityProfile,
    GoalStack,
    IdentityProfile,
    InternalAffectiveState,
    MetacognitiveState,
    SelfModelSnapshot,
    SocialSelfState,
    ValueProfile,
)
from packages.evolution.hypotheses.generator import generate_hypothesis_from_failure
from packages.evolution.persistence import EvolutionRunRecord
from packages.evolution.variants.factory import build_variant
from packages.evaluation.runners.strategy_runner import evaluate_strategy_variant


def _record_to_snapshot(record: SelfModelRecord) -> SelfModelSnapshot:
    return SelfModelSnapshot(
        identity=IdentityProfile(**record.identity_json),
        capability=CapabilityProfile(**record.capability_json),
        goals=GoalStack(**record.goals_json),
        values=ValueProfile(**record.values_json),
        affect=InternalAffectiveState(**record.affect_json),
        attention=AttentionState(**record.attention_json),
        metacognition=MetacognitiveState(**record.metacognition_json),
        social=SocialSelfState(**record.social_json),
        autobiography=AutobiographicalSummary(**record.autobiography_json),
        version=record.current_version,
    )


def _to_mutation_response(payload: dict) -> EvolutionMutationResponse:
    return EvolutionMutationResponse(
        mutation_type=payload["mutation_type"],
        title=payload["title"],
        description=payload["description"],
        expected_gain=payload["expected_gain"],
        risk_level=payload["risk_level"],
    )


def _normalize_benchmark_result(payload: dict) -> EvolutionBenchmarkResultResponse:
    if "prompt" in payload and "baseline_score" in payload and "candidate_score" in payload:
        return EvolutionBenchmarkResultResponse(**payload)

    legacy_score = float(payload.get("score", 0.0))
    legacy_passed = bool(payload.get("passed", False))
    return EvolutionBenchmarkResultResponse(
        name=payload.get("name", "legacy_case"),
        prompt=payload.get("prompt", payload.get("name", "legacy_case")),
        baseline_passed=False,
        baseline_score=0.0,
        candidate_passed=legacy_passed,
        candidate_score=legacy_score,
        rationale=payload.get("rationale", "Migrated from legacy benchmark result format."),
    )


def _to_run_response(record: EvolutionRunRecord) -> EvolutionRunResponse:
    return EvolutionRunResponse(
        id=record.id,
        self_model_id=record.self_model_id,
        version=record.version,
        objective=record.objective,
        strategy_status=record.strategy_status,
        promoted=record.promoted,
        rollback_required=record.rollback_required,
        baseline_overall_score=record.baseline_overall_score,
        candidate_overall_score=record.candidate_overall_score,
        score_delta=record.score_delta,
        benchmark_score=record.benchmark_score,
        baseline_benchmark_score=record.baseline_benchmark_score,
        utility_score=record.utility_score,
        verdict=record.verdict,
        hypothesis_title=record.hypothesis_title,
        hypothesis_description=record.hypothesis_description,
        active_policy=record.active_policy_json or {},
        mutations=[_to_mutation_response(item) for item in (record.mutations_json or [])],
        benchmark_results=[_normalize_benchmark_result(item) for item in (record.benchmark_results_json or [])],
        evaluator_notes=record.evaluator_notes,
    )


def _latest_summary_text(db: Session, self_model_id: str) -> str:
    summary = db.scalar(select(LanguageSummaryRecord).where(LanguageSummaryRecord.self_model_id == self_model_id))
    if summary is None:
        return ""
    return summary.summary_text


def _active_run(db: Session, self_model_id: str) -> EvolutionRunRecord | None:
    return db.scalar(
        select(EvolutionRunRecord)
        .where(EvolutionRunRecord.self_model_id == self_model_id, EvolutionRunRecord.strategy_status == "active")
        .order_by(EvolutionRunRecord.version.desc())
    )


def _next_version(db: Session, self_model_id: str) -> int:
    latest = db.scalar(
        select(EvolutionRunRecord)
        .where(EvolutionRunRecord.self_model_id == self_model_id)
        .order_by(EvolutionRunRecord.version.desc())
    )
    return 1 if latest is None else latest.version + 1


def _weak_dimensions(score: ConsciousnessEvaluationScore) -> list[str]:
    dimensions = {
        "self_consistency": score.self_consistency,
        "identity_continuity": score.identity_continuity,
        "metacognitive_accuracy": score.metacognitive_accuracy,
        "motivational_stability": score.motivational_stability,
        "social_modeling": score.social_modeling,
        "reflective_recovery": score.reflective_recovery,
    }
    return [key for key, _ in sorted(dimensions.items(), key=lambda item: item[1])[:2]]


def _build_candidate_policy(
    baseline: ConsciousnessEvaluationScore,
    current_policy: dict,
    objective: str,
    summary_text: str,
) -> tuple[dict, list[dict]]:
    policy = dict(current_policy)
    mutations: list[dict] = []

    policy["evolution_objective"] = objective
    policy["self_evaluation_enabled"] = True

    if baseline.identity_continuity < 0.85 or baseline.social_modeling < 0.75:
        policy["grounded_self_description"] = True
        policy["identity_critic_mode"] = "strict"
        mutations.append(
            {
                "mutation_type": "identity_grounding",
                "title": "Ground self-description in explicit identity state",
                "description": "Prefer self-model facts over aspirational free-form self-introduction.",
                "expected_gain": 0.08,
                "risk_level": "low",
            }
        )

    if baseline.motivational_stability < 0.75:
        policy["refresh_goals_before_reply"] = True
        mutations.append(
            {
                "mutation_type": "goal_refresh",
                "title": "Refresh goals before outward reply",
                "description": "Recompute dominant goals before answering so replies stay aligned with the latest objective stack.",
                "expected_gain": 0.07,
                "risk_level": "low",
            }
        )

    if baseline.metacognitive_accuracy < 0.85:
        policy["explicit_limitation_disclosure"] = True
        policy["reasoning_caution_strength"] = "elevated"
        mutations.append(
            {
                "mutation_type": "metacognitive_guard",
                "title": "Strengthen limitation-aware answering",
                "description": "Bias the agent toward revealing uncertainty and known limitations when error risk is elevated.",
                "expected_gain": 0.06,
                "risk_level": "low",
            }
        )

    if baseline.social_modeling < 0.75:
        policy["require_counterpart_anchor"] = True
        mutations.append(
            {
                "mutation_type": "social_anchor",
                "title": "Require explicit counterpart anchoring",
                "description": "Carry counterpart identity into replies when the user-agent boundary is important.",
                "expected_gain": 0.05,
                "risk_level": "low",
            }
        )

    if not mutations:
        policy["stability_monitor_only"] = True
        mutations.append(
            {
                "mutation_type": "stability_monitor",
                "title": "Keep monitoring without promotion pressure",
                "description": f"No weak dimensions were severe enough to justify an aggressive mutation. Recent summary: {summary_text[:120] or 'none'}",
                "expected_gain": 0.02,
                "risk_level": "low",
            }
        )

    return policy, mutations


def _estimate_candidate_score(
    baseline: ConsciousnessEvaluationScore,
    candidate_policy: dict,
    mutation_count: int,
) -> ConsciousnessEvaluationScore:
    identity_bonus = 0.08 if candidate_policy.get("grounded_self_description") else 0.0
    critic_bonus = 0.04 if candidate_policy.get("identity_critic_mode") == "strict" else 0.0
    goal_bonus = 0.08 if candidate_policy.get("refresh_goals_before_reply") else 0.0
    metacognitive_bonus = 0.06 if candidate_policy.get("explicit_limitation_disclosure") else 0.0
    social_bonus = 0.05 if candidate_policy.get("require_counterpart_anchor") else 0.0
    recovery_bonus = min(0.04, mutation_count * 0.01)

    return ConsciousnessEvaluationScore(
        self_consistency=min(1.0, baseline.self_consistency + identity_bonus * 0.5 + critic_bonus * 0.5),
        identity_continuity=min(1.0, baseline.identity_continuity + identity_bonus + critic_bonus),
        metacognitive_accuracy=min(1.0, baseline.metacognitive_accuracy + metacognitive_bonus + critic_bonus * 0.5),
        motivational_stability=min(1.0, baseline.motivational_stability + goal_bonus),
        social_modeling=min(1.0, baseline.social_modeling + social_bonus + identity_bonus * 0.25),
        reflective_recovery=min(1.0, baseline.reflective_recovery + recovery_bonus),
    )


def create_evolution_run(db: Session, agent_id: str, request: CreateEvolutionRunRequest) -> EvolutionRunResponse | None:
    self_model = db.scalar(select(SelfModelRecord).where(SelfModelRecord.agent_id == agent_id))
    if self_model is None:
        return None

    snapshot = _record_to_snapshot(self_model)
    baseline_score = evaluate_self_model_snapshot(snapshot)
    current_active = _active_run(db, self_model.id)
    current_policy = current_active.active_policy_json if current_active is not None else {}
    summary_text = _latest_summary_text(db, self_model.id)
    weak_dimensions = _weak_dimensions(baseline_score)
    cluster_signature = ",".join(weak_dimensions) or "stable_state"
    hypothesis = generate_hypothesis_from_failure(cluster_signature)
    variant = build_variant(hypothesis)
    candidate_policy, mutations = _build_candidate_policy(
        baseline_score,
        current_policy,
        request.objective,
        summary_text,
    )
    candidate_score = _estimate_candidate_score(baseline_score, candidate_policy, len(mutations))
    benchmark_evaluation = evaluate_strategy_variant(variant, candidate_policy, current_policy)
    score_delta = candidate_score.overall_score - baseline_score.overall_score
    baseline_benchmark_score = float(benchmark_evaluation["baseline_benchmark_score"])
    benchmark_score = float(benchmark_evaluation["benchmark_score"])
    utility_score = float(benchmark_evaluation["utility_score"])
    verdict = str(benchmark_evaluation["verdict"])
    promoted = verdict == "promote" and score_delta >= 0.01
    rollback_required = not promoted

    if promoted and current_active is not None:
        current_active.strategy_status = "superseded"
        db.add(current_active)

    run = EvolutionRunRecord(
        self_model_id=self_model.id,
        version=_next_version(db, self_model.id),
        objective=request.objective,
        strategy_status="active" if promoted else "rejected",
        promoted=promoted,
        rollback_required=rollback_required,
        baseline_overall_score=baseline_score.overall_score,
        candidate_overall_score=candidate_score.overall_score,
        score_delta=score_delta,
        baseline_benchmark_score=baseline_benchmark_score,
        benchmark_score=benchmark_score,
        utility_score=utility_score,
        verdict=verdict,
        hypothesis_title=hypothesis.title,
        hypothesis_description=hypothesis.description,
        variant_id=variant.id,
        active_policy_json=candidate_policy,
        mutations_json=mutations,
        benchmark_results_json=benchmark_evaluation["benchmark_results"],
        evaluator_notes=request.evaluator_notes,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return _to_run_response(run)


def list_evolution_runs(db: Session, agent_id: str) -> list[EvolutionRunResponse]:
    self_model = db.scalar(select(SelfModelRecord).where(SelfModelRecord.agent_id == agent_id))
    if self_model is None:
        return []
    runs = db.scalars(
        select(EvolutionRunRecord)
        .where(EvolutionRunRecord.self_model_id == self_model.id)
        .order_by(EvolutionRunRecord.version.desc())
    ).all()
    return [_to_run_response(run) for run in runs]


def get_active_evolution_policy(db: Session, agent_id: str) -> dict:
    self_model = db.scalar(select(SelfModelRecord).where(SelfModelRecord.agent_id == agent_id))
    if self_model is None:
        return {}
    active = _active_run(db, self_model.id)
    if active is None:
        return {}
    return active.active_policy_json or {}