from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.app.schemas.tasks import ExecuteTaskRequest, ExecuteTaskResponse
from apps.api.app.services.task_execution import execute_task
from packages.infra.db.session import get_db

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/execute", response_model=ExecuteTaskResponse)
def run_task(payload: ExecuteTaskRequest, db: Session = Depends(get_db)) -> ExecuteTaskResponse:
    return execute_task(payload, db)
