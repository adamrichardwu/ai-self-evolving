from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.app.schemas.core_capability import (
    CoreCapabilityDatasetResponse,
    CoreCapabilityEvaluationJobResponse,
    CoreCapabilityEvaluationResponse,
    CoreCapabilityExportJobResponse,
    CoreCapabilityExportResponse,
    CoreCapabilityTrainingJobQueueResponse,
    CoreCapabilityTrainingJobResponse,
    CoreCapabilityTrainingEvaluationQueueResponse,
    CoreCapabilityTrainingEvaluationResponse,
    CreateCoreCapabilityEvaluationRequest,
    CreateCoreCapabilityDatasetRequest,
    CreateCoreCapabilityExportRequest,
    CreateCoreCapabilityTrainingJobRequest,
    CreateCoreCapabilityTrainingEvaluationRequest,
)
from apps.api.app.services.core_capability import (
    build_core_capability_dataset,
    evaluate_core_capability_export,
    evaluate_core_capability_training_run,
    export_core_capability_dataset_bundle,
    prepare_core_capability_training_job,
)
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


@router.post("/evaluate", response_model=CoreCapabilityEvaluationResponse)
def evaluate_core_capability_export_endpoint(
    payload: CreateCoreCapabilityEvaluationRequest,
) -> CoreCapabilityEvaluationResponse:
    return evaluate_core_capability_export(payload)


@router.post("/evaluate/queue", response_model=CoreCapabilityEvaluationJobResponse)
def queue_core_capability_export_evaluation_endpoint(
    payload: CreateCoreCapabilityEvaluationRequest,
) -> CoreCapabilityEvaluationJobResponse:
    try:
        task_result = celery_app.send_task(
            "core_capability.evaluate_export",
            args=[payload.model_dump()],
        )
        return CoreCapabilityEvaluationJobResponse(
            task_id=task_result.id,
            task_name="core_capability.evaluate_export",
            status="queued",
        )
    except Exception:
        result = evaluate_core_capability_export(payload)
        return CoreCapabilityEvaluationJobResponse(
            task_id=result.manifest_path,
            task_name="core_capability.evaluate_export",
            status="completed_inline",
        )


@router.post("/training-jobs", response_model=CoreCapabilityTrainingJobResponse)
def prepare_core_capability_training_job_endpoint(
    payload: CreateCoreCapabilityTrainingJobRequest,
) -> CoreCapabilityTrainingJobResponse:
    return prepare_core_capability_training_job(payload)


@router.post("/training-jobs/queue", response_model=CoreCapabilityTrainingJobQueueResponse)
def queue_core_capability_training_job_endpoint(
    payload: CreateCoreCapabilityTrainingJobRequest,
) -> CoreCapabilityTrainingJobQueueResponse:
    try:
        task_result = celery_app.send_task(
            "core_capability.prepare_training_job",
            args=[payload.model_dump()],
        )
        return CoreCapabilityTrainingJobQueueResponse(
            task_id=task_result.id,
            task_name="core_capability.prepare_training_job",
            status="queued",
        )
    except Exception:
        result = prepare_core_capability_training_job(payload)
        return CoreCapabilityTrainingJobQueueResponse(
            task_id=result.job_spec_path,
            task_name="core_capability.prepare_training_job",
            status="completed_inline",
        )


@router.post("/training-evaluations", response_model=CoreCapabilityTrainingEvaluationResponse)
def evaluate_core_capability_training_run_endpoint(
    payload: CreateCoreCapabilityTrainingEvaluationRequest,
) -> CoreCapabilityTrainingEvaluationResponse:
    return evaluate_core_capability_training_run(payload)


@router.post("/training-evaluations/queue", response_model=CoreCapabilityTrainingEvaluationQueueResponse)
def queue_core_capability_training_run_endpoint(
    payload: CreateCoreCapabilityTrainingEvaluationRequest,
) -> CoreCapabilityTrainingEvaluationQueueResponse:
    try:
        task_result = celery_app.send_task(
            "core_capability.evaluate_training_run",
            args=[payload.model_dump()],
        )
        return CoreCapabilityTrainingEvaluationQueueResponse(
            task_id=task_result.id,
            task_name="core_capability.evaluate_training_run",
            status="queued",
        )
    except Exception:
        result = evaluate_core_capability_training_run(payload)
        return CoreCapabilityTrainingEvaluationQueueResponse(
            task_id=result.evaluation_path,
            task_name="core_capability.evaluate_training_run",
            status="completed_inline",
        )