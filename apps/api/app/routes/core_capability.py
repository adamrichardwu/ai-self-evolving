from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.app.schemas.core_capability import (
    CoreCapabilityDatasetResponse,
    CoreCapabilityExportJobResponse,
    CoreCapabilityExportResponse,
    CreateCoreCapabilityDatasetRequest,
    CreateCoreCapabilityExportRequest,
)
from apps.api.app.services.core_capability import build_core_capability_dataset, export_core_capability_dataset_bundle
from apps.worker.app.celery_app import celery_app
from packages.infra.db.session import get_db

router = APIRouter(prefix="/core-capability", tags=["core-capability"])


@router.post("/{agent_id}/dataset", response_model=CoreCapabilityDatasetResponse)
def create_core_capability_dataset_endpoint(
    agent_id: str,
    payload: CreateCoreCapabilityDatasetRequest,
    db: Session = Depends(get_db),
) -> CoreCapabilityDatasetResponse:
    dataset = build_core_capability_dataset(db, agent_id, payload)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Self model not found")
    return dataset


@router.post("/{agent_id}/export", response_model=CoreCapabilityExportJobResponse)
def export_core_capability_dataset_endpoint(
    agent_id: str,
    payload: CreateCoreCapabilityExportRequest,
    db: Session = Depends(get_db),
) -> CoreCapabilityExportJobResponse:
    if build_core_capability_dataset(db, agent_id, payload) is None:
        raise HTTPException(status_code=404, detail="Self model not found")
    try:
        task_result = celery_app.send_task(
            "core_capability.export_dataset",
            args=[agent_id, payload.model_dump()],
        )
        return CoreCapabilityExportJobResponse(
            task_id=task_result.id,
            task_name="core_capability.export_dataset",
            status="queued",
        )
    except Exception:
        export_result = export_core_capability_dataset_bundle(db, agent_id, payload)
        if export_result is None:
            raise HTTPException(status_code=404, detail="Self model not found")
        return CoreCapabilityExportJobResponse(
            task_id=export_result.export_id,
            task_name="core_capability.export_dataset",
            status="completed_inline",
        )


@router.post("/{agent_id}/export/run", response_model=CoreCapabilityExportResponse)
def export_core_capability_dataset_inline_endpoint(
    agent_id: str,
    payload: CreateCoreCapabilityExportRequest,
    db: Session = Depends(get_db),
) -> CoreCapabilityExportResponse:
    export_result = export_core_capability_dataset_bundle(db, agent_id, payload)
    if export_result is None:
        raise HTTPException(status_code=404, detail="Self model not found")
    return export_result