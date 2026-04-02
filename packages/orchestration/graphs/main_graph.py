from packages.orchestration.state.task_state import TaskState


def run_task_graph(state: TaskState) -> dict[str, str]:
    return {
        "prompt": state.prompt,
        "strategy_version": state.strategy_version,
        "model_profile": state.model_profile,
        "agent_id": state.agent_id or "",
        "self_model_focus": state.self_model_focus,
    }
