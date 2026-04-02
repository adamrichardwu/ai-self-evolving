from pathlib import Path
from threading import Lock

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from apps.api.app.core.settings import settings


class LocalTransformersLLM:
    def __init__(self) -> None:
        self._lock = Lock()
        self._model = None
        self._tokenizer = None
        self._loaded_path: str | None = None

    def configured_path(self) -> str | None:
        return settings.local_model_path

    def is_configured(self) -> bool:
        path = self.configured_path()
        return bool(path and Path(path).exists())

    def status(self) -> tuple[bool, str]:
        if not self.is_configured():
            return False, "Local model path is not configured or does not exist."
        if self._model is None or self._tokenizer is None:
            return True, "Local model is configured and will load on first request."
        return True, "Local model is loaded and ready."

    @staticmethod
    def _contains_cjk(text: str) -> bool:
        return any("\u4e00" <= character <= "\u9fff" for character in text)

    def _normalize_prompts(self, system_prompt: str, user_prompt: str) -> tuple[str, str]:
        chinese_output = self._contains_cjk(user_prompt)
        language_guard = (
            "默认使用简体中文回答。直接回答用户问题，避免泛泛自我介绍，除非用户明确要求。"
            if chinese_output
            else "Reply in the user's language. Answer directly and avoid generic self-introductions unless asked."
        )
        tightened_system_prompt = (
            f"{system_prompt.strip()}\n\n"
            f"Output policy: {language_guard} Keep the reply concrete and within 1-3 short paragraphs."
        )
        tightened_user_prompt = (
            f"{user_prompt.strip()}\n\n"
            "Return the final answer only. Do not explain hidden reasoning."
        )
        return tightened_system_prompt, tightened_user_prompt

    @staticmethod
    def _clean_output(content: str) -> str:
        cleaned = content.strip()
        for prefix in ("assistant:", "Assistant:", "答复：", "回答：", "最终回答："):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix) :].strip()
        return cleaned

    def _ensure_loaded(self) -> bool:
        model_path = self.configured_path()
        if not model_path or not Path(model_path).exists():
            return False

        if self._model is not None and self._tokenizer is not None and self._loaded_path == model_path:
            return True

        with self._lock:
            if self._model is not None and self._tokenizer is not None and self._loaded_path == model_path:
                return True

            self._tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
            self._model = AutoModelForCausalLM.from_pretrained(
                model_path,
                dtype=torch.float32,
                low_cpu_mem_usage=True,
                trust_remote_code=True,
            )
            self._model.eval()
            self._loaded_path = model_path
        return True

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str | None:
        if not self._ensure_loaded():
            return None

        normalized_system_prompt, normalized_user_prompt = self._normalize_prompts(
            system_prompt,
            user_prompt,
        )

        messages = [
            {"role": "system", "content": normalized_system_prompt},
            {"role": "user", "content": normalized_user_prompt},
        ]

        if hasattr(self._tokenizer, "apply_chat_template"):
            prompt_text = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            prompt_text = f"System: {system_prompt}\nUser: {user_prompt}\nAssistant:"

        inputs = self._tokenizer(prompt_text, return_tensors="pt")
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=settings.local_model_max_new_tokens,
                do_sample=temperature > 0,
                temperature=max(temperature, 0.1),
                top_p=settings.local_model_top_p,
                repetition_penalty=settings.local_model_repetition_penalty,
                pad_token_id=self._tokenizer.eos_token_id,
            )

        generated_tokens = outputs[0][inputs["input_ids"].shape[-1] :]
        content = self._clean_output(self._tokenizer.decode(generated_tokens, skip_special_tokens=True))
        return content or None