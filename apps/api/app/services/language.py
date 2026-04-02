from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.core.settings import settings
from apps.api.app.schemas.goals import GoalResponse
from apps.api.app.schemas.language import (
    InnerThoughtResponse,
    LanguageExchangeResponse,
    LanguageInputRequest,
    LanguageMessageResponse,
    LanguageSummaryResponse,
    LanguageStateResponse,
)
from apps.api.app.schemas.social import SocialInteractionContextSchema
from apps.api.app.services.goals import list_goals, refresh_goals
from apps.api.app.services.llm import OpenAICompatibleLLM
from apps.api.app.services.self_model import apply_runtime_self_model_update, get_self_model_by_agent_id
from apps.api.app.services.social import record_social_interaction
from packages.consciousness.language.engine import LanguageEngine
from packages.consciousness.language.persistence import (
    InnerThoughtRecord,
    LanguageMessageRecord,
    LanguageSummaryRecord,
)
from packages.consciousness.metacognition.engine import MetacognitiveMonitor
from packages.consciousness.metacognition.state import MetacognitiveSummary
from packages.consciousness.reflection.engine import ReflectiveLoopEngine
from packages.consciousness.self_model.persistence import SelfModelRecord
from packages.consciousness.workspace.engine import GlobalWorkspaceEngine
from packages.consciousness.workspace.state import WorkspaceSignal


llm = OpenAICompatibleLLM()


def _get_self_model_record(db: Session, agent_id: str) -> SelfModelRecord | None:
    return db.scalar(select(SelfModelRecord).where(SelfModelRecord.agent_id == agent_id))


def _to_message_response(record: LanguageMessageRecord) -> LanguageMessageResponse:
    return LanguageMessageResponse(
        id=record.id,
        self_model_id=record.self_model_id,
        role=record.role,
        content=record.content,
        channel=record.channel,
    )


def _to_thought_response(record: InnerThoughtRecord) -> InnerThoughtResponse:
    return InnerThoughtResponse(
        id=record.id,
        self_model_id=record.self_model_id,
        thought_type=record.thought_type,
        focus=record.focus,
        content=record.content,
        salience_score=record.salience_score,
        source=record.source,
    )


def _to_summary_response(record: LanguageSummaryRecord) -> LanguageSummaryResponse:
    return LanguageSummaryResponse(
        self_model_id=record.self_model_id,
        summary_text=record.summary_text,
        message_count=record.message_count,
        last_focus=record.last_focus,
    )


def _active_goals_snapshot(db: Session, agent_id: str) -> tuple[str, list[GoalResponse]]:
    active_goals = list_goals(db, agent_id, active_only=True) or []
    dominant_goal = active_goals[0].title if active_goals else ""
    return dominant_goal, active_goals


def _latest_message(db: Session, self_model_id: str, role: str | None = None) -> LanguageMessageRecord | None:
    query = select(LanguageMessageRecord).where(LanguageMessageRecord.self_model_id == self_model_id)
    if role is not None:
        query = query.where(LanguageMessageRecord.role == role)
    return db.scalar(query.order_by(LanguageMessageRecord.created_at.desc()))


def _latest_thought(db: Session, self_model_id: str) -> InnerThoughtRecord | None:
    return db.scalar(
        select(InnerThoughtRecord)
        .where(InnerThoughtRecord.self_model_id == self_model_id)
        .order_by(InnerThoughtRecord.created_at.desc())
    )


def _get_language_summary(db: Session, self_model_id: str) -> LanguageSummaryRecord | None:
    return db.scalar(
        select(LanguageSummaryRecord).where(LanguageSummaryRecord.self_model_id == self_model_id)
    )


