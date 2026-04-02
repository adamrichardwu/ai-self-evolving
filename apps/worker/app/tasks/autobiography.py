from packages.infra.db.session import SessionLocal

from apps.api.app.services.autobiography import run_autobiographical_consolidation
from apps.worker.app.celery_app import celery_app


@celery_app.task(name="autobiography.consolidate")
def run_autobiography_consolidation(agent_id: str, max_events: int = 10) -> dict[str, str | int]:
    with SessionLocal() as session:
        result = run_autobiographical_consolidation(session, agent_id, max_events=max_events)
        if result is None:
            return {"agent_id": agent_id, "status": "skipped", "event_count": 0}
        return {
            "agent_id": agent_id,
            "status": "consolidated",
            "event_count": result.event_count,
            "consolidation_id": result.id,
        }
