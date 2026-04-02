from pydantic import BaseModel, Field


class SocialInteractionContextSchema(BaseModel):
    counterpart_id: str = Field(min_length=1)
    counterpart_name: str = ""
    relationship_type: str = "user"
    interaction_summary: str = ""
    observed_sentiment: str = "neutral"
    role_in_context: str = ""
    social_obligations: list[str] = Field(default_factory=list)
    trust_delta: float | None = None


class UpsertSocialRelationshipRequest(BaseModel):
    context: SocialInteractionContextSchema


class SocialRelationshipResponse(BaseModel):
    id: str
    self_model_id: str
    counterpart_id: str
    counterpart_name: str
    relationship_type: str
    trust_score: float
    familiarity_score: float
    interaction_count: int
    last_interaction_summary: str
    role_in_context: str
    social_obligations: list[str] = Field(default_factory=list)