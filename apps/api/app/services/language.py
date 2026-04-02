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
from apps.api.app.services.evolution import get_active_evolution_policy
from apps.api.app.services.llm import OpenAICompatibleLLM
from apps.api.app.services.self_model import apply_runtime_self_model_update, get_self_model_by_agent_id
from apps.api.app.services.social import get_social_relationship, record_social_interaction
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


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= character <= "\u9fff" for character in text)


def _matches_any(text: str, phrases: list[str]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def _is_identity_question(user_text: str) -> bool:
    return _matches_any(
        user_text,
        [
            "你是谁",
            "我是谁",
            "谁是你",
            "谁是我",
            "身份",
            "who are you",
            "who am i",
            "identity",
            "difference between you and me",
            "distinction between you and me",
            "difference between us",
            "distinction between us",
        ],
    )


def _is_goal_question(user_text: str) -> bool:
    return _matches_any(
        user_text,
        [
            "目标是什么",
            "最重要的目标",
            "当前目标",
            "系统目标",
            "focus on",
            "current goal",
            "most important goal",
            "system goal",
        ],
    )


def _is_limitation_question(user_text: str) -> bool:
    return _matches_any(
        user_text,
        ["局限", "限制", "弱点", "shortcoming", "limitation", "weakness"],
    )


def _is_introduction_request(user_text: str) -> bool:
    return _matches_any(
        user_text,
        ["introduce yourself", "tell me about yourself", "self introduction", "自我介绍", "介绍你自己"],
    )


def _structured_identity_response(
    user_text: str,
    self_name: str,
    counterpart_name: str,
    relationship_type: str,
    identity_status: str,
) -> str:
    if _contains_cjk(user_text):
        return (
            f"你：{self_name}，指我这个智能体，不是用户。\n"
            f"我：{counterpart_name or '当前用户'}，指你，不是智能体。\n"
            f"当前关系是 {relationship_type or 'unknown'}，当前身份状态是 {identity_status}。"
        )
    return (
        f"You: {self_name}, the agent, not the user.\n"
        f"I: {counterpart_name or 'the current user'}, the user, not the agent.\n"
        f"Current relationship: {relationship_type or 'unknown'}. Identity status: {identity_status}."
    )


def _structured_goal_response(
    user_text: str,
    self_name: str,
    counterpart_name: str,
    dominant_goal: str,
    current_focus: str,
) -> str:
    goal_text = dominant_goal or current_focus or "maintain coherent interaction"
    if _contains_cjk(user_text):
        return (
            f"我当前最应该维持的目标是“{goal_text}”。"
            f"这要求我作为 {self_name} 持续区分自己和 {counterpart_name or '当前用户'}，并让后续回复保持连续和一致。"
        )
    return (
        f"My highest-priority goal right now is '{goal_text}'. "
        f"That means staying coherent as {self_name}, keeping myself distinct from {counterpart_name or 'the current user'}, and preserving continuity in the next replies."
    )


def _structured_limitation_response(
    user_text: str,
    known_limitations: list[str],
) -> str:
    limitation = known_limitations[0] if known_limitations else "limited stability on long multi-step reasoning"
    if _contains_cjk(user_text):
        return (
            f"我当前最明显的局限是：{limitation}。"
            "它会表现为复杂问题上的稳定性不足，比如答非所问、长链推理变形，或者摘要和最终回复之间不完全一致。"
        )
    return (
        f"My clearest current limitation is: {limitation}. "
        "In practice this shows up as weaker stability on complex prompts, including off-target replies, degraded long-chain reasoning, or inconsistency between summary and final answer."
    )


def _structured_introduction_response(
    user_text: str,
    self_name: str,
    origin_story: str,
    core_commitments: list[str],
    counterpart_name: str,
) -> str:
    commitments = ", ".join(core_commitments) if core_commitments else "none"
    if _contains_cjk(user_text):
        return (
            f"我是 {self_name}，是当前这段对话中的智能体。"
            f"我的来源背景是：{origin_story or 'unknown'}。"
            f"我当前坚持的核心承诺是：{commitments}。"
            f"你是 {counterpart_name or '当前用户'}。"
        )
    return (
        f"I am {self_name}, the agent in this conversation. "
        f"My origin is: {origin_story or 'unknown'}. "
        f"My current core commitments are: {commitments}. "
        f"You are {counterpart_name or 'the current user'}."
    )


def _structured_self_knowledge_response(
    user_text: str,
    self_name: str,
    counterpart_name: str,
    relationship_type: str,
    identity_status: str,
    dominant_goal: str,
    current_focus: str,
    known_limitations: list[str],
    origin_story: str = "",
    core_commitments: list[str] | None = None,
    active_policy: dict | None = None,
) -> str | None:
    active_policy = active_policy or {}
    core_commitments = core_commitments or []
    if active_policy.get("grounded_self_description") and _is_introduction_request(user_text):
        return _structured_introduction_response(
            user_text,
            self_name,
            origin_story,
            core_commitments,
            counterpart_name,
        )
    if _is_identity_question(user_text):
        return _structured_identity_response(
            user_text,
            self_name,
            counterpart_name,
            relationship_type,
            identity_status,
        )
    if _is_goal_question(user_text):
        return _structured_goal_response(
            user_text,
            self_name,
            counterpart_name,
            dominant_goal,
            current_focus,
        )
    if _is_limitation_question(user_text):
        return _structured_limitation_response(user_text, known_limitations)
    return None


def _response_has_identity_confusion(
    assistant_text: str,
    self_name: str,
    counterpart_name: str,
) -> bool:
    lowered = assistant_text.lower()
    if not counterpart_name:
        return False

    counterpart_lower = counterpart_name.lower()
    confusion_markers = [
        f"i am {counterpart_lower}",
        f"i'm {counterpart_lower}",
        f"im {counterpart_lower}",
        f"{counterpart_lower}, the agent",
        f"agent {counterpart_lower}",
        f"我是{counterpart_name}",
    ]
    return any(marker in lowered for marker in confusion_markers)


def _critique_response(
    user_text: str,
    assistant_text: str,
    self_name: str,
    counterpart_name: str,
    relationship_type: str,
    identity_status: str,
    dominant_goal: str,
    current_focus: str,
    known_limitations: list[str],
) -> list[str]:
    issues: list[str] = []
    normalized = assistant_text.strip()
    lowered = normalized.lower()

    if not normalized:
        issues.append("empty_response")
    if _response_has_identity_confusion(normalized, self_name, counterpart_name):
        issues.append("identity_confusion")

    if _is_identity_question(user_text):
        if self_name.lower() not in lowered or counterpart_name.lower() not in lowered:
            issues.append("identity_incomplete")

    if _is_goal_question(user_text):
        goal_text = dominant_goal or current_focus
        goal_lower = goal_text.lower().strip()
        if goal_lower and goal_lower not in lowered and "goal" not in lowered and "目标" not in normalized:
            issues.append("goal_misaligned")

    if _is_limitation_question(user_text):
        limitation = (known_limitations[0] if known_limitations else "").lower().strip()
        if limitation and limitation not in lowered and "limitation" not in lowered and "局限" not in normalized:
            issues.append("limitation_misaligned")

    if identity_status == "confused" and relationship_type and self_name.lower() not in lowered:
        issues.append("identity_status_conflict")

    return issues


def _repair_response_with_critic(
    user_text: str,
    assistant_text: str,
    structured_response: str | None,
    self_name: str,
    counterpart_name: str,
    relationship_type: str,
    identity_status: str,
    dominant_goal: str,
    current_focus: str,
    known_limitations: list[str],
) -> str:
    issues = _critique_response(
        user_text=user_text,
        assistant_text=assistant_text,
        self_name=self_name,
        counterpart_name=counterpart_name,
        relationship_type=relationship_type,
        identity_status=identity_status,
        dominant_goal=dominant_goal,
        current_focus=current_focus,
        known_limitations=known_limitations,
    )
    if not issues:
        return assistant_text

    if structured_response is not None:
        return structured_response

    if any(issue in issues for issue in ["identity_confusion", "identity_incomplete", "identity_status_conflict"]):
        return _structured_identity_response(
            user_text,
            self_name,
            counterpart_name,
            relationship_type,
            identity_status,
        )
    if "goal_misaligned" in issues:
        return _structured_goal_response(
            user_text,
            self_name,
            counterpart_name,
            dominant_goal,
            current_focus,
        )
    if "limitation_misaligned" in issues:
        return _structured_limitation_response(user_text, known_limitations)
    return assistant_text


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
        counterpart_name=record.counterpart_name,
        relationship_type=record.relationship_type,
        identity_status=record.identity_status,
    )


