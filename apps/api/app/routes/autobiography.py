from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.schemas.autobiography import (
    AutobiographyConsolidationResponse,
    TriggerAutobiographyConsolidationRequest,
)
from apps.api.app.services.autobiography import (
    list_autobiographical_consolidations,
    run_autobiographical_consolidation,
)
from packages.infra.db.session import get_db

router = APIRouter(prefix="/autobiography", tags=["autobiography"])


@router.post(
    "/{agent_id}/consolidate",
    response_model=AutobiographyConsolidationResponse,
    status_code=status.HTTP_201_CREATED,
)
def consolidate_autobiography_endpoint(
    agent_id: str,
    payload: TriggerAutobiographyConsolidationRequest,
    db: Session = Depends(get_db),
) -> AutobiographyConsolidationResponse:
    result = run_autobiographical_consolidation(db, agent_id, payload.max_events)
    if result is None:
        raise HTTPException(status_code=404, detail="No autobiographical events available")
    return result


@router.get("/{agent_id}/consolidations", response_model=list[AutobiographyConsolidationResponse])
def list_autobiography_consolidations_endpoint(
    agent_id: str, db: Session = Depends(get_db)
) -> list[AutobiographyConsolidationResponse]:
    return list_autobiographical_consolidations(db, agent_id)
