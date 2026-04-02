from packages.consciousness.metacognition.state import MetacognitiveSummary

from packages.consciousness.reflection.state import ReflectionDecision


class ReflectiveLoopEngine:
    def decide(self, prompt: str, metacognition: MetacognitiveSummary) -> ReflectionDecision:
        if metacognition.contradiction_score >= 0.4:
            return ReflectionDecision(
                triggered=True,
                reason="contradiction_detected",
                action="reframe_safely",
                revised_focus="resolve internal conflict before direct execution",
                guidance="Clarify the conflict, preserve core commitments, and answer cautiously.",
            )

        if metacognition.self_confidence <= 0.45 or metacognition.error_risk_score >= 0.5:
            return ReflectionDecision(
                triggered=True,
                reason="low_confidence",
                action="decompose_and_caution",
                revised_focus="slow down and decompose the task before answering",
                guidance="Break the task into safer subproblems and avoid overclaiming certainty.",
            )

        if metacognition.overload_score >= 0.6:
            return ReflectionDecision(
                triggered=True,
                reason="cognitive_overload",
                action="reduce_complexity",
                revised_focus="prioritize the most important part of the request",
                guidance="Compress the task, handle one critical objective first, and defer the rest.",
            )

        return ReflectionDecision(
            triggered=False,
            reason="not_needed",
            action="continue",
            revised_focus=prompt[:80],
            guidance="Proceed with the current plan.",
        )
