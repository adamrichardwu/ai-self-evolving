from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.schemas.goals import GoalCheckpointCreateRequest, GoalCheckpointResponse, GoalResponse, GoalsRefreshResponse
from apps.api.app.schemas.self_model import SelfModelPayload
from packages.consciousness.goals.engine import GoalEngine
from packages.consciousness.goals.persistence import GoalCheckpointRecord, GoalRecord
from packages.consciousness.language.persistence import LanguageSummaryRecord
from packages.consciousness.self_model.persistence import SelfModelRecord


def _get_self_model_record(db: Session, agent_id: str) -> SelfModelRecord | None:
    return db.scalar(select(SelfModelRecord).where(SelfModelRecord.agent_id == agent_id))


def _snapshot_from_record(record: SelfModelRecord) -> SelfModelPayload:
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


def _to_goal_response(record: GoalRecord) -> GoalResponse:
    return GoalResponse(
        id=record.id,
        self_model_id=record.self_model_id,
        origin_key=record.origin_key,
        title=record.title,
        description=record.description,
        goal_type=record.goal_type,
        priority=record.priority,
        status=record.status,
        time_horizon=record.time_horizon,
        origin=record.origin,
        success_criteria=record.success_criteria,
        progress_score=record.progress_score,
    )


def _to_checkpoint_response(record: GoalCheckpointRecord) -> GoalCheckpointResponse:
    return GoalCheckpointResponse(
        id=record.id,
        goal_id=record.goal_id,
        event_type=record.event_type,
        summary=record.summary,
        score_delta=record.score_delta,
    )


def _sync_self_model_goals_projection(
    db: Session,
    self_model: SelfModelRecord,
    goals: list[GoalRecord],
) -> None:
    active_goals = [goal for goal in goals if goal.status == "active"]
    previous_goals = self_model.goals_json or {}
    active_titles = [goal.title for goal in active_goals[:5]]
    self_model.goals_json = {
        "survival_goals": previous_goals.get("survival_goals", []),
        "system_integrity_goals": [goal.title for goal in active_goals if goal.goal_type == "system_integrity"],
        "relationship_goals": [goal.title for goal in active_goals if goal.goal_type == "relationship"],
        "learning_goals": [goal.title for goal in active_goals if goal.goal_type == "learning"],
        "active_task_goals": [goal.title for goal in active_goals if goal.goal_type == "active_task"] or active_titles,
    }
    attention = dict(self_model.attention_json or {})
    if active_titles:
        attention["dominant_goal"] = active_titles[0]
    self_model.attention_json = attention
    db.add(self_model)


def list_goals(db: Session, agent_id: str, active_only: bool = False) -> list[GoalResponse] | None:
    self_model = _get_self_model_record(db, agent_id)
    if self_model is None:
        return None

    query = select(GoalRecord).where(GoalRecord.self_model_id == self_model.id)
    if active_only:
        query = query.where(GoalRecord.status == "active")
    goals = db.scalars(query.order_by(GoalRecord.priority.desc(), GoalRecord.updated_at.desc())).all()
    return [_to_goal_response(goal) for goal in goals]


def refresh_goals(db: Session, agent_id: str) -> GoalsRefreshResponse | None:
    self_model = _get_self_model_record(db, agent_id)
    if self_model is None:
        return None

    summary = db.scalar(
        select(LanguageSummaryRecord).where(LanguageSummaryRecord.self_model_id == self_model.id)
    )
    engine = GoalEngine()
    drafts = engine.build_goal_drafts(
        snapshot=_snapshot_from_record(self_model),
        summary_text=summary.summary_text if summary is not None else "",
    )
    existing_goals = db.scalars(
        select(GoalRecord).where(GoalRecord.self_model_id == self_model.id)
    ).all()
    existing_by_origin = {goal.origin_key: goal for goal in existing_goals}
    active_origin_keys = {draft.origin_key for draft in drafts}
    now = datetime.now(timezone.utc)

    for draft in drafts:
        existing = existing_by_origin.get(draft.origin_key)
        if existing is None:
            db.add(
                GoalRecord(
                    self_model_id=self_model.id,
                    origin_key=draft.origin_key,
                    title=draft.title,
                    description=draft.description,
                    goal_type=draft.goal_type,
                    priority=draft.priority,
                    status="active",
                    time_horizon=draft.time_horizon,
                    origin=draft.origin,
                    success_criteria=draft.success_criteria,
                    progress_score=0.0,
                    last_evaluated_at=now,
                )
            )
            continue

        existing.title = draft.title
        existing.description = draft.description
        existing.goal_type = draft.goal_type
        existing.priority = draft.priority
        existing.time_horizon = draft.time_horizon
        existing.origin = draft.origin
        existing.success_criteria = draft.success_criteria
        existing.status = "active" if existing.status != "completed" else existing.status
        existing.last_evaluated_at = now
        db.add(existing)

    for goal in existing_goals:
        if goal.origin_key not in active_origin_keys and goal.status == "active":
            goal.status = "paused"
            goal.last_evaluated_at = now
            db.add(goal)

    db.flush()
    goals = db.scalars(
        select(GoalRecord)
        .where(GoalRecord.self_model_id == self_model.id)
        .order_by(GoalRecord.priority.desc(), GoalRecord.updated_at.desc())
    ).all()
    _sync_self_model_goals_projection(db, self_model, goals)
    db.commit()
    return GoalsRefreshResponse(
        agent_id=agent_id,
        dominant_goal=(next((goal.title for goal in goals if goal.status == "active"), "")),
        goals=[_to_goal_response(goal) for goal in goals],
    )


def create_goal_checkpoint(
    db: Session,
    agent_id: str,
    goal_id: str,
    request: GoalCheckpointCreateRequest,
) -> GoalCheckpointResponse | None:
    self_model = _get_self_model_record(db, agent_id)
    if self_model is None:
        return None

    goal = db.scalar(
        select(GoalRecord).where(GoalRecord.self_model_id == self_model.id, GoalRecord.id == goal_id)
    )
    if goal is None:
        return None

    checkpoint = GoalCheckpointRecord(
        goal_id=goal.id,
        event_type=request.event_type,
        summary=request.summary,
        score_delta=request.score_delta,
    )
    goal.progress_score = request.progress_score if request.progress_score is not None else max(
        0.0, min(1.0, goal.progress_score + request.score_delta)
    )
    if request.status is not None:
        goal.status = request.status
    if goal.status == "completed" and request.progress_score is None:
        goal.progress_score = 1.0
    goal.last_evaluated_at = datetime.now(timezone.utc)
    db.add(goal)
    db.add(checkpoint)
    db.flush()

    goals = db.scalars(
        select(GoalRecord)
        .where(GoalRecord.self_model_id == self_model.id)
        .order_by(GoalRecord.priority.desc(), GoalRecord.updated_at.desc())
    ).all()
    _sync_self_model_goals_projection(db, self_model, goals)
    db.commit()
    db.refresh(checkpoint)
    return _to_checkpoint_response(checkpoint)