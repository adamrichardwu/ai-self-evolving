from pydantic import BaseModel, Field


class GoalResponse(BaseModel):
    id: str
    self_model_id: str
    origin_key: str
    title: str
    description: str
    goal_type: str
    priority: float
    status: str
    time_horizon: str
    origin: str
    success_criteria: str
    progress_score: float


class GoalCheckpointCreateRequest(BaseModel):
    event_type: str = "progress_update"
    summary: str = Field(min_length=1)
    score_delta: float = 0.0
    status: str | None = None
    progress_score: float | None = None


class GoalCheckpointResponse(BaseModel):
    id: str
    goal_id: str
    event_type: str
    summary: str
    score_delta: float


class GoalsRefreshResponse(BaseModel):
    agent_id: str
    dominant_goal: str
    goals: list[GoalResponse] = Field(default_factory=list)