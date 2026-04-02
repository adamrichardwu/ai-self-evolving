from uuid import uuid4

from sqlalchemy.orm import Session

from apps.api.app.services.social import record_social_interaction
from apps.api.app.services.self_model import apply_runtime_self_model_update, get_self_model_by_agent_id
from apps.api.app.schemas.tasks import (
    ExecuteTaskMetrics,
    MetacognitiveAlertSchema,
    MetacognitiveSummarySchema,
    ExecuteTaskOutput,
    ExecuteTaskRequest,
    ExecuteTaskResponse,
    ReflectionSummary,
    WorkspaceSummary,
)
from packages.consciousness.metacognition.engine import MetacognitiveMonitor
from packages.consciousness.metacognition.state import MetacognitiveSummary
from packages.consciousness.reflection.engine import ReflectiveLoopEngine
from packages.consciousness.workspace.engine import GlobalWorkspaceEngine
from packages.consciousness.workspace.state import WorkspaceSignal
from packages.orchestration.graphs.main_graph import run_task_graph
from packages.orchestration.state.task_state import TaskState


def _build_workspace_signals(
    payload: ExecuteTaskRequest,
    self_model_focus: str,
    metacognitive_alerts: list[str],
    reflection_focus: str,
) -> list[WorkspaceSignal]:
    prompt = payload.input.prompt.strip()
    signals = [
        WorkspaceSignal(
            signal_id="external_input",
            content=prompt,
            risk_score=0.2,
            urgency_score=0.7,
            goal_relevance=0.9,
            novelty_score=0.4,
            social_score=0.2,
        ),
        WorkspaceSignal(
            signal_id="strategy_context",
            content=f"strategy:{payload.strategy_version}",
            risk_score=0.1,
            urgency_score=0.3,
            goal_relevance=0.8,
            novelty_score=0.1,
            social_score=0.0,
        ),
    ]
    if payload.social_context is not None:
        counterpart_label = (
            payload.social_context.counterpart_name or payload.social_context.counterpart_id
        )
        signals.append(
            WorkspaceSignal(
                signal_id="social_context",
                content=f"social:{counterpart_label}:{payload.social_context.relationship_type}",
                risk_score=0.2,
                urgency_score=0.5,
                goal_relevance=0.7,
                novelty_score=0.3,
                social_score=0.9,
            )
        )
    if self_model_focus:
        signals.append(
            WorkspaceSignal(
                signal_id="self_model_focus",
                content=self_model_focus,
                risk_score=0.4,
                urgency_score=0.5,
                goal_relevance=0.8,
                novelty_score=0.2,
                social_score=0.3,
            )
        )
    for index, alert in enumerate(metacognitive_alerts, start=1):
        signals.append(
            WorkspaceSignal(
                signal_id=f"metacognitive_alert_{index}",
                content=alert,
                risk_score=0.9,
                urgency_score=0.8,
                goal_relevance=0.7,
                novelty_score=0.3,
                social_score=0.0,
            )
        )
    if reflection_focus:
        signals.append(
            WorkspaceSignal(
                signal_id="reflection_focus",
                content=reflection_focus,
                risk_score=0.7,
                urgency_score=0.7,
                goal_relevance=0.9,
                novelty_score=0.2,
                social_score=0.0,
            )
        )
    return signals


