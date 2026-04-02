from dataclasses import dataclass


@dataclass(slots=True)
class TaskState:
    prompt: str
    strategy_version: str
    model_profile: str
    agent_id: str | None = None
    self_model_focus: str = ""
