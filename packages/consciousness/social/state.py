from dataclasses import dataclass, field


@dataclass(slots=True)
class SocialInteractionSignal:
    counterpart_id: str
    counterpart_name: str = ""
    relationship_type: str = "user"
    interaction_summary: str = ""
    observed_sentiment: str = "neutral"
    role_in_context: str = ""
    social_obligations: list[str] = field(default_factory=list)
    trust_delta: float | None = None


@dataclass(slots=True)
class SocialRelationshipSnapshot:
    counterpart_id: str
    counterpart_name: str
    relationship_type: str
    trust_score: float
    familiarity_score: float
    interaction_count: int
    last_interaction_summary: str
    role_in_context: str
    social_obligations: list[str] = field(default_factory=list)