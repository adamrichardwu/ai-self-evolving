from pydantic import BaseModel, Field

from apps.api.app.schemas.goals import GoalResponse


class LanguageInputRequest(BaseModel):
    text: str = Field(min_length=1)
    counterpart_id: str = "user-primary"
    counterpart_name: str = "User"
    relationship_type: str = "user"
    observed_sentiment: str = "neutral"


class InnerThoughtResponse(BaseModel):
    id: str
    self_model_id: str
    thought_type: str
    focus: str
    content: str
    salience_score: float
    source: str


class LanguageMessageResponse(BaseModel):
    id: str
    self_model_id: str
    role: str
    content: str
    channel: str


class LanguageSummaryResponse(BaseModel):
    self_model_id: str
    summary_text: str
    message_count: int
    last_focus: str


class LLMStatusResponse(BaseModel):
    configured: bool
    reachable: bool
    mode: str
    api_base_url: str | None = None
    model: str | None = None
    detail: str = ""


class LanguageExchangeResponse(BaseModel):
    assistant_message: LanguageMessageResponse
    inner_thought: InnerThoughtResponse
    current_focus: str
    dominant_goal: str = ""
    active_goals: list[GoalResponse] = Field(default_factory=list)
    reflection_triggered: bool


class LanguageStateResponse(BaseModel):
    agent_id: str
    background_loop_enabled: bool
    summary: LanguageSummaryResponse | None = None
    dominant_goal: str = ""
    active_goals: list[GoalResponse] = Field(default_factory=list)
    messages: list[LanguageMessageResponse] = Field(default_factory=list)
    thoughts: list[InnerThoughtResponse] = Field(default_factory=list)