def execute_task(payload: ExecuteTaskRequest, db: Session) -> ExecuteTaskResponse:
    prompt = payload.input.prompt.strip()
    self_model = None
    if payload.agent_id:
        self_model = get_self_model_by_agent_id(db, payload.agent_id)

    self_model_focus = ""
    core_commitments: list[str] = []
    known_limitations: list[str] = []
    existing_contradiction_score = 0.0
    if self_model is not None:
        self_model_focus = self_model.snapshot.attention.current_focus or self_model.snapshot.identity.chosen_name
        core_commitments = self_model.snapshot.identity.core_commitments
        known_limitations = self_model.snapshot.capability.known_limitations
        existing_contradiction_score = self_model.snapshot.metacognition.contradiction_score

    metacognitive_monitor = MetacognitiveMonitor()
    metacognitive_summary = metacognitive_monitor.analyze(
        prompt=prompt,
        current_focus=self_model_focus,
        core_commitments=core_commitments,
        known_limitations=known_limitations,
        existing_contradiction_score=existing_contradiction_score,
    )

    reflective_loop = ReflectiveLoopEngine()
    reflection_decision = reflective_loop.decide(
        prompt=prompt,
        metacognition=MetacognitiveSummary(
            self_confidence=metacognitive_summary.self_confidence,
            contradiction_score=metacognitive_summary.contradiction_score,
            overload_score=metacognitive_summary.overload_score,
            novelty_score=metacognitive_summary.novelty_score,
            error_risk_score=metacognitive_summary.error_risk_score,
            alerts=metacognitive_summary.alerts,
        ),
    )

    task_state = TaskState(
        prompt=prompt,
        strategy_version=payload.strategy_version,
        model_profile=payload.model_profile,
        agent_id=payload.agent_id,
        self_model_focus=self_model_focus,
    )
    graph_state = run_task_graph(task_state)

    workspace_engine = GlobalWorkspaceEngine()
    workspace_state = workspace_engine.run_cycle(
        _build_workspace_signals(
            payload,
            graph_state["self_model_focus"],
            [alert.message for alert in metacognitive_summary.alerts],
            reflection_decision.revised_focus if reflection_decision.triggered else "",
        )
    )

    focused_prompt = workspace_state.dominant_focus or prompt
    if reflection_decision.triggered:
        focused_prompt = f"{reflection_decision.guidance} | {focused_prompt}"
    metacognition_schema = MetacognitiveSummarySchema(
        self_confidence=metacognitive_summary.self_confidence,
        contradiction_score=metacognitive_summary.contradiction_score,
        overload_score=metacognitive_summary.overload_score,
        novelty_score=metacognitive_summary.novelty_score,
        error_risk_score=metacognitive_summary.error_risk_score,
        alerts=[
            MetacognitiveAlertSchema(kind=alert.kind, message=alert.message, severity=alert.severity)
            for alert in metacognitive_summary.alerts
        ],
    )

    if payload.agent_id and self_model is not None:
        if payload.social_context is not None:
            record_social_interaction(
                db=db,
                agent_id=payload.agent_id,
                context=payload.social_context,
                fallback_summary=prompt[:240],
            )
        apply_runtime_self_model_update(
            db=db,
            agent_id=payload.agent_id,
            current_focus=workspace_state.dominant_focus or self_model_focus or prompt,
            metacognition=self_model.snapshot.metacognition.model_copy(
                update={
                    "self_confidence": metacognitive_summary.self_confidence,
                    "contradiction_score": metacognitive_summary.contradiction_score,
                    "overload_score": metacognitive_summary.overload_score,
                    "novelty_score": metacognitive_summary.novelty_score,
                    "error_risk_score": metacognitive_summary.error_risk_score,
                }
            ),
            task_prompt=prompt,
        )

    return ExecuteTaskResponse(
        task_run_id=str(uuid4()),
        status="succeeded",
        output=ExecuteTaskOutput(text=f"stub-response: {focused_prompt}"),
        metrics=ExecuteTaskMetrics(latency_ms=100, token_input=len(prompt), token_output=16),
        workspace=WorkspaceSummary(
            dominant_focus=workspace_state.dominant_focus,
            active_broadcast_items=workspace_state.active_broadcast_items,
            suppressed_items=workspace_state.suppressed_items,
            attention_shift_reason=workspace_state.attention_shift_reason,
            cycle_confidence=workspace_state.cycle_confidence,
        ),
        metacognition=metacognition_schema,
        reflection=ReflectionSummary(
            triggered=reflection_decision.triggered,
            reason=reflection_decision.reason,
            action=reflection_decision.action,
            revised_focus=reflection_decision.revised_focus,
            guidance=reflection_decision.guidance,
        ),
    )
