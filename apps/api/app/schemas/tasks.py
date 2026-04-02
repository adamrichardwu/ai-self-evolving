from pydantic import BaseModel, Field

from apps.api.app.schemas.social import SocialInteractionContextSchema


class ExecuteTaskInput(BaseModel):
    prompt: str = Field(min_length=1)


class ExecuteTaskRequest(BaseModel):
    task_type: str
    input: ExecuteTaskInput
    strategy_version: str
    model_profile: str
    agent_id: str | None = None
    context_policy: str = "default"
    social_context: SocialInteractionContextSchema | None = None


class ExecuteTaskMetrics(BaseModel):
    latency_ms: int
    token_input: int
    token_output: int


class ExecuteTaskOutput(BaseModel):
    text: str


class WorkspaceSummary(BaseModel):
    dominant_focus: str
    active_broadcast_items: list[str]
    suppressed_items: list[str]
    attention_shift_reason: str
    cycle_confidence: float


class MetacognitiveAlertSchema(BaseModel):
    kind: str
    message: str
    severity: float


class MetacognitiveSummarySchema(BaseModel):
    self_confidence: float
    contradiction_score: float
    overload_score: float
    novelty_score: float
    error_risk_score: float
    alerts: list[MetacognitiveAlertSchema]


class ReflectionSummary(BaseModel):
    triggered: bool
    reason: str
    action: str
    revised_focus: str
    guidance: str


class ExecuteTaskResponse(BaseModel):
    task_run_id: str
    status: str
    output: ExecuteTaskOutput
    metrics: ExecuteTaskMetrics
    workspace: WorkspaceSummary
    metacognition: MetacognitiveSummarySchema
    reflection: ReflectionSummary
