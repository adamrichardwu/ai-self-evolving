from typing import Any

import httpx

from apps.api.app.core.settings import settings


class OpenAICompatibleLLM:
    def is_configured(self) -> bool:
        return bool(settings.llm_api_base_url and settings.llm_model)

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str | None:
        if not self.is_configured():
            return None

        url = settings.llm_api_base_url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"

        payload: dict[str, Any] = {
            "model": settings.llm_model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.HTTPError:
            return None

        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            return None
        message = choices[0].get("message") or {}
        content = (message.get("content") or "").strip()
        return content or None