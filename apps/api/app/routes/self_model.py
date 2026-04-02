from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.schemas.self_model import (
    AutobiographicalEventResponse,
    CreateSelfModelRequest,
    SelfModelResponse,
    SelfModelSnapshotResponse,
    UpdateSelfModelRequest,
)
from apps.api.app.services.self_model import (
    create_self_model,
    get_self_model_by_agent_id,
    list_autobiographical_events,
    list_self_model_snapshots,
    update_self_model,
)
from packages.infra.db.session import get_db

router = APIRouter(prefix="/self-models", tags=["self-models"])


@router.post("", response_model=SelfModelResponse, status_code=status.HTTP_201_CREATED)
def create_self_model_endpoint(
    payload: CreateSelfModelRequest, db: Session = Depends(get_db)
) -> SelfModelResponse:
    existing = get_self_model_by_agent_id(db, payload.snapshot.identity.agent_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Self model already exists for agent_id")
    return create_self_model(db, payload)


@router.get("/{agent_id}", response_model=SelfModelResponse)
def get_self_model_endpoint(agent_id: str, db: Session = Depends(get_db)) -> SelfModelResponse:
    model = get_self_model_by_agent_id(db, agent_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Self model not found")
    return model


@router.put("/{agent_id}", response_model=SelfModelResponse)
def update_self_model_endpoint(
    agent_id: str, payload: UpdateSelfModelRequest, db: Session = Depends(get_db)
) -> SelfModelResponse:
    model = update_self_model(db, agent_id, payload)
    if model is None:
        raise HTTPException(status_code=404, detail="Self model not found")
    return model


@router.get("/{agent_id}/snapshots", response_model=list[SelfModelSnapshotResponse])
def list_self_model_snapshots_endpoint(
    agent_id: str, db: Session = Depends(get_db)
) -> list[SelfModelSnapshotResponse]:
    return list_self_model_snapshots(db, agent_id)


@router.get("/{agent_id}/autobiography", response_model=list[AutobiographicalEventResponse])
def list_autobiographical_events_endpoint(
    agent_id: str, db: Session = Depends(get_db)
) -> list[AutobiographicalEventResponse]:
    return list_autobiographical_events(db, agent_id)