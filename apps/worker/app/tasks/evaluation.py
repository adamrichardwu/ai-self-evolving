from apps.worker.app.celery_app import celery_app


@celery_app.task(name="evaluation.run_strategy")
def run_strategy_evaluation(variant_id: str) -> dict[str, str]:
    return {"variant_id": variant_id, "status": "queued"}
