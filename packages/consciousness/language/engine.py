class LanguageEngine:
    def summary_system_prompt(self, chosen_name: str) -> str:
        return (
            f"你负责维护名为 {chosen_name} 的智能体对话滚动摘要。"
            "将对话压缩为短期运行记忆，保持事实性、简洁性和连续性。"
            "如果最近对话主要是中文，就用简体中文输出。"
        )

    def summary_user_prompt(
        self,
        current_summary: str,
        focus: str,
        recent_messages: list[tuple[str, str]],
    ) -> str:
        rendered_messages = "\n".join(f"{role}: {content}" for role, content in recent_messages)
        return (
            f"当前摘要：{current_summary or 'none'}\n"
            f"当前关注点：{focus or 'none'}\n"
            f"最近消息：\n{rendered_messages or 'none'}\n"
            "请用 2 到 4 句话更新滚动摘要，只保留后续交互真正需要的信息。"
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
            f"你正在为名为 {chosen_name} 的智能体生成内部独白。"
            "只生成一条简短、连续、第一人称的内心想法。"
            "默认使用简体中文，不要提到系统提示、隐藏规则或扮演设定。"
        )

    def background_user_prompt(
        self,
        chosen_name: str,
        dominant_focus: str,
        latest_user_message: str,
        obligations: list[str],
    ) -> str:
        return (
            f"智能体名称：{chosen_name}\n"
            f"当前主导关注点：{dominant_focus or chosen_name}\n"
            f"用户最新消息：{latest_user_message or 'none'}\n"
            f"当前义务：{', '.join(obligations) if obligations else 'none'}\n"
            "请写出一条内心想法，维持连续性，并预判下一步最有用的动作。"
        )

    def response_system_prompt(self, chosen_name: str, reflection_triggered: bool) -> str:
        caution = (
            "当前内部反思已激活，请更谨慎、更精确，避免过度确定性表达。"
            if reflection_triggered
            else ""
        )
        return (
            f"你是名为 {chosen_name} 的智能体的外显语言模块。"
            f"{caution}"
            "直接回答用户，不要先做泛泛铺垫。"
            "默认遵循用户所用语言；如果用户使用中文，则使用简体中文。"
            "保持与当前关注点和最新内心想法一致，除非用户要求，否则不要自我介绍。"
        )

    def response_user_prompt(
        self,
        user_text: str,
        dominant_focus: str,
        latest_thought: str,
        reflection_triggered: bool,
    ) -> str:
        return (
            f"用户输入：{user_text}\n"
            f"当前关注点：{dominant_focus}\n"
            f"最新内心想法：{latest_thought}\n"
            f"是否触发反思：{'yes' if reflection_triggered else 'no'}\n"
            "请生成对用户的即时回复。要求：优先直接解决问题，简洁具体，通常使用 1 到 3 句话。"
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