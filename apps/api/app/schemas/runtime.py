from pydantic import BaseModel, Field

from apps.api.app.schemas.goals import GoalResponse
from apps.api.app.schemas.language import InnerThoughtResponse


class RuntimeStepRequest(BaseModel):
    user_text: str = ""
    counterpart_id: str = "user-primary"
    counterpart_name: str = "User"
    relationship_type: str = "user"
    observed_sentiment: str = "neutral"
    mode: str = "auto"


class RuntimeStateResponse(BaseModel):
    agent_id: str
    chosen_name: str
    current_focus: str
    dominant_goal: str
    active_goals: list[GoalResponse] = Field(default_factory=list)
    summary_text: str = ""
    latest_thought: InnerThoughtResponse | None = None
    last_assistant_message: str = ""


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