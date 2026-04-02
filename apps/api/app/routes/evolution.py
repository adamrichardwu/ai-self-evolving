from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.schemas.evolution import CreateEvolutionRunRequest, EvolutionRunResponse
from apps.api.app.services.evolution import create_evolution_run, list_evolution_runs
from packages.infra.db.session import get_db

router = APIRouter(prefix="/self-evolution", tags=["self-evolution"])


@router.post("/{agent_id}/run", response_model=EvolutionRunResponse, status_code=status.HTTP_201_CREATED)
def create_evolution_run_endpoint(
    agent_id: str,
    payload: CreateEvolutionRunRequest,
    db: Session = Depends(get_db),
) -> EvolutionRunResponse:
    run = create_evolution_run(db, agent_id, payload)
    if run is None:
        raise HTTPException(status_code=404, detail="Self model not found")
    return run


@router.get("/{agent_id}", response_model=list[EvolutionRunResponse])
def list_evolution_runs_endpoint(agent_id: str, db: Session = Depends(get_db)) -> list[EvolutionRunResponse]:
    return list_evolution_runs(db, agent_id)