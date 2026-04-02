from sqlalchemy.orm import Session

from apps.api.app.schemas.language import LanguageInputRequest
from apps.api.app.schemas.runtime import IdentityContextResponse, RuntimeStateResponse, RuntimeStepRequest, RuntimeStepResponse, RuntimeTraceResponse
from apps.api.app.services.goals import refresh_goals
from apps.api.app.services.language import derive_identity_status, get_language_state, run_language_thought_cycle, send_language_message
from apps.api.app.services.self_model import get_self_model_by_agent_id
from apps.api.app.services.social import get_social_relationship
from packages.consciousness.runtime.persistence import RuntimeTraceRecord


def _to_trace_response(record: RuntimeTraceRecord) -> RuntimeTraceResponse:
    return RuntimeTraceResponse(
        id=record.id,
        action_taken=record.action_taken,
        current_focus=record.current_focus,
        dominant_goal=record.dominant_goal,
        identity_status=record.identity_status,
        counterpart_name=record.counterpart_name,
        relationship_type=record.relationship_type,
        summary_text=record.summary_text,
        assistant_text=record.assistant_text,
        thought_focus=record.thought_focus,
        cycle_confidence=record.cycle_confidence,
    )


def _list_recent_traces(db: Session, self_model_id: str, limit: int = 8) -> list[RuntimeTraceResponse]:
    traces = (
        db.query(RuntimeTraceRecord)
        .filter(RuntimeTraceRecord.self_model_id == self_model_id)
        .order_by(RuntimeTraceRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_to_trace_response(trace) for trace in traces]


def _persist_runtime_trace(
    db: Session,
    self_model_id: str,
    action_taken: str,
    current_focus: str,
    dominant_goal: str,
    identity_status: str,
    counterpart_name: str,
    relationship_type: str,
    summary_text: str,
    assistant_text: str,
    thought_focus: str,
    cycle_confidence: float,
) -> RuntimeTraceResponse:
    record = RuntimeTraceRecord(
        self_model_id=self_model_id,
        action_taken=action_taken,
        current_focus=current_focus,
        dominant_goal=dominant_goal,
        identity_status=identity_status,
        counterpart_name=counterpart_name,
        relationship_type=relationship_type,
        summary_text=summary_text,
        assistant_text=assistant_text,
        thought_focus=thought_focus,
        cycle_confidence=cycle_confidence,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_trace_response(record)


def _build_identity_context(db: Session, agent_id: str) -> IdentityContextResponse | None:
    self_model = get_self_model_by_agent_id(db, agent_id)
    if self_model is None:
        return None

    relationship = get_social_relationship(db, agent_id, "user-primary")
    obligations = relationship.social_obligations if relationship is not None else self_model.snapshot.social.social_obligations
    relationship_summary = relationship.last_interaction_summary if relationship is not None else ""
    counterpart_name = relationship.counterpart_name if relationship is not None else ""
    counterpart_role = relationship.role_in_context if relationship is not None else self_model.snapshot.social.role_in_current_context
    relationship_type = relationship.relationship_type if relationship is not None else ""

    identity_status = derive_identity_status(
        self_model.snapshot.identity.chosen_name,
        counterpart_name,
        relationship_type,
        self_model.snapshot.autobiography.long_term_narrative,
        relationship_summary,
    )

    return IdentityContextResponse(
        self_name=self_model.snapshot.identity.chosen_name,
        self_origin_story=self_model.snapshot.identity.origin_story,
        self_commitments=self_model.snapshot.identity.core_commitments,
        self_narrative=self_model.snapshot.autobiography.long_term_narrative,
        counterpart_name=counterpart_name,
        counterpart_role=counterpart_role,
        relationship_type=relationship_type,
        relationship_summary=relationship_summary,
        social_obligations=obligations,
        trust_score=relationship.trust_score if relationship is not None else None,
        identity_status=identity_status,
    )


def get_runtime_state(db: Session, agent_id: str) -> RuntimeStateResponse | None:
    self_model = get_self_model_by_agent_id(db, agent_id)
    language_state = get_language_state(db, agent_id)
    identity_context = _build_identity_context(db, agent_id)
    if self_model is None or language_state is None or identity_context is None:
        return None

    latest_thought = language_state.thoughts[-1] if language_state.thoughts else None
    last_assistant_message = next(
        (message.content for message in reversed(language_state.messages) if message.role == "assistant"),
        "",
    )
    return RuntimeStateResponse(
        agent_id=agent_id,
        chosen_name=self_model.snapshot.identity.chosen_name,
        current_focus=self_model.snapshot.attention.current_focus,
        dominant_goal=language_state.dominant_goal,
        active_goals=language_state.active_goals,
        summary_text=language_state.summary.summary_text if language_state.summary is not None else "",
        latest_thought=latest_thought,
        last_assistant_message=last_assistant_message,
        identity_context=identity_context,
        recent_traces=_list_recent_traces(db, self_model.id),
    )


def run_runtime_step(db: Session, agent_id: str, request: RuntimeStepRequest) -> RuntimeStepResponse | None:
    self_model = get_self_model_by_agent_id(db, agent_id)
    if self_model is None:
        return None

    normalized_text = request.user_text.strip()
    if normalized_text:
        exchange = send_language_message(
            db,
            agent_id,
            LanguageInputRequest(
                text=normalized_text,
                counterpart_id=request.counterpart_id,
                counterpart_name=request.counterpart_name,
                relationship_type=request.relationship_type,
                counterpart_role=request.counterpart_role,
                observed_sentiment=request.observed_sentiment,
            ),
        )
        if exchange is None:
            return None
        state = get_runtime_state(db, agent_id)
        if state is None:
            return None
        return RuntimeStepResponse(
            agent_id=agent_id,
            action_taken="language_reply",
            current_focus=exchange.current_focus,
            dominant_goal=exchange.dominant_goal,
            active_goals=exchange.active_goals,
            summary_text=state.summary_text,
            assistant_text=exchange.assistant_message.content,
            reflection_triggered=exchange.reflection_triggered,
            thought=exchange.inner_thought,
            identity_context=state.identity_context,
            trace=_persist_runtime_trace(
                db,
                self_model.id,
                "language_reply",
                exchange.current_focus,
                exchange.dominant_goal,
                state.identity_context.identity_status,
                state.identity_context.counterpart_name,
                state.identity_context.relationship_type,
                state.summary_text,
                exchange.assistant_message.content,
                exchange.inner_thought.focus,
                exchange.inner_thought.salience_score,
            ),
        )

    thought = run_language_thought_cycle(db, agent_id, thought_type="runtime_cycle", source="runtime")
    if thought is None:
        return None
    refresh_goals(db, agent_id)
    state = get_runtime_state(db, agent_id)
    if state is None:
        return None
    return RuntimeStepResponse(
        agent_id=agent_id,
        action_taken="background_thought",
        current_focus=state.current_focus,
        dominant_goal=state.dominant_goal,
        active_goals=state.active_goals,
        summary_text=state.summary_text,
        assistant_text="",
        reflection_triggered=False,
        thought=thought,
        identity_context=state.identity_context,
        trace=_persist_runtime_trace(
            db,
            self_model.id,
            "background_thought",
            state.current_focus,
            state.dominant_goal,
            state.identity_context.identity_status,
            state.identity_context.counterpart_name,
            state.identity_context.relationship_type,
            state.summary_text,
            "",
            thought.focus,
            thought.salience_score,
        ),
    )