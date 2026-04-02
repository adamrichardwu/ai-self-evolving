from pydantic import BaseModel


class CreateConsciousnessEvaluationRequest(BaseModel):
    agent_id: str
    evaluation_type: str = "baseline"
    evaluator_notes: str = ""


class ConsciousnessEvaluationResponse(BaseModel):
    id: str
    self_model_id: str
    evaluation_type: str
    self_consistency: float
    identity_continuity: float
    metacognitive_accuracy: float
    motivational_stability: float
    social_modeling: float
    reflective_recovery: float
    overall_score: float
    evaluator_notes: str
