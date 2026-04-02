from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.schemas.consciousness_evaluation import (
    ConsciousnessEvaluationResponse,
    CreateConsciousnessEvaluationRequest,
)
from apps.api.app.services.consciousness_evaluation import (
    create_consciousness_evaluation,
    list_consciousness_evaluations,
)
from packages.infra.db.session import get_db

router = APIRouter(prefix="/consciousness-evaluations", tags=["consciousness-evaluations"])


@router.post("", response_model=ConsciousnessEvaluationResponse, status_code=status.HTTP_201_CREATED)
def create_consciousness_evaluation_endpoint(
    payload: CreateConsciousnessEvaluationRequest, db: Session = Depends(get_db)
) -> ConsciousnessEvaluationResponse:
    evaluation = create_consciousness_evaluation(db, payload)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Self model not found")
    return evaluation


@router.get("/{agent_id}", response_model=list[ConsciousnessEvaluationResponse])
def list_consciousness_evaluations_endpoint(
    agent_id: str, db: Session = Depends(get_db)
) -> list[ConsciousnessEvaluationResponse]:
    return list_consciousness_evaluations(db, agent_id)