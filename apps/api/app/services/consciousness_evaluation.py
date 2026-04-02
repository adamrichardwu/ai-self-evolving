from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.schemas.consciousness_evaluation import (
    ConsciousnessEvaluationResponse,
    CreateConsciousnessEvaluationRequest,
)
from packages.consciousness.evaluation.persistence import ConsciousnessEvaluationRecord
from packages.consciousness.evaluation.runner import evaluate_self_model_snapshot
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


def create_consciousness_evaluation(
    db: Session, request: CreateConsciousnessEvaluationRequest
) -> ConsciousnessEvaluationResponse | None:
    self_model = db.scalar(select(SelfModelRecord).where(SelfModelRecord.agent_id == request.agent_id))
    if self_model is None:
        return None

    snapshot = _record_to_snapshot(self_model)
    score = evaluate_self_model_snapshot(snapshot)
    evaluation = ConsciousnessEvaluationRecord(
        self_model_id=self_model.id,
        evaluation_type=request.evaluation_type,
        self_consistency=score.self_consistency,
        identity_continuity=score.identity_continuity,
        metacognitive_accuracy=score.metacognitive_accuracy,
        motivational_stability=score.motivational_stability,
        social_modeling=score.social_modeling,
        reflective_recovery=score.reflective_recovery,
        overall_score=score.overall_score,
        evaluator_notes=request.evaluator_notes,
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return ConsciousnessEvaluationResponse(
        id=evaluation.id,
        self_model_id=evaluation.self_model_id,
        evaluation_type=evaluation.evaluation_type,
        self_consistency=evaluation.self_consistency,
        identity_continuity=evaluation.identity_continuity,
        metacognitive_accuracy=evaluation.metacognitive_accuracy,
        motivational_stability=evaluation.motivational_stability,
        social_modeling=evaluation.social_modeling,
        reflective_recovery=evaluation.reflective_recovery,
        overall_score=evaluation.overall_score,
        evaluator_notes=evaluation.evaluator_notes,
    )


def list_consciousness_evaluations(db: Session, agent_id: str) -> list[ConsciousnessEvaluationResponse]:
    self_model = db.scalar(select(SelfModelRecord).where(SelfModelRecord.agent_id == agent_id))
    if self_model is None:
        return []
    evaluations = db.scalars(
        select(ConsciousnessEvaluationRecord)
        .where(ConsciousnessEvaluationRecord.self_model_id == self_model.id)
        .order_by(ConsciousnessEvaluationRecord.created_at.desc())
    ).all()
    return [
        ConsciousnessEvaluationResponse(
            id=evaluation.id,
            self_model_id=evaluation.self_model_id,
            evaluation_type=evaluation.evaluation_type,
            self_consistency=evaluation.self_consistency,
            identity_continuity=evaluation.identity_continuity,
            metacognitive_accuracy=evaluation.metacognitive_accuracy,
            motivational_stability=evaluation.motivational_stability,
            social_modeling=evaluation.social_modeling,
            reflective_recovery=evaluation.reflective_recovery,
            overall_score=evaluation.overall_score,
            evaluator_notes=evaluation.evaluator_notes,
        )
        for evaluation in evaluations
    ]