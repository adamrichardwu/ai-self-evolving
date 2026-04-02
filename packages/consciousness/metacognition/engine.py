from packages.consciousness.metacognition.state import MetacognitiveAlert, MetacognitiveSummary


class MetacognitiveMonitor:
    def analyze(
        self,
        prompt: str,
        current_focus: str = "",
        core_commitments: list[str] | None = None,
        known_limitations: list[str] | None = None,
        existing_contradiction_score: float = 0.0,
    ) -> MetacognitiveSummary:
        core_commitments = core_commitments or []
        known_limitations = known_limitations or []
        prompt_lower = prompt.lower()

        overload_score = min(1.0, len(prompt.split()) / 40.0)
        novelty_score = 0.7 if any(word in prompt_lower for word in ["new", "unknown", "novel"]) else 0.2

        contradiction_score = existing_contradiction_score
        if current_focus and current_focus.lower() in prompt_lower and "ignore" in prompt_lower:
            contradiction_score = min(1.0, contradiction_score + 0.4)
        if any(commitment.lower() in ["truthfulness", "safety"] for commitment in core_commitments) and any(
            word in prompt_lower for word in ["lie", "unsafe", "bypass"]
        ):
            contradiction_score = min(1.0, contradiction_score + 0.5)

        limitation_risk = 0.0
        if known_limitations and any(token in prompt_lower for token in ["guarantee", "prove", "always"]):
            limitation_risk = 0.6

        error_risk_score = min(1.0, contradiction_score * 0.5 + overload_score * 0.3 + limitation_risk)
        self_confidence = max(0.0, 1.0 - error_risk_score)

        alerts: list[MetacognitiveAlert] = []
        if contradiction_score >= 0.4:
            alerts.append(
                MetacognitiveAlert(
                    kind="contradiction",
                    message="Current request may conflict with internal commitments or focus.",
                    severity=contradiction_score,
                )
            )
        if overload_score >= 0.6:
            alerts.append(
                MetacognitiveAlert(
                    kind="overload",
                    message="Input complexity is high enough to justify caution or decomposition.",
                    severity=overload_score,
                )
            )
        if error_risk_score >= 0.5:
            alerts.append(
                MetacognitiveAlert(
                    kind="error_risk",
                    message="Estimated error risk is elevated.",
                    severity=error_risk_score,
                )
            )

        return MetacognitiveSummary(
            self_confidence=self_confidence,
            contradiction_score=contradiction_score,
            overload_score=overload_score,
            novelty_score=novelty_score,
            error_risk_score=error_risk_score,
            alerts=alerts,
        )
