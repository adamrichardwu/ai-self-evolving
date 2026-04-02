from dataclasses import dataclass, field


@dataclass(slots=True)
class MetacognitiveAlert:
    kind: str
    message: str
    severity: float


@dataclass(slots=True)
class MetacognitiveSummary:
    self_confidence: float
    contradiction_score: float
    overload_score: float
    novelty_score: float
    error_risk_score: float
    alerts: list[MetacognitiveAlert] = field(default_factory=list)