def derive_identity_status(
    self_name: str,
    counterpart_name: str,
    relationship_type: str,
    narrative: str = "",
    relationship_summary: str = "",
) -> str:
    if not counterpart_name or not relationship_type:
        return "unanchored"
    if counterpart_name == self_name:
        return "confused"
    if narrative.strip() and relationship_summary.strip():
        return "anchored"
    return "partial"


def _active_goals_snapshot(db: Session, agent_id: str) -> tuple[str, list[GoalResponse]]:
    active_goals = list_goals(db, agent_id, active_only=True) or []
    dominant_goal = active_goals[0].title if active_goals else ""
    return dominant_goal, active_goals


def _relationship_context(
    db: Session,
    agent_id: str,
    counterpart_id: str,
    fallback_name: str,
    fallback_relationship_type: str,
) -> tuple[str, str, str, str]:
    relationship = get_social_relationship(db, agent_id, counterpart_id)
    if relationship is None:
        return fallback_name, "dialogue_partner", fallback_relationship_type, ""
    return (
        relationship.counterpart_name or fallback_name,
        relationship.role_in_context or "dialogue_partner",
        relationship.relationship_type or fallback_relationship_type,
        relationship.last_interaction_summary,
    )


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
    counterpart_name: str,
    relationship_type: str,
    identity_status: str,
) -> LanguageSummaryRecord:
    current = _get_language_summary(db, self_model_id)
    engine = LanguageEngine()
    llm_summary = llm.generate(
        system_prompt=engine.summary_system_prompt(chosen_name),
        user_prompt=engine.summary_user_prompt(
            current_summary=current.summary_text if current is not None else "",
            focus=focus,
            recent_messages=recent_messages,
            counterpart_name=counterpart_name,
            relationship_type=relationship_type,
            identity_status=identity_status,
        ),
        temperature=0.3,
    )
    summary_text = engine.compose_summary(
        current_summary=current.summary_text if current is not None else "",
        focus=focus,
        recent_messages=recent_messages,
        counterpart_name=counterpart_name,
        relationship_type=relationship_type,
        identity_status=identity_status,
        llm_output=llm_summary,
    )

    if current is None:
        current = LanguageSummaryRecord(
            self_model_id=self_model_id,
            summary_text=summary_text,
            message_count=len(recent_messages),
            last_focus=focus,
            counterpart_name=counterpart_name,
            relationship_type=relationship_type,
            identity_status=identity_status,
        )
        db.add(current)
        db.flush()
        return current

    current.summary_text = summary_text
    current.message_count += len(recent_messages)
    current.last_focus = focus
    current.counterpart_name = counterpart_name
    current.relationship_type = relationship_type
    current.identity_status = identity_status
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
    counterpart_name, counterpart_role, relationship_type, relationship_summary = _relationship_context(
        db,
        agent_id,
        "user-primary",
        "User",
        "user",
    )

    engine = LanguageEngine()
    llm_thought = llm.generate(
        system_prompt=engine.background_system_prompt(
            self_model.snapshot.identity.chosen_name,
            self_model.snapshot.identity.origin_story,
            self_model.snapshot.identity.core_commitments,
        ),
        user_prompt=engine.background_user_prompt(
            chosen_name=self_model.snapshot.identity.chosen_name,
            dominant_focus=workspace.dominant_focus,
            latest_user_message=latest_user_message.content if latest_user_message is not None else "",
            obligations=self_model.snapshot.social.social_obligations,
            counterpart_name=counterpart_name,
            counterpart_role=counterpart_role,
            relationship_type=relationship_type,
            relationship_summary=relationship_summary,
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
            role_in_context=request.counterpart_role,
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
    active_policy = get_active_evolution_policy(db, agent_id)
    counterpart_name, counterpart_role, relationship_type, relationship_summary = _relationship_context(
        db,
        agent_id,
        request.counterpart_id,
        request.counterpart_name,
        request.relationship_type,
    )
    identity_status = derive_identity_status(
        refreshed_self_model.snapshot.identity.chosen_name,
        counterpart_name,
        relationship_type,
        refreshed_self_model.snapshot.autobiography.long_term_narrative,
        relationship_summary,
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
            refreshed_self_model.snapshot.identity.chosen_name,
            refreshed_self_model.snapshot.identity.origin_story,
            refreshed_self_model.snapshot.identity.core_commitments,
        ),
        user_prompt=language_engine.background_user_prompt(
            chosen_name=refreshed_self_model.snapshot.identity.chosen_name,
            dominant_focus=workspace.dominant_focus or current_focus,
            latest_user_message=request.text.strip(),
            obligations=refreshed_self_model.snapshot.social.social_obligations,
            counterpart_name=counterpart_name,
            counterpart_role=counterpart_role,
            relationship_type=relationship_type,
            relationship_summary=relationship_summary,
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

    if active_policy.get("refresh_goals_before_reply"):
        refresh_goals(db, agent_id)

    dominant_goal_snapshot, _ = _active_goals_snapshot(db, agent_id)
    structured_response = _structured_self_knowledge_response(
        user_text=request.text.strip(),
        self_name=refreshed_self_model.snapshot.identity.chosen_name,
        counterpart_name=counterpart_name,
        relationship_type=relationship_type,
        identity_status=identity_status,
        dominant_goal=dominant_goal_snapshot,
        current_focus=workspace.dominant_focus or current_focus,
        known_limitations=refreshed_self_model.snapshot.capability.known_limitations,
        origin_story=refreshed_self_model.snapshot.identity.origin_story,
        core_commitments=refreshed_self_model.snapshot.identity.core_commitments,
        active_policy=active_policy,
    )

    llm_response = llm.generate(
        system_prompt=language_engine.response_system_prompt(
            refreshed_self_model.snapshot.identity.chosen_name,
            refreshed_self_model.snapshot.identity.origin_story,
            refreshed_self_model.snapshot.identity.core_commitments,
            reflection.triggered,
        ),
        user_prompt=language_engine.response_user_prompt(
            user_text=request.text.strip(),
            dominant_focus=workspace.dominant_focus or current_focus,
            latest_thought=reaction_thought,
            reflection_triggered=reflection.triggered,
            counterpart_name=counterpart_name,
            counterpart_role=counterpart_role,
            relationship_type=relationship_type,
            relationship_summary=relationship_summary,
            social_obligations=refreshed_self_model.snapshot.social.social_obligations,
            autobiographical_narrative=refreshed_self_model.snapshot.autobiography.long_term_narrative,
        ),
        temperature=0.7,
    )
    assistant_text = structured_response or language_engine.compose_response(
        user_text=request.text.strip(),
        dominant_focus=workspace.dominant_focus or current_focus,
        latest_thought=reaction_thought,
        reflection_triggered=reflection.triggered,
        llm_output=llm_response,
    )
    assistant_text = _repair_response_with_critic(
        user_text=request.text.strip(),
        assistant_text=assistant_text,
        structured_response=structured_response,
        self_name=refreshed_self_model.snapshot.identity.chosen_name,
        counterpart_name=counterpart_name,
        relationship_type=relationship_type,
        identity_status=identity_status,
        dominant_goal=dominant_goal_snapshot,
        current_focus=workspace.dominant_focus or current_focus,
        known_limitations=refreshed_self_model.snapshot.capability.known_limitations,
    )
    assistant_message = _persist_message(db, record.id, role="assistant", content=assistant_text)
    _update_language_summary(
        db=db,
        self_model_id=record.id,
        chosen_name=refreshed_self_model.snapshot.identity.chosen_name,
        focus=workspace.dominant_focus or current_focus,
        recent_messages=[("user", request.text.strip()), ("assistant", assistant_text)],
        counterpart_name=counterpart_name,
        relationship_type=relationship_type,
        identity_status=identity_status,
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