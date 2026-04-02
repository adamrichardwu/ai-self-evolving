from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from apps.api.app.schemas.goals import GoalCheckpointCreateRequest, GoalCheckpointResponse, GoalResponse, GoalsRefreshResponse
from apps.api.app.services.goals import create_goal_checkpoint, list_goals, refresh_goals
from packages.infra.db.session import get_db

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("/{agent_id}", response_model=list[GoalResponse])
def list_goals_endpoint(
    agent_id: str,
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[GoalResponse]:
    goals = list_goals(db, agent_id, active_only=active_only)
    if goals is None:
        raise HTTPException(status_code=404, detail="Self model not found")
    return goals


@router.post("/{agent_id}/refresh", response_model=GoalsRefreshResponse, status_code=status.HTTP_201_CREATED)
def refresh_goals_endpoint(agent_id: str, db: Session = Depends(get_db)) -> GoalsRefreshResponse:
    response = refresh_goals(db, agent_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Self model not found")
    return response


@router.post(
    "/{agent_id}/{goal_id}/checkpoints",
    response_model=GoalCheckpointResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_goal_checkpoint_endpoint(
    agent_id: str,
    goal_id: str,
    payload: GoalCheckpointCreateRequest,
    db: Session = Depends(get_db),
) -> GoalCheckpointResponse:
    checkpoint = create_goal_checkpoint(db, agent_id, goal_id, payload)
    if checkpoint is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    return checkpoint