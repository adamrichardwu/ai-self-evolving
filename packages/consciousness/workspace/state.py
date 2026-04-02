from dataclasses import dataclass, field


@dataclass(slots=True)
class WorkspaceSignal:
    signal_id: str
    content: str
    risk_score: float
    urgency_score: float
    goal_relevance: float
    novelty_score: float
    social_score: float

    @property
    def salience(self) -> float:
        return (
            self.risk_score
            + self.urgency_score
            + self.goal_relevance
            + self.novelty_score
            + self.social_score
        )


@dataclass(slots=True)
class WorkspaceCycleState:
    dominant_focus: str = ""
    active_broadcast_items: list[str] = field(default_factory=list)
    suppressed_items: list[str] = field(default_factory=list)
    attention_shift_reason: str = ""
    cycle_confidence: float = 0.0
