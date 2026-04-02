from packages.consciousness.social.state import SocialInteractionSignal, SocialRelationshipSnapshot


class SocialMemoryEngine:
    def compute_trust_delta(self, signal: SocialInteractionSignal) -> float:
        if signal.trust_delta is not None:
            return signal.trust_delta

        sentiment = signal.observed_sentiment.lower().strip()
        if sentiment in {"positive", "warm", "supportive"}:
            return 0.08
        if sentiment in {"negative", "hostile", "strained"}:
            return -0.12
        return 0.03

    def update_trust(self, current: float, signal: SocialInteractionSignal) -> float:
        return max(0.0, min(1.0, current + self.compute_trust_delta(signal)))

    def update_familiarity(self, current: float, interaction_count: int) -> float:
        step = 0.15 if interaction_count == 0 else 0.08
        return max(0.0, min(1.0, current + step))

    def merge_obligations(self, current: list[str], incoming: list[str]) -> list[str]:
        merged = current + incoming
        return list(dict.fromkeys(item.strip() for item in merged if item.strip()))

    def build_active_relationship_label(self, snapshot: SocialRelationshipSnapshot) -> str:
        return snapshot.counterpart_name or snapshot.counterpart_id