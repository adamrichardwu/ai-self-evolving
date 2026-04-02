from dataclasses import dataclass


@dataclass(slots=True)
class MotivationVector:
    knowledge_drive: float = 0.5
    competence_drive: float = 0.5
    consistency_drive: float = 0.5
    social_drive: float = 0.5


class MotivationalEngine:
    def reweight_after_failure(self, vector: MotivationVector) -> MotivationVector:
        vector.knowledge_drive = min(1.0, vector.knowledge_drive + 0.1)
        vector.competence_drive = min(1.0, vector.competence_drive + 0.05)
        return vector
