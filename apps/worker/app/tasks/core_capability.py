from packages.infra.db.session import SessionLocal

from apps.api.app.schemas.core_capability import CreateCoreCapabilityExportRequest
from apps.api.app.services.core_capability import export_core_capability_dataset_bundle
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