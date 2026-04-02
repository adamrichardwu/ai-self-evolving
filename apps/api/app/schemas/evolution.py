from pydantic import BaseModel, Field


class CreateEvolutionRunRequest(BaseModel):
    objective: str = "improve self-consistency and adaptive behavior"
    evaluator_notes: str = ""


class EvolutionMutationResponse(BaseModel):
    mutation_type: str
    title: str
    description: str
    expected_gain: float
    risk_level: str


class EvolutionRunResponse(BaseModel):
    id: str
    self_model_id: str
    version: int
    objective: str
    strategy_status: str
    promoted: bool
    rollback_required: bool
    baseline_overall_score: float
    candidate_overall_score: float
    score_delta: float
    hypothesis_title: str
    hypothesis_description: str
    active_policy: dict = Field(default_factory=dict)
    mutations: list[EvolutionMutationResponse] = Field(default_factory=list)
    evaluator_notes: str = ""