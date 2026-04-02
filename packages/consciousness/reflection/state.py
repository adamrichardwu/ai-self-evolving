from dataclasses import dataclass


@dataclass(slots=True)
class ReflectionDecision:
    triggered: bool
    reason: str
    action: str
    revised_focus: str
    guidance: str