def _update_language_summary(
    db: Session,
    self_model_id: str,
    chosen_name: str,
    focus: str,
    recent_messages: list[tuple[str, str]],
) -> LanguageSummaryRecord:
    current = _get_language_summary(db, self_model_id)
    engine = LanguageEngine()
    llm_summary = llm.generate(
        system_prompt=engine.summary_system_prompt(chosen_name),
        user_prompt=engine.summary_user_prompt(
            current_summary=current.summary_text if current is not None else "",
            focus=focus,
            recent_messages=recent_messages,
        ),
        temperature=0.3,
    )
    summary_text = engine.compose_summary(
        current_summary=current.summary_text if current is not None else "",
        focus=focus,
        recent_messages=recent_messages,
        llm_output=llm_summary,
    )

    if current is None:
        current = LanguageSummaryRecord(
            self_model_id=self_model_id,
            summary_text=summary_text,
            message_count=len(recent_messages),
            last_focus=focus,
        )
        db.add(current)
        db.flush()
        return current

    current.summary_text = summary_text
    current.message_count += len(recent_messages)
    current.last_focus = focus
    db.add(current)
    db.flush()
    return current


def _build_language_workspace_signals(
    user_text: str,
    self_focus: str,
    latest_thought: str,
    obligations: list[str],
) -> list[WorkspaceSignal]:
    signals = [
        WorkspaceSignal(
            signal_id="language_input",
            content=user_text,
            risk_score=0.2,
            urgency_score=0.8,
            goal_relevance=0.9,
            novelty_score=0.4,
            social_score=0.5,
        ),
        WorkspaceSignal(
            signal_id="self_focus",
            content=self_focus,
            risk_score=0.2,
            urgency_score=0.4,
            goal_relevance=0.8,
            novelty_score=0.2,
            social_score=0.2,
        ),
    ]
    if latest_thought:
        signals.append(
            WorkspaceSignal(
                signal_id="latest_thought",
                content=latest_thought,
                risk_score=0.1,
                urgency_score=0.3,
                goal_relevance=0.7,
                novelty_score=0.1,
                social_score=0.2,
            )
        )
    if obligations:
        signals.append(
            WorkspaceSignal(
                signal_id="social_obligations",
                content=", ".join(obligations[:3]),
                risk_score=0.4,
                urgency_score=0.5,
                goal_relevance=0.7,
                novelty_score=0.1,
                social_score=0.8,
            )
        )
    return signals


def _persist_message(db: Session, self_model_id: str, role: str, content: str) -> LanguageMessageRecord:
    record = LanguageMessageRecord(self_model_id=self_model_id, role=role, content=content)
    db.add(record)
    db.flush()
    return record


def _persist_thought(
    db: Session,
    self_model_id: str,
    thought_type: str,
    focus: str,
    content: str,
    salience_score: float,
    source: str,
) -> InnerThoughtRecord:
    record = InnerThoughtRecord(
        self_model_id=self_model_id,
        thought_type=thought_type,
        focus=focus,
        content=content,
        salience_score=salience_score,
        source=source,
    )
    db.add(record)
    db.flush()
    return record


def run_language_thought_cycle(
    db: Session, agent_id: str, thought_type: str = "background_cycle", source: str = "background"
) -> InnerThoughtResponse | None:
    self_model = get_self_model_by_agent_id(db, agent_id)
    record = _get_self_model_record(db, agent_id)
    if self_model is None or record is None:
        return None

    latest_user_message = _latest_message(db, record.id, role="user")
    workspace_engine = GlobalWorkspaceEngine()
    workspace = workspace_engine.run_cycle(
        _build_language_workspace_signals(
            user_text=latest_user_message.content if latest_user_message is not None else "",
            self_focus=self_model.snapshot.attention.current_focus or self_model.snapshot.identity.chosen_name,
            latest_thought=_latest_thought(db, record.id).content if _latest_thought(db, record.id) else "",
            obligations=self_model.snapshot.social.social_obligations,
        )
    )

    engine = LanguageEngine()
    llm_thought = llm.generate(
        system_prompt=engine.background_system_prompt(self_model.snapshot.identity.chosen_name),
        user_prompt=engine.background_user_prompt(
            chosen_name=self_model.snapshot.identity.chosen_name,
            dominant_focus=workspace.dominant_focus,
            latest_user_message=latest_user_message.content if latest_user_message is not None else "",
            obligations=self_model.snapshot.social.social_obligations,
        ),
        temperature=0.6,
    )
    thought_content = engine.compose_background_thought(
        chosen_name=self_model.snapshot.identity.chosen_name,
        dominant_focus=workspace.dominant_focus,
        latest_user_message=latest_user_message.content if latest_user_message is not None else "",
        obligations=self_model.snapshot.social.social_obligations,
        llm_output=llm_thought,
    )
    thought = _persist_thought(
        db=db,
        self_model_id=record.id,
        thought_type=thought_type,
        focus=workspace.dominant_focus or self_model.snapshot.identity.chosen_name,
        content=thought_content,
        salience_score=workspace.cycle_confidence,
        source=source,
    )
    db.commit()
    db.refresh(thought)
    return _to_thought_response(thought)


