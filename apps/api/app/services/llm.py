from typing import Any

import httpx

from apps.api.app.core.settings import settings
from apps.api.app.schemas.language import LLMStatusResponse
from apps.api.app.services.local_llm import LocalTransformersLLM


local_llm = LocalTransformersLLM()


class OpenAICompatibleLLM:
    def is_configured(self) -> bool:
        return bool(settings.llm_api_base_url and settings.llm_model)

    def status(self) -> LLMStatusResponse:
        local_ready, local_detail = local_llm.status()
        if local_ready:
            return LLMStatusResponse(
                configured=True,
                reachable=True,
                mode="local-transformers",
                api_base_url=None,
                model=settings.local_model_path,
                detail=local_detail,
            )

        if not self.is_configured():
            return LLMStatusResponse(
                configured=False,
                reachable=False,
                mode="template-fallback",
                api_base_url=settings.llm_api_base_url,
                model=settings.llm_model,
                detail="LLM_API_BASE_URL or LLM_MODEL is not configured.",
            )

        url = settings.llm_api_base_url.rstrip("/") + "/models"
        headers = {"Content-Type": "application/json"}
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"

        try:
            with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            return LLMStatusResponse(
                configured=True,
                reachable=False,
                mode="template-fallback",
                api_base_url=settings.llm_api_base_url,
                model=settings.llm_model,
                detail=f"Configured but unreachable: {exc.__class__.__name__}",
            )

        return LLMStatusResponse(
            configured=True,
            reachable=True,
            mode="local-llm",
            api_base_url=settings.llm_api_base_url,
            model=settings.llm_model,
            detail="Configured endpoint responded successfully.",
        )

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str | None:
        local_output = local_llm.generate(system_prompt, user_prompt, temperature=temperature)
        if local_output:
            return local_output

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