from pydantic import BaseModel, Field

from apps.api.app.schemas.goals import GoalResponse
from apps.api.app.schemas.language import InnerThoughtResponse


class RuntimeStepRequest(BaseModel):
    user_text: str = ""
    counterpart_id: str = "user-primary"
    counterpart_name: str = "User"
    relationship_type: str = "user"
    counterpart_role: str = "dialogue_partner"
    observed_sentiment: str = "neutral"
    mode: str = "auto"


class IdentityContextResponse(BaseModel):
    self_name: str
    self_origin_story: str = ""
    self_commitments: list[str] = Field(default_factory=list)
    self_narrative: str = ""
    counterpart_name: str = ""
    counterpart_role: str = ""
    relationship_type: str = ""
    relationship_summary: str = ""
    social_obligations: list[str] = Field(default_factory=list)
    trust_score: float | None = None
    identity_status: str = "unanchored"


class RuntimeTraceResponse(BaseModel):
    id: str
    action_taken: str
    current_focus: str
    dominant_goal: str
    identity_status: str
    counterpart_name: str
    relationship_type: str
    summary_text: str
    assistant_text: str
    thought_focus: str
    cycle_confidence: float


class RuntimeStateResponse(BaseModel):
    agent_id: str
    chosen_name: str
    current_focus: str
    dominant_goal: str
    active_goals: list[GoalResponse] = Field(default_factory=list)
    summary_text: str = ""
    latest_thought: InnerThoughtResponse | None = None
    last_assistant_message: str = ""
    identity_context: IdentityContextResponse
    recent_traces: list[RuntimeTraceResponse] = Field(default_factory=list)


class RuntimeStepResponse(BaseModel):
    agent_id: str
    action_taken: str
    current_focus: str
    dominant_goal: str
    active_goals: list[GoalResponse] = Field(default_factory=list)
    summary_text: str = ""
    assistant_text: str = ""
    reflection_triggered: bool = False
    thought: InnerThoughtResponse | None = None
    identity_context: IdentityContextResponse
    trace: RuntimeTraceResponse | None = None