def run_background_language_cycles(db: Session) -> int:
    agents = db.scalars(select(SelfModelRecord.agent_id).order_by(SelfModelRecord.updated_at.desc())).all()
    processed = 0
    for agent_id in agents:
        thought = run_language_thought_cycle(db, agent_id, thought_type="background_cycle", source="background")
        if thought is not None:
            processed += 1
    return processed


def send_language_message(
    db: Session, agent_id: str, request: LanguageInputRequest
) -> LanguageExchangeResponse | None:
    self_model = get_self_model_by_agent_id(db, agent_id)
    record = _get_self_model_record(db, agent_id)
    if self_model is None or record is None:
        return None

    user_message = _persist_message(db, record.id, role="user", content=request.text.strip())

    record_social_interaction(
        db=db,
        agent_id=agent_id,
        context=SocialInteractionContextSchema(
            counterpart_id=request.counterpart_id,
            counterpart_name=request.counterpart_name,
            relationship_type=request.relationship_type,
            interaction_summary=request.text.strip(),
            observed_sentiment=request.observed_sentiment,
            role_in_context="dialogue_partner",
            social_obligations=self_model.snapshot.social.social_obligations,
        ),
        fallback_summary=request.text.strip(),
    )

    refreshed_self_model = get_self_model_by_agent_id(db, agent_id)
    if refreshed_self_model is None:
        return None

    current_focus = (
        refreshed_self_model.snapshot.attention.current_focus
        or refreshed_self_model.snapshot.identity.chosen_name
    )
    latest_thought = _latest_thought(db, record.id)
    latest_thought_text = latest_thought.content if latest_thought is not None else ""

    monitor = MetacognitiveMonitor()
    summary = monitor.analyze(
        prompt=request.text.strip(),
        current_focus=current_focus,
        core_commitments=refreshed_self_model.snapshot.identity.core_commitments,
        known_limitations=refreshed_self_model.snapshot.capability.known_limitations,
        existing_contradiction_score=refreshed_self_model.snapshot.metacognition.contradiction_score,
    )
    reflection = ReflectiveLoopEngine().decide(
        prompt=request.text.strip(),
        metacognition=MetacognitiveSummary(
            self_confidence=summary.self_confidence,
            contradiction_score=summary.contradiction_score,
            overload_score=summary.overload_score,
            novelty_score=summary.novelty_score,
            error_risk_score=summary.error_risk_score,
            alerts=summary.alerts,
        ),
    )

    workspace = GlobalWorkspaceEngine().run_cycle(
        _build_language_workspace_signals(
            user_text=request.text.strip(),
            self_focus=current_focus,
            latest_thought=latest_thought_text,
            obligations=refreshed_self_model.snapshot.social.social_obligations,
        )
    )

    language_engine = LanguageEngine()
    llm_reaction_thought = llm.generate(
        system_prompt=language_engine.background_system_prompt(
            refreshed_self_model.snapshot.identity.chosen_name
        ),
        user_prompt=language_engine.background_user_prompt(
            chosen_name=refreshed_self_model.snapshot.identity.chosen_name,
            dominant_focus=workspace.dominant_focus or current_focus,
            latest_user_message=request.text.strip(),
            obligations=refreshed_self_model.snapshot.social.social_obligations,
        ),
        temperature=0.6,
    )
    reaction_thought = language_engine.compose_background_thought(
        chosen_name=refreshed_self_model.snapshot.identity.chosen_name,
        dominant_focus=workspace.dominant_focus or current_focus,
        latest_user_message=request.text.strip(),
        obligations=refreshed_self_model.snapshot.social.social_obligations,
        llm_output=llm_reaction_thought,
    )
    thought_record = _persist_thought(
        db=db,
        self_model_id=record.id,
        thought_type="reaction_cycle",
        focus=workspace.dominant_focus or current_focus,
        content=reaction_thought,
        salience_score=workspace.cycle_confidence,
        source="user_input",
    )

    llm_response = llm.generate(
        system_prompt=language_engine.response_system_prompt(
            refreshed_self_model.snapshot.identity.chosen_name,
            reflection.triggered,
        ),
        user_prompt=language_engine.response_user_prompt(
            user_text=request.text.strip(),
            dominant_focus=workspace.dominant_focus or current_focus,
            latest_thought=reaction_thought,
            reflection_triggered=reflection.triggered,
        ),
        temperature=0.7,
    )
    assistant_text = language_engine.compose_response(
        user_text=request.text.strip(),
        dominant_focus=workspace.dominant_focus or current_focus,
        latest_thought=reaction_thought,
        reflection_triggered=reflection.triggered,
        llm_output=llm_response,
    )
    assistant_message = _persist_message(db, record.id, role="assistant", content=assistant_text)
    _update_language_summary(
        db=db,
        self_model_id=record.id,
        chosen_name=refreshed_self_model.snapshot.identity.chosen_name,
        focus=workspace.dominant_focus or current_focus,
        recent_messages=[("user", request.text.strip()), ("assistant", assistant_text)],
    )
    db.commit()

    apply_runtime_self_model_update(
        db=db,
        agent_id=agent_id,
        current_focus=workspace.dominant_focus or current_focus,
        metacognition=refreshed_self_model.snapshot.metacognition.model_copy(
            update={
                "self_confidence": summary.self_confidence,
                "contradiction_score": summary.contradiction_score,
                "overload_score": summary.overload_score,
                "novelty_score": summary.novelty_score,
                "error_risk_score": summary.error_risk_score,
            }
        ),
        task_prompt=request.text.strip(),
        update_reason="language_interaction",
    )

    goals_refresh = refresh_goals(db, agent_id)
    dominant_goal, active_goals = _active_goals_snapshot(db, agent_id)
    if goals_refresh is not None and goals_refresh.dominant_goal:
        dominant_goal = goals_refresh.dominant_goal
        active_goals = goals_refresh.goals

    db.refresh(thought_record)
    db.refresh(assistant_message)
    return LanguageExchangeResponse(
        assistant_message=_to_message_response(assistant_message),
        inner_thought=_to_thought_response(thought_record),
        current_focus=workspace.dominant_focus or current_focus,
        dominant_goal=dominant_goal,
        active_goals=active_goals,
        reflection_triggered=reflection.triggered,
    )


def get_language_state(
    db: Session, agent_id: str, message_limit: int = 12, thought_limit: int = 12
) -> LanguageStateResponse | None:
    record = _get_self_model_record(db, agent_id)
    if record is None:
        return None

    messages = db.scalars(
        select(LanguageMessageRecord)
        .where(LanguageMessageRecord.self_model_id == record.id)
        .order_by(LanguageMessageRecord.created_at.desc())
        .limit(message_limit)
    ).all()
    thoughts = db.scalars(
        select(InnerThoughtRecord)
        .where(InnerThoughtRecord.self_model_id == record.id)
        .order_by(InnerThoughtRecord.created_at.desc())
        .limit(thought_limit)
    ).all()
    summary = _get_language_summary(db, record.id)
    dominant_goal, active_goals = _active_goals_snapshot(db, agent_id)
    return LanguageStateResponse(
        agent_id=agent_id,
        background_loop_enabled=settings.language_background_loop_enabled,
        summary=_to_summary_response(summary) if summary is not None else None,
        dominant_goal=dominant_goal,
        active_goals=active_goals,
        messages=[_to_message_response(item) for item in reversed(messages)],
        thoughts=[_to_thought_response(item) for item in reversed(thoughts)],
    )