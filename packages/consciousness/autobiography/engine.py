from apps.api.app.schemas.self_model import AutobiographicalSummarySchema, MetacognitiveStateSchema


class AutobiographicalConsolidator:
    def build_event_summary(
        self,
        current_focus: str,
        task_prompt: str,
        metacognition: MetacognitiveStateSchema,
    ) -> tuple[str, str, str, str]:
        event_type = "routine_cycle"
        emotional_tone = "neutral"
        salience = "medium"

        if metacognition.contradiction_score >= 0.4:
            event_type = "conflict_encounter"
            emotional_tone = "tense"
            salience = "high"
        elif metacognition.self_confidence >= 0.75:
            event_type = "stable_progress"
            emotional_tone = "steady"
            salience = "medium"

        summary = (
            f"Focus was '{current_focus}'. Prompt theme was '{task_prompt[:80]}'. "
            f"Confidence={metacognition.self_confidence:.2f}, risk={metacognition.error_risk_score:.2f}."
        )
        return event_type, summary, emotional_tone, salience

    def consolidate(
        self,
        current_summary: AutobiographicalSummarySchema,
        current_focus: str,
        event_summary: str,
        metacognition: MetacognitiveStateSchema,
    ) -> AutobiographicalSummarySchema:
        recent_updates = list(current_summary.recent_identity_updates)
        recent_updates.append(event_summary)

        key_milestones = list(current_summary.key_milestones)
        if metacognition.contradiction_score >= 0.5:
            key_milestones.append("Encountered a meaningful internal contradiction and preserved it for review")

        narrative_parts = [current_summary.long_term_narrative.strip()] if current_summary.long_term_narrative else []
        narrative_parts.append(
            f"The agent is currently organizing itself around focus '{current_focus}' while tracking risk at {metacognition.error_risk_score:.2f}."
        )
        long_term_narrative = " ".join(part for part in narrative_parts if part).strip()

        return AutobiographicalSummarySchema(
            key_milestones=key_milestones[-10:],
            recent_identity_updates=recent_updates[-12:],
            major_failures=current_summary.major_failures,
            recovered_failures=current_summary.recovered_failures,
            long_term_narrative=long_term_narrative,
        )

    def consolidate_event_batch(
        self,
        current_summary: AutobiographicalSummarySchema,
        event_summaries: list[str],
        dominant_themes: list[str],
    ) -> tuple[AutobiographicalSummarySchema, str, str]:
        if not event_summaries:
            return current_summary, "", ""

        compressed_summary = " ".join(event_summaries[-5:]).strip()
        theme_text = ", ".join(dominant_themes[:3]) if dominant_themes else "continuity"
        narrative_delta = (
            f"Recent autobiographical consolidation indicates dominant themes of {theme_text}. "
            f"The agent is integrating {len(event_summaries)} recent experiences into a more stable identity narrative."
        )

        key_milestones = list(current_summary.key_milestones)
        key_milestones.append(f"Consolidated {len(event_summaries)} autobiographical events into a phase summary")

        recent_updates = list(current_summary.recent_identity_updates)
        recent_updates.append(compressed_summary)

        long_term_narrative = " ".join(
            part
            for part in [current_summary.long_term_narrative.strip(), narrative_delta]
            if part
        ).strip()

        updated = AutobiographicalSummarySchema(
            key_milestones=key_milestones[-12:],
            recent_identity_updates=recent_updates[-12:],
            major_failures=current_summary.major_failures,
            recovered_failures=current_summary.recovered_failures,
            long_term_narrative=long_term_narrative,
        )
        return updated, compressed_summary, narrative_delta

