from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from apps.api.app.schemas.language import (
    InnerThoughtResponse,
    LanguageExchangeResponse,
    LanguageInputRequest,
    LanguageStateResponse,
)
from apps.api.app.services.language import get_language_state, run_language_thought_cycle, send_language_message
from packages.infra.db.session import get_db

router = APIRouter(prefix="/language", tags=["language"])


@router.post("/{agent_id}/messages", response_model=LanguageExchangeResponse)
def send_language_message_endpoint(
    agent_id: str, payload: LanguageInputRequest, db: Session = Depends(get_db)
) -> LanguageExchangeResponse:
    response = send_language_message(db, agent_id, payload)
    if response is None:
        raise HTTPException(status_code=404, detail="Self model not found")
    return response


@router.post(
    "/{agent_id}/think",
    response_model=InnerThoughtResponse,
    status_code=status.HTTP_201_CREATED,
)
def run_language_think_cycle_endpoint(
    agent_id: str, db: Session = Depends(get_db)
) -> InnerThoughtResponse:
    thought = run_language_thought_cycle(db, agent_id, thought_type="manual_cycle", source="manual")
    if thought is None:
        raise HTTPException(status_code=404, detail="Self model not found")
    return thought


@router.get("/{agent_id}/state", response_model=LanguageStateResponse)
def get_language_state_endpoint(
    agent_id: str,
    message_limit: int = Query(default=12, ge=1, le=50),
    thought_limit: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
) -> LanguageStateResponse:
    state = get_language_state(db, agent_id, message_limit=message_limit, thought_limit=thought_limit)
    if state is None:
        raise HTTPException(status_code=404, detail="Self model not found")
    return state