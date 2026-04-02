from sqlalchemy.orm import Session

from apps.api.app.schemas.language import LanguageInputRequest
from apps.api.app.schemas.runtime import RuntimeStateResponse, RuntimeStepRequest, RuntimeStepResponse
from apps.api.app.services.goals import refresh_goals
from apps.api.app.services.language import get_language_state, run_language_thought_cycle, send_language_message
from apps.api.app.services.self_model import get_self_model_by_agent_id


def get_runtime_state(db: Session, agent_id: str) -> RuntimeStateResponse | None:
    self_model = get_self_model_by_agent_id(db, agent_id)
    language_state = get_language_state(db, agent_id)
    if self_model is None or language_state is None:
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
    )