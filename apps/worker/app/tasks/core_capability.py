from packages.infra.db.session import SessionLocal

from apps.api.app.schemas.core_capability import (
    CreateCoreCapabilityEvaluationRequest,
    CreateCoreCapabilityExportRequest,
    CreateCoreCapabilityTrainingJobRequest,
    CreateCoreCapabilityTrainingEvaluationRequest,
)
from apps.api.app.services.core_capability import (
    evaluate_core_capability_export,
    evaluate_core_capability_training_run,
    export_core_capability_dataset_bundle,
    prepare_core_capability_training_job,
)
from apps.worker.app.celery_app import celery_app


@celery_app.task(name="core_capability.export_dataset")
def export_core_capability_dataset_task(agent_id: str, payload: dict | None = None) -> dict[str, str | int]:
    request = CreateCoreCapabilityExportRequest(**(payload or {}))
    with SessionLocal() as session:
        result = export_core_capability_dataset_bundle(session, agent_id, request)
        if result is None:
            return {"agent_id": agent_id, "status": "skipped", "export_id": ""}
        return {
            "agent_id": agent_id,
            "status": result.status,
            "export_id": result.export_id,
            "bundle_dir": result.bundle_dir,
            "manifest_path": result.manifest_path,
            "sft_dataset_path": result.sft_dataset_path,
            "preference_dataset_path": result.preference_dataset_path,
            "sft_example_count": result.sft_example_count,
            "preference_example_count": result.preference_example_count,
        }


@celery_app.task(name="core_capability.evaluate_export")
def evaluate_core_capability_export_task(payload: dict | None = None) -> dict[str, str | int | float | list[str]]:
    request = CreateCoreCapabilityEvaluationRequest(**(payload or {}))
    result = evaluate_core_capability_export(request)
    return {
        "status": result.status,
        "verdict": result.verdict,
        "manifest_path": result.manifest_path,
        "sft_example_count": result.sft_example_count,
        "preference_example_count": result.preference_example_count,
        "dialogue_example_count": result.dialogue_example_count,
        "capability_coverage": result.capability_coverage,
        "average_prompt_length": result.average_prompt_length,
        "average_response_length": result.average_response_length,
        "warnings": result.warnings,
    }


@celery_app.task(name="core_capability.prepare_training_job")
def prepare_core_capability_training_job_task(payload: dict | None = None) -> dict[str, str | list[dict]]:
    request = CreateCoreCapabilityTrainingJobRequest(**(payload or {}))
    result = prepare_core_capability_training_job(request)
    return {
        "status": result.status,
        "manifest_path": result.manifest_path,
        "job_spec_path": result.job_spec_path,
        "base_model": result.base_model,
        "mode": result.mode,
        "stages": result.stages,
    }


@celery_app.task(name="core_capability.evaluate_training_run")
def evaluate_core_capability_training_run_task(payload: dict | None = None) -> dict[str, str | float]:
    request = CreateCoreCapabilityTrainingEvaluationRequest(**(payload or {}))
    result = evaluate_core_capability_training_run(request)
    return {
        "status": result.status,
        "run_manifest_path": result.run_manifest_path,
        "evaluation_path": result.evaluation_path,
        "baseline_model_path": result.baseline_model_path,
        "candidate_model_path": result.candidate_model_path,
        "sft_loss_baseline": result.sft_loss_baseline,
        "sft_loss_candidate": result.sft_loss_candidate,
        "preference_margin_baseline": result.preference_margin_baseline,
        "preference_margin_candidate": result.preference_margin_candidate,
        "overall_delta": result.overall_delta,
        "verdict": result.verdict,
    }