from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.schemas.self_model import (
    AutobiographicalEventResponse,
    CreateSelfModelRequest,
    MetacognitiveStateSchema,
    SelfModelPayload,
    SelfModelResponse,
    SelfModelSnapshotResponse,
    AttentionStateSchema,
    AutobiographicalSummarySchema,
    UpdateSelfModelRequest,
)
from packages.consciousness.self_model.persistence import (
    SelfModelRecord,
    SelfModelSnapshotRecord,
)
from packages.consciousness.autobiography.engine import AutobiographicalConsolidator
from packages.consciousness.autobiography.persistence import AutobiographicalEventRecord


def _payload_to_record_data(payload: SelfModelPayload) -> dict:
    data = payload.model_dump()
    return {
        "agent_id": data["identity"]["agent_id"],
        "chosen_name": data["identity"]["chosen_name"],
        "identity_json": data["identity"],
        "capability_json": data["capability"],
        "goals_json": data["goals"],
        "values_json": data["values"],
        "affect_json": data["affect"],
        "attention_json": data["attention"],
        "metacognition_json": data["metacognition"],
        "social_json": data["social"],
        "autobiography_json": data["autobiography"],
    }


def _record_snapshot_payload(record: SelfModelRecord) -> SelfModelPayload:
    return SelfModelPayload(
        identity=record.identity_json,
        capability=record.capability_json,
        goals=record.goals_json,
        values=record.values_json,
        affect=record.affect_json,
        attention=record.attention_json,
        metacognition=record.metacognition_json,
        social=record.social_json,
        autobiography=record.autobiography_json,
    )


def create_self_model(db: Session, request: CreateSelfModelRequest) -> SelfModelResponse:
    record = SelfModelRecord(**_payload_to_record_data(request.snapshot))
    db.add(record)
    db.flush()

    snapshot = SelfModelSnapshotRecord(
        self_model_id=record.id,
        version=record.current_version,
        snapshot_json=request.snapshot.model_dump(),
        update_reason=request.update_reason,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(record)
    return SelfModelResponse(
        id=record.id,
        agent_id=record.agent_id,
        chosen_name=record.chosen_name,
        status=record.status,
        current_version=record.current_version,
        snapshot=_record_snapshot_payload(record),
    )


def get_self_model_by_agent_id(db: Session, agent_id: str) -> SelfModelResponse | None:
    record = db.scalar(select(SelfModelRecord).where(SelfModelRecord.agent_id == agent_id))
    if record is None:
        return None
    return SelfModelResponse(
        id=record.id,
        agent_id=record.agent_id,
        chosen_name=record.chosen_name,
        status=record.status,
        current_version=record.current_version,
        snapshot=_record_snapshot_payload(record),
    )


def update_self_model(db: Session, agent_id: str, request: UpdateSelfModelRequest) -> SelfModelResponse | None:
    record = db.scalar(select(SelfModelRecord).where(SelfModelRecord.agent_id == agent_id))
    if record is None:
        return None

    update_data = _payload_to_record_data(request.snapshot)
    for key, value in update_data.items():
        setattr(record, key, value)
    record.current_version += 1

    snapshot = SelfModelSnapshotRecord(
        self_model_id=record.id,
        version=record.current_version,
        snapshot_json=request.snapshot.model_dump(),
        update_reason=request.update_reason,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(record)

    return SelfModelResponse(
        id=record.id,
        agent_id=record.agent_id,
        chosen_name=record.chosen_name,
        status=record.status,
        current_version=record.current_version,
        snapshot=_record_snapshot_payload(record),
    )


def list_self_model_snapshots(db: Session, agent_id: str) -> list[SelfModelSnapshotResponse]:
    record = db.scalar(select(SelfModelRecord).where(SelfModelRecord.agent_id == agent_id))
    if record is None:
        return []
    snapshots = db.scalars(
        select(SelfModelSnapshotRecord)
        .where(SelfModelSnapshotRecord.self_model_id == record.id)
        .order_by(SelfModelSnapshotRecord.version.desc())
    ).all()
    return [
        SelfModelSnapshotResponse(
            id=snapshot.id,
            self_model_id=snapshot.self_model_id,
            version=snapshot.version,
            update_reason=snapshot.update_reason,
            snapshot=SelfModelPayload(**snapshot.snapshot_json),
        )
        for snapshot in snapshots
    ]


def list_autobiographical_events(db: Session, agent_id: str) -> list[AutobiographicalEventResponse]:
    record = db.scalar(select(SelfModelRecord).where(SelfModelRecord.agent_id == agent_id))
    if record is None:
        return []
    events = db.scalars(
        select(AutobiographicalEventRecord)
        .where(AutobiographicalEventRecord.self_model_id == record.id)
        .order_by(AutobiographicalEventRecord.created_at.desc())
    ).all()
    return [
        AutobiographicalEventResponse(
            id=event.id,
            self_model_id=event.self_model_id,
            event_type=event.event_type,
            focus=event.focus,
            summary=event.summary,
            emotional_tone=event.emotional_tone,
            salience=event.salience,
        )
        for event in events
    ]


def apply_runtime_self_model_update(
    db: Session,
    agent_id: str,
    current_focus: str,
    metacognition: MetacognitiveStateSchema,
    task_prompt: str,
    update_reason: str = "runtime_cycle_update",
) -> SelfModelResponse | None:
    current = get_self_model_by_agent_id(db, agent_id)
    if current is None:
        return None

    consolidator = AutobiographicalConsolidator()
    event_type, event_summary, emotional_tone, salience = consolidator.build_event_summary(
        current_focus=current_focus,
        task_prompt=task_prompt,
        metacognition=metacognition,
    )

    snapshot = current.snapshot.model_copy(deep=True)
    snapshot.attention = AttentionStateSchema(
        current_focus=current_focus,
        competing_signals=snapshot.attention.competing_signals,
        dominant_goal=snapshot.attention.dominant_goal,
        current_threats=snapshot.attention.current_threats,
        current_opportunities=snapshot.attention.current_opportunities,
    )
    snapshot.metacognition = metacognition
    snapshot.autobiography = consolidator.consolidate(
        current_summary=snapshot.autobiography,
        current_focus=current_focus or task_prompt[:48],
        event_summary=event_summary,
        metacognition=metacognition,
    )

    updated = update_self_model(
        db,
        agent_id,
        UpdateSelfModelRequest(snapshot=snapshot, update_reason=update_reason),
    )
    if updated is None:
        return None

    record = db.scalar(select(SelfModelRecord).where(SelfModelRecord.agent_id == agent_id))
    if record is not None:
        event = AutobiographicalEventRecord(
            self_model_id=record.id,
            event_type=event_type,
            focus=current_focus or task_prompt[:48],
            summary=event_summary,
            emotional_tone=emotional_tone,
            salience=salience,
        )
        db.add(event)
        db.commit()

    return updated