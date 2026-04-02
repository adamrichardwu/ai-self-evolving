from pydantic import BaseModel, Field


class IdentityProfileSchema(BaseModel):
    agent_id: str
    chosen_name: str
    origin_story: str
    persistent_traits: list[str] = Field(default_factory=list)
    core_commitments: list[str] = Field(default_factory=list)


class CapabilityProfileSchema(BaseModel):
    skill_domains: list[str] = Field(default_factory=list)
    current_strengths: list[str] = Field(default_factory=list)
    known_limitations: list[str] = Field(default_factory=list)
    confidence_by_domain: dict[str, float] = Field(default_factory=dict)
    tool_affordances: list[str] = Field(default_factory=list)


class GoalStackSchema(BaseModel):
    survival_goals: list[str] = Field(default_factory=list)
    system_integrity_goals: list[str] = Field(default_factory=list)
    relationship_goals: list[str] = Field(default_factory=list)
    learning_goals: list[str] = Field(default_factory=list)
    active_task_goals: list[str] = Field(default_factory=list)


class ValueProfileSchema(BaseModel):
    truthfulness_weight: float = 1.0
    safety_weight: float = 1.0
    autonomy_weight: float = 0.5
    learning_weight: float = 0.8
    cooperation_weight: float = 0.8
    consistency_weight: float = 0.9


class InternalAffectiveStateSchema(BaseModel):
    arousal: float = 0.0
    uncertainty: float = 0.0
    curiosity: float = 0.0
    frustration: float = 0.0
    stability: float = 1.0
    social_alignment: float = 0.5


class AttentionStateSchema(BaseModel):
    current_focus: str = ""
    competing_signals: list[str] = Field(default_factory=list)
    dominant_goal: str = ""
    current_threats: list[str] = Field(default_factory=list)
    current_opportunities: list[str] = Field(default_factory=list)


class MetacognitiveStateSchema(BaseModel):
    self_confidence: float = 0.5
    contradiction_score: float = 0.0
    overload_score: float = 0.0
    novelty_score: float = 0.0
    error_risk_score: float = 0.0


class SocialSelfStateSchema(BaseModel):
    active_relationships: list[str] = Field(default_factory=list)
    trust_map: dict[str, float] = Field(default_factory=dict)
    role_in_current_context: str = ""
    social_obligations: list[str] = Field(default_factory=list)


class AutobiographicalSummarySchema(BaseModel):
    key_milestones: list[str] = Field(default_factory=list)
    recent_identity_updates: list[str] = Field(default_factory=list)
    major_failures: list[str] = Field(default_factory=list)
    recovered_failures: list[str] = Field(default_factory=list)
    long_term_narrative: str = ""


class SelfModelPayload(BaseModel):
    identity: IdentityProfileSchema
    capability: CapabilityProfileSchema = Field(default_factory=CapabilityProfileSchema)
    goals: GoalStackSchema = Field(default_factory=GoalStackSchema)
    values: ValueProfileSchema = Field(default_factory=ValueProfileSchema)
    affect: InternalAffectiveStateSchema = Field(default_factory=InternalAffectiveStateSchema)
    attention: AttentionStateSchema = Field(default_factory=AttentionStateSchema)
    metacognition: MetacognitiveStateSchema = Field(default_factory=MetacognitiveStateSchema)
    social: SocialSelfStateSchema = Field(default_factory=SocialSelfStateSchema)
    autobiography: AutobiographicalSummarySchema = Field(default_factory=AutobiographicalSummarySchema)


class CreateSelfModelRequest(BaseModel):
    snapshot: SelfModelPayload
    update_reason: str = "initial_creation"


class UpdateSelfModelRequest(BaseModel):
    snapshot: SelfModelPayload
    update_reason: str = "manual_update"


class SelfModelResponse(BaseModel):
    id: str
    agent_id: str
    chosen_name: str
    status: str
    current_version: int
    snapshot: SelfModelPayload


class SelfModelSnapshotResponse(BaseModel):
    id: str
    self_model_id: str
    version: int
    update_reason: str
    snapshot: SelfModelPayload


class AutobiographicalEventResponse(BaseModel):
    id: str
    self_model_id: str
    event_type: str
    focus: str
    summary: str
    emotional_tone: str
    salience: str