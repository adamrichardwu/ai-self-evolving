from dataclasses import dataclass


@dataclass(slots=True)
class ConsciousnessEvaluationScore:
    self_consistency: float
    identity_continuity: float
    metacognitive_accuracy: float
    motivational_stability: float
    social_modeling: float
    reflective_recovery: float

    @property
    def overall_score(self) -> float:
        return (
            self.self_consistency
            + self.identity_continuity
            + self.metacognitive_accuracy
            + self.motivational_stability
            + self.social_modeling
            + self.reflective_recovery
        ) / 6.0
