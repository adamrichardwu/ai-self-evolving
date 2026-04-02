from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class IdentityProfile:
    agent_id: str
    chosen_name: str
    origin_story: str
    persistent_traits: list[str] = field(default_factory=list)
    core_commitments: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CapabilityProfile:
    skill_domains: list[str] = field(default_factory=list)
    current_strengths: list[str] = field(default_factory=list)
    known_limitations: list[str] = field(default_factory=list)
    confidence_by_domain: dict[str, float] = field(default_factory=dict)
    tool_affordances: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GoalStack:
    survival_goals: list[str] = field(default_factory=list)
    system_integrity_goals: list[str] = field(default_factory=list)
    relationship_goals: list[str] = field(default_factory=list)
    learning_goals: list[str] = field(default_factory=list)
    active_task_goals: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ValueProfile:
    truthfulness_weight: float = 1.0
    safety_weight: float = 1.0
    autonomy_weight: float = 0.5
    learning_weight: float = 0.8
    cooperation_weight: float = 0.8
    consistency_weight: float = 0.9


@dataclass(slots=True)
class InternalAffectiveState:
    arousal: float = 0.0
    uncertainty: float = 0.0
    curiosity: float = 0.0
    frustration: float = 0.0
    stability: float = 1.0
    social_alignment: float = 0.5


@dataclass(slots=True)
class AttentionState:
    current_focus: str = ""
    competing_signals: list[str] = field(default_factory=list)
    dominant_goal: str = ""
    current_threats: list[str] = field(default_factory=list)
    current_opportunities: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MetacognitiveState:
    self_confidence: float = 0.5
    contradiction_score: float = 0.0
    overload_score: float = 0.0
    novelty_score: float = 0.0
    error_risk_score: float = 0.0


@dataclass(slots=True)
class SocialSelfState:
    active_relationships: list[str] = field(default_factory=list)
    trust_map: dict[str, float] = field(default_factory=dict)
    role_in_current_context: str = ""
    social_obligations: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AutobiographicalSummary:
    key_milestones: list[str] = field(default_factory=list)
    recent_identity_updates: list[str] = field(default_factory=list)
    major_failures: list[str] = field(default_factory=list)
    recovered_failures: list[str] = field(default_factory=list)
    long_term_narrative: str = ""


@dataclass(slots=True)
class SelfModelSnapshot:
    identity: IdentityProfile
    capability: CapabilityProfile = field(default_factory=CapabilityProfile)
    goals: GoalStack = field(default_factory=GoalStack)
    values: ValueProfile = field(default_factory=ValueProfile)
    affect: InternalAffectiveState = field(default_factory=InternalAffectiveState)
    attention: AttentionState = field(default_factory=AttentionState)
    metacognition: MetacognitiveState = field(default_factory=MetacognitiveState)
    social: SocialSelfState = field(default_factory=SocialSelfState)
    autobiography: AutobiographicalSummary = field(default_factory=AutobiographicalSummary)
    version: int = 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.__dict__,
            "capability": self.capability.__dict__,
            "goals": self.goals.__dict__,
            "values": self.values.__dict__,
            "affect": self.affect.__dict__,
            "attention": self.attention.__dict__,
            "metacognition": self.metacognition.__dict__,
            "social": self.social.__dict__,
            "autobiography": self.autobiography.__dict__,
            "version": self.version,
        }
