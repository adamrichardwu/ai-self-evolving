from pydantic import BaseModel


class TriggerAutobiographyConsolidationRequest(BaseModel):
    max_events: int = 10


class AutobiographyConsolidationResponse(BaseModel):
    id: str
    self_model_id: str
    event_count: int
    summary: str
    narrative_delta: str
