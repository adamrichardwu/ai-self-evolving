from packages.consciousness.workspace.state import WorkspaceCycleState, WorkspaceSignal


class GlobalWorkspaceEngine:
    def run_cycle(self, signals: list[WorkspaceSignal], top_k: int = 3) -> WorkspaceCycleState:
        ordered = sorted(signals, key=lambda signal: signal.salience, reverse=True)
        selected = ordered[:top_k]
        suppressed = ordered[top_k:]
        if not selected:
            return WorkspaceCycleState(attention_shift_reason="no_signals")

        dominant = selected[0]
        return WorkspaceCycleState(
            dominant_focus=dominant.content,
            active_broadcast_items=[signal.content for signal in selected],
            suppressed_items=[signal.content for signal in suppressed],
            attention_shift_reason="salience_ranking",
            cycle_confidence=min(1.0, dominant.salience / 5.0),
        )
