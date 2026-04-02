from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.app.schemas.runtime import RuntimeStateResponse, RuntimeStepRequest, RuntimeStepResponse
from apps.api.app.services.runtime import get_runtime_state, run_runtime_step
from packages.infra.db.session import get_db

router = APIRouter(prefix="/runtime", tags=["runtime"])


@router.get("/{agent_id}/state", response_model=RuntimeStateResponse)
def get_runtime_state_endpoint(agent_id: str, db: Session = Depends(get_db)) -> RuntimeStateResponse:
    state = get_runtime_state(db, agent_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Self model not found")
    return state


@router.post("/{agent_id}/step", response_model=RuntimeStepResponse)
def run_runtime_step_endpoint(
    agent_id: str,
    payload: RuntimeStepRequest,
    db: Session = Depends(get_db),
) -> RuntimeStepResponse:
    step = run_runtime_step(db, agent_id, payload)
    if step is None:
        raise HTTPException(status_code=404, detail="Self model not found")
    return step