from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.schemas.social import SocialRelationshipResponse, UpsertSocialRelationshipRequest
from apps.api.app.services.social import (
    get_social_relationship,
    list_social_relationships,
    upsert_social_relationship,
)
from packages.infra.db.session import get_db

router = APIRouter(prefix="/social-memory", tags=["social-memory"])


@router.get("/{agent_id}/relationships", response_model=list[SocialRelationshipResponse])
def list_social_relationships_endpoint(
    agent_id: str, db: Session = Depends(get_db)
) -> list[SocialRelationshipResponse]:
    relationships = list_social_relationships(db, agent_id)
    if relationships is None:
        raise HTTPException(status_code=404, detail="Self model not found")
    return relationships


@router.get("/{agent_id}/relationships/{counterpart_id}", response_model=SocialRelationshipResponse)
def get_social_relationship_endpoint(
    agent_id: str, counterpart_id: str, db: Session = Depends(get_db)
) -> SocialRelationshipResponse:
    relationship = get_social_relationship(db, agent_id, counterpart_id)
    if relationship is None:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return relationship


@router.post(
    "/{agent_id}/relationships",
    response_model=SocialRelationshipResponse,
    status_code=status.HTTP_201_CREATED,
)
def upsert_social_relationship_endpoint(
    agent_id: str, payload: UpsertSocialRelationshipRequest, db: Session = Depends(get_db)
) -> SocialRelationshipResponse:
    relationship = upsert_social_relationship(db, agent_id, payload)
    if relationship is None:
        raise HTTPException(status_code=404, detail="Self model not found")
    return relationship