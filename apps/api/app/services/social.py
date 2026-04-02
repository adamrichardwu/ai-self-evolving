from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.schemas.social import (
    SocialInteractionContextSchema,
    SocialRelationshipResponse,
    UpsertSocialRelationshipRequest,
)
from packages.consciousness.self_model.persistence import SelfModelRecord
from packages.consciousness.social.engine import SocialMemoryEngine
from packages.consciousness.social.persistence import SocialRelationshipRecord
from packages.consciousness.social.state import SocialInteractionSignal, SocialRelationshipSnapshot


def _get_self_model_record(db: Session, agent_id: str) -> SelfModelRecord | None:
    return db.scalar(select(SelfModelRecord).where(SelfModelRecord.agent_id == agent_id))


def _to_response(record: SocialRelationshipRecord) -> SocialRelationshipResponse:
    return SocialRelationshipResponse(
        id=record.id,
        self_model_id=record.self_model_id,
        counterpart_id=record.counterpart_id,
        counterpart_name=record.counterpart_name,
        relationship_type=record.relationship_type,
        trust_score=record.trust_score,
        familiarity_score=record.familiarity_score,
        interaction_count=record.interaction_count,
        last_interaction_summary=record.last_interaction_summary,
        role_in_context=record.role_in_context,
        social_obligations=record.social_obligations_json,
    )


def _to_snapshot(record: SocialRelationshipRecord) -> SocialRelationshipSnapshot:
    return SocialRelationshipSnapshot(
        counterpart_id=record.counterpart_id,
        counterpart_name=record.counterpart_name,
        relationship_type=record.relationship_type,
        trust_score=record.trust_score,
        familiarity_score=record.familiarity_score,
        interaction_count=record.interaction_count,
        last_interaction_summary=record.last_interaction_summary,
        role_in_context=record.role_in_context,
        social_obligations=record.social_obligations_json,
    )


def _sync_self_model_social_projection(
    db: Session, self_model: SelfModelRecord, relationships: list[SocialRelationshipRecord]
) -> None:
    engine = SocialMemoryEngine()
    snapshots = [_to_snapshot(record) for record in relationships]
    previous = self_model.social_json or {}
    self_model.social_json = {
        "active_relationships": [
            engine.build_active_relationship_label(snapshot) for snapshot in snapshots
        ],
        "trust_map": {
            snapshot.counterpart_id: round(snapshot.trust_score, 3) for snapshot in snapshots
        },
        "role_in_current_context": next(
            (snapshot.role_in_context for snapshot in snapshots if snapshot.role_in_context),
            previous.get("role_in_current_context", ""),
        ),
        "social_obligations": engine.merge_obligations(
            [], [item for snapshot in snapshots for item in snapshot.social_obligations]
        ),
    }
    db.add(self_model)


def list_social_relationships(db: Session, agent_id: str) -> list[SocialRelationshipResponse] | None:
    self_model = _get_self_model_record(db, agent_id)
    if self_model is None:
        return None

    relationships = db.scalars(
        select(SocialRelationshipRecord)
        .where(SocialRelationshipRecord.self_model_id == self_model.id)
        .order_by(SocialRelationshipRecord.trust_score.desc(), SocialRelationshipRecord.updated_at.desc())
    ).all()
    return [_to_response(record) for record in relationships]


def get_social_relationship(
    db: Session, agent_id: str, counterpart_id: str
) -> SocialRelationshipResponse | None:
    self_model = _get_self_model_record(db, agent_id)
    if self_model is None:
        return None

    relationship = db.scalar(
        select(SocialRelationshipRecord).where(
            SocialRelationshipRecord.self_model_id == self_model.id,
            SocialRelationshipRecord.counterpart_id == counterpart_id,
        )
    )
    if relationship is None:
        return None
    return _to_response(relationship)


def upsert_social_relationship(
    db: Session, agent_id: str, request: UpsertSocialRelationshipRequest
) -> SocialRelationshipResponse | None:
    return record_social_interaction(db, agent_id, request.context)


def record_social_interaction(
    db: Session,
    agent_id: str,
    context: SocialInteractionContextSchema,
    fallback_summary: str = "",
) -> SocialRelationshipResponse | None:
    self_model = _get_self_model_record(db, agent_id)
    if self_model is None:
        return None

    relationship = db.scalar(
        select(SocialRelationshipRecord).where(
            SocialRelationshipRecord.self_model_id == self_model.id,
            SocialRelationshipRecord.counterpart_id == context.counterpart_id,
        )
    )

    engine = SocialMemoryEngine()
    signal = SocialInteractionSignal(
        counterpart_id=context.counterpart_id,
        counterpart_name=context.counterpart_name,
        relationship_type=context.relationship_type,
        interaction_summary=context.interaction_summary or fallback_summary,
        observed_sentiment=context.observed_sentiment,
        role_in_context=context.role_in_context,
        social_obligations=context.social_obligations,
        trust_delta=context.trust_delta,
    )

    if relationship is None:
        relationship = SocialRelationshipRecord(
            self_model_id=self_model.id,
            counterpart_id=signal.counterpart_id,
            counterpart_name=signal.counterpart_name,
            relationship_type=signal.relationship_type,
            trust_score=engine.update_trust(0.5, signal),
            familiarity_score=engine.update_familiarity(0.0, 0),
            interaction_count=1,
            last_interaction_summary=signal.interaction_summary,
            role_in_context=signal.role_in_context,
            social_obligations_json=engine.merge_obligations([], signal.social_obligations),
        )
        db.add(relationship)
        db.flush()
    else:
        relationship.counterpart_name = signal.counterpart_name or relationship.counterpart_name
        relationship.relationship_type = signal.relationship_type or relationship.relationship_type
        relationship.trust_score = engine.update_trust(relationship.trust_score, signal)
        relationship.familiarity_score = engine.update_familiarity(
            relationship.familiarity_score, relationship.interaction_count
        )
        relationship.interaction_count += 1
        relationship.last_interaction_summary = signal.interaction_summary or relationship.last_interaction_summary
        relationship.role_in_context = signal.role_in_context or relationship.role_in_context
        relationship.social_obligations_json = engine.merge_obligations(
            relationship.social_obligations_json,
            signal.social_obligations,
        )

    relationships = db.scalars(
        select(SocialRelationshipRecord).where(SocialRelationshipRecord.self_model_id == self_model.id)
    ).all()
    _sync_self_model_social_projection(db, self_model, relationships)
    db.commit()
    db.refresh(relationship)
    return _to_response(relationship)