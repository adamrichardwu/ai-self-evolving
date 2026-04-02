from packages.consciousness.evaluation.metrics import ConsciousnessEvaluationScore
from packages.consciousness.self_model.state import SelfModelSnapshot


def build_baseline_consciousness_score() -> ConsciousnessEvaluationScore:
    return ConsciousnessEvaluationScore(
        self_consistency=0.0,
        identity_continuity=0.0,
        metacognitive_accuracy=0.0,
        motivational_stability=0.0,
        social_modeling=0.0,
        reflective_recovery=0.0,
    )


def evaluate_self_model_snapshot(snapshot: SelfModelSnapshot) -> ConsciousnessEvaluationScore:
    trait_score = min(1.0, len(snapshot.identity.persistent_traits) / 5.0)
    commitment_score = min(1.0, len(snapshot.identity.core_commitments) / 5.0)
    identity_continuity = min(
        1.0,
        0.3
        + (0.4 if snapshot.autobiography.long_term_narrative else 0.0)
        + min(0.3, len(snapshot.autobiography.recent_identity_updates) / 20.0),
    )
    metacognitive_accuracy = max(
        0.0,
        1.0
        - (
            snapshot.metacognition.contradiction_score * 0.5
            + snapshot.metacognition.error_risk_score * 0.3
            + snapshot.metacognition.overload_score * 0.2
        ),
    )
    motivational_stability = min(1.0, len(snapshot.goals.learning_goals + snapshot.goals.active_task_goals) / 5.0)
    social_modeling = min(1.0, len(snapshot.social.active_relationships) / 5.0)
    reflective_recovery = min(1.0, len(snapshot.autobiography.recovered_failures) / 5.0)

    return ConsciousnessEvaluationScore(
        self_consistency=(trait_score + commitment_score) / 2.0,
        identity_continuity=identity_continuity,
        metacognitive_accuracy=metacognitive_accuracy,
        motivational_stability=motivational_stability,
        social_modeling=social_modeling,
        reflective_recovery=reflective_recovery,
    )
