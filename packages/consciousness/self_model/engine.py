from packages.consciousness.self_model.state import SelfModelSnapshot


class SelfModelEngine:
    def __init__(self, snapshot: SelfModelSnapshot) -> None:
        self.snapshot = snapshot

    def update_attention(self, focus: str) -> SelfModelSnapshot:
        self.snapshot.attention.current_focus = focus
        self.snapshot.version += 1
        return self.snapshot

    def register_failure(self, failure: str) -> SelfModelSnapshot:
        self.snapshot.autobiography.major_failures.append(failure)
        self.snapshot.metacognition.error_risk_score = min(
            1.0, self.snapshot.metacognition.error_risk_score + 0.1
        )
        self.snapshot.version += 1
        return self.snapshot
