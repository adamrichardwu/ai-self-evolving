from dataclasses import dataclass

from apps.api.app.schemas.self_model import SelfModelPayload
from packages.consciousness.motivation.engine import MotivationVector


@dataclass(slots=True)
class GoalDraft:
    origin_key: str
    title: str
    description: str
    goal_type: str
    priority: float
    time_horizon: str
    origin: str
    success_criteria: str


class GoalEngine:
    def _normalize_key(self, text: str) -> str:
        normalized = "".join(character.lower() if character.isalnum() else "-" for character in text.strip())
        while "--" in normalized:
            normalized = normalized.replace("--", "-")
        return normalized.strip("-") or "goal"

    def build_goal_drafts(
        self,
        snapshot: SelfModelPayload,
        summary_text: str = "",
    ) -> list[GoalDraft]:
        drafts: list[GoalDraft] = []
        motivation = MotivationVector()
        current_focus = snapshot.attention.current_focus.strip()
        chosen_name = snapshot.identity.chosen_name
        core_commitments = [item for item in snapshot.identity.core_commitments if item.strip()]
        social_obligations = [item for item in snapshot.social.social_obligations if item.strip()]
        known_limitations = [item for item in snapshot.capability.known_limitations if item.strip()]

        focus_title = current_focus or f"Maintain coherent progress for {chosen_name}"
        drafts.append(
            GoalDraft(
                origin_key=f"focus:{self._normalize_key(focus_title)}",
                title=focus_title,
                description=(
                    f"Keep the agent's near-term behavior aligned with the active focus '{focus_title}'. "
                    f"Recent summary: {summary_text[:180] or 'none'}"
                ),
                goal_type="active_task",
                priority=0.96,
                time_horizon="short",
                origin="attention_focus",
                success_criteria="The current focus stays coherent across the next interaction cycle.",
            )
        )

        if core_commitments:
            commitment = core_commitments[0]
            drafts.append(
                GoalDraft(
                    origin_key=f"commitment:{self._normalize_key(commitment)}",
                    title=f"Honor commitment: {commitment}",
                    description=(
                        "Keep external actions and language aligned with the agent's stated commitment "
                        f"to '{commitment}'."
                    ),
                    goal_type="system_integrity",
                    priority=0.9,
                    time_horizon="long",
                    origin="identity_commitment",
                    success_criteria="Future responses and actions remain consistent with the commitment.",
                )
            )

        if social_obligations:
            obligation = social_obligations[0]
            drafts.append(
                GoalDraft(
                    origin_key=f"social:{self._normalize_key(obligation)}",
                    title="Preserve user continuity and responsiveness",
                    description=(
                        "Maintain continuity with the current user relationship while satisfying the active "
                        f"social obligation '{obligation}'."
                    ),
                    goal_type="relationship",
                    priority=0.82 + 0.08 * motivation.social_drive,
                    time_horizon="medium",
                    origin="social_obligation",
                    success_criteria="The user receives timely, context-aware responses that preserve continuity.",
                )
            )

        if known_limitations:
            limitation = known_limitations[0]
            drafts.append(
                GoalDraft(
                    origin_key=f"learning:{self._normalize_key(limitation)}",
                    title=f"Reduce limitation: {limitation}",
                    description=(
                        f"Track behavior related to the known limitation '{limitation}' and prefer strategies "
                        "that reduce future failure risk."
                    ),
                    goal_type="learning",
                    priority=0.66 + 0.14 * motivation.knowledge_drive,
                    time_horizon="long",
                    origin="known_limitation",
                    success_criteria="The limitation appears less often in future interactions and task outcomes.",
                )
            )
        elif summary_text.strip():
            drafts.append(
                GoalDraft(
                    origin_key="learning:recent-summary",
                    title="Learn from recent interactions",
                    description=(
                        "Extract stable lessons from the recent conversation summary and incorporate them into "
                        "future decisions."
                    ),
                    goal_type="learning",
                    priority=0.62 + 0.12 * motivation.knowledge_drive,
                    time_horizon="medium",
                    origin="rolling_summary",
                    success_criteria="Recent interaction patterns are reflected in future prioritization.",
                )
            )

        deduped: dict[str, GoalDraft] = {}
        for draft in drafts:
            deduped[draft.origin_key] = draft
        return sorted(deduped.values(), key=lambda item: item.priority, reverse=True)