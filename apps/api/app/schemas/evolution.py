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


class EvolutionBenchmarkResultResponse(BaseModel):
    name: str
    prompt: str
    baseline_passed: bool
    baseline_score: float
    candidate_passed: bool
    candidate_score: float
    rationale: str


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
    benchmark_score: float = 0.0
    baseline_benchmark_score: float = 0.0
    utility_score: float = 0.0
    verdict: str = "needs_review"
    hypothesis_title: str
    hypothesis_description: str
    active_policy: dict = Field(default_factory=dict)
    mutations: list[EvolutionMutationResponse] = Field(default_factory=list)
    benchmark_results: list[EvolutionBenchmarkResultResponse] = Field(default_factory=list)
    evaluator_notes: str = ""