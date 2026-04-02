from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.schemas.autobiography import AutobiographyConsolidationResponse
from apps.api.app.schemas.self_model import UpdateSelfModelRequest
from packages.consciousness.autobiography.consolidation_persistence import AutobiographicalConsolidationRecord
from packages.consciousness.autobiography.engine import AutobiographicalConsolidator
from packages.consciousness.autobiography.persistence import AutobiographicalEventRecord
from packages.consciousness.self_model.persistence import SelfModelRecord


def _extract_themes(events: list[AutobiographicalEventRecord]) -> list[str]:
    tokens: list[str] = []
    for event in events:
        tokens.extend(word.strip(".,:'\"").lower() for word in event.focus.split())
    filtered = [token for token in tokens if len(token) > 4]
    return [token for token, _count in Counter(filtered).most_common(5)]


def run_autobiographical_consolidation(
    db: Session, agent_id: str, max_events: int = 10
) -> AutobiographyConsolidationResponse | None:
    self_model = db.scalar(select(SelfModelRecord).where(SelfModelRecord.agent_id == agent_id))
    if self_model is None:
        return None

    events = db.scalars(
        select(AutobiographicalEventRecord)
        .where(AutobiographicalEventRecord.self_model_id == self_model.id)
        .order_by(AutobiographicalEventRecord.created_at.desc())
        .limit(max_events)
    ).all()
    if not events:
        return None

    current_summary = UpdateSelfModelRequest(
        snapshot={
            "identity": self_model.identity_json,
            "capability": self_model.capability_json,
            "goals": self_model.goals_json,
            "values": self_model.values_json,
            "affect": self_model.affect_json,
            "attention": self_model.attention_json,
            "metacognition": self_model.metacognition_json,
            "social": self_model.social_json,
            "autobiography": self_model.autobiography_json,
        }
    ).snapshot.autobiography

    consolidator = AutobiographicalConsolidator()
    updated_summary, compressed_summary, narrative_delta = consolidator.consolidate_event_batch(
        current_summary=current_summary,
        event_summaries=[event.summary for event in reversed(events)],
        dominant_themes=_extract_themes(events),
    )

    self_model.autobiography_json = updated_summary.model_dump()
    self_model.current_version += 1

    consolidation = AutobiographicalConsolidationRecord(
        self_model_id=self_model.id,
        event_count=len(events),
        summary=compressed_summary,
        narrative_delta=narrative_delta,
    )
    db.add(consolidation)
    db.commit()
    db.refresh(consolidation)

    return AutobiographyConsolidationResponse(
        id=consolidation.id,
        self_model_id=consolidation.self_model_id,
        event_count=consolidation.event_count,
        summary=consolidation.summary,
        narrative_delta=consolidation.narrative_delta,
    )


def list_autobiographical_consolidations(
    db: Session, agent_id: str
) -> list[AutobiographyConsolidationResponse]:
    self_model = db.scalar(select(SelfModelRecord).where(SelfModelRecord.agent_id == agent_id))
    if self_model is None:
        return []
    runs = db.scalars(
        select(AutobiographicalConsolidationRecord)
        .where(AutobiographicalConsolidationRecord.self_model_id == self_model.id)
        .order_by(AutobiographicalConsolidationRecord.created_at.desc())
    ).all()
    return [
        AutobiographyConsolidationResponse(
            id=run.id,
            self_model_id=run.self_model_id,
            event_count=run.event_count,
            summary=run.summary,
            narrative_delta=run.narrative_delta,
        )
        for run in runs
    ]
