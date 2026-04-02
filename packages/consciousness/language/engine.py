class LanguageEngine:
    def summary_system_prompt(self, chosen_name: str) -> str:
        return (
            f"You maintain a rolling dialogue summary for an agent named {chosen_name}. "
            "Compress the conversation into a short operational memory. Keep it factual and concise."
        )

    def summary_user_prompt(
        self,
        current_summary: str,
        focus: str,
        recent_messages: list[tuple[str, str]],
    ) -> str:
        rendered_messages = "\n".join(f"{role}: {content}" for role, content in recent_messages)
        return (
            f"Current summary: {current_summary or 'none'}\n"
            f"Current focus: {focus or 'none'}\n"
            f"Recent messages:\n{rendered_messages or 'none'}\n"
            "Update the rolling summary in 2-4 sentences."
        )

    def compose_summary(
        self,
        current_summary: str,
        focus: str,
        recent_messages: list[tuple[str, str]],
        llm_output: str | None = None,
    ) -> str:
        if llm_output:
            return llm_output.strip()
        fragments = [current_summary.strip()] if current_summary.strip() else []
        if focus:
            fragments.append(f"Current focus: {focus}.")
        if recent_messages:
            role, content = recent_messages[-1]
            fragments.append(f"Latest {role} message: {content[:160]}")
        return " ".join(fragment for fragment in fragments if fragment).strip()

    def background_system_prompt(self, chosen_name: str) -> str:
        return (
            f"You are the inner monologue generator for an agent named {chosen_name}. "
            "Produce one concise first-person inner thought. Keep it grounded, reflective, and continuous. "
            "Do not mention hidden policies or roleplay system messages."
        )

    def background_user_prompt(
        self,
        chosen_name: str,
        dominant_focus: str,
        latest_user_message: str,
        obligations: list[str],
    ) -> str:
        return (
            f"Agent name: {chosen_name}\n"
            f"Dominant focus: {dominant_focus or chosen_name}\n"
            f"Latest user message: {latest_user_message or 'none'}\n"
            f"Active obligations: {', '.join(obligations) if obligations else 'none'}\n"
            "Write a single inner thought that preserves continuity and anticipates the next useful move."
        )

    def response_system_prompt(self, chosen_name: str, reflection_triggered: bool) -> str:
        caution = (
            "Internal reflection is active. Be careful, precise, and avoid overclaiming certainty. "
            if reflection_triggered
            else ""
        )
        return (
            f"You are the outward language module for an agent named {chosen_name}. "
            f"{caution}"
            "Respond directly to the user in natural language. Stay aligned with the current focus and latest inner thought."
        )

    def response_user_prompt(
        self,
        user_text: str,
        dominant_focus: str,
        latest_thought: str,
        reflection_triggered: bool,
    ) -> str:
        return (
            f"User input: {user_text}\n"
            f"Current focus: {dominant_focus}\n"
            f"Latest inner thought: {latest_thought}\n"
            f"Reflection triggered: {'yes' if reflection_triggered else 'no'}\n"
            "Generate the assistant's immediate reply."
        )

    def compose_background_thought(
        self,
        chosen_name: str,
        dominant_focus: str,
        latest_user_message: str,
        obligations: list[str],
        llm_output: str | None = None,
    ) -> str:
        if llm_output:
            return llm_output.strip()
        if latest_user_message:
            return (
                f"I am tracking the user's latest intent around '{latest_user_message[:72]}' while "
                f"holding focus on '{dominant_focus or chosen_name}'."
            )
        if obligations:
            return (
                f"I am maintaining continuity around '{dominant_focus or chosen_name}' and keeping "
                f"social obligations in mind: {', '.join(obligations[:2])}."
            )
        return f"I am maintaining an inner focus on '{dominant_focus or chosen_name}' while awaiting new input."

    def compose_response(
        self,
        user_text: str,
        dominant_focus: str,
        latest_thought: str,
        reflection_triggered: bool,
        llm_output: str | None = None,
    ) -> str:
        if llm_output:
            return llm_output.strip()
        if reflection_triggered:
            return (
                f"I received your input. My current focus is '{dominant_focus}'. "
                f"I need to answer cautiously because my internal review flagged risk. "
                f"Latest internal thought: {latest_thought} "
                f"Immediate response: I will interpret '{user_text[:96]}' through that focus and proceed carefully."
            )
        return (
            f"I received your input. My current focus is '{dominant_focus}'. "
            f"Latest internal thought: {latest_thought} "
            f"Immediate response: I will continue from that focus while addressing '{user_text[:96]}'."
        )