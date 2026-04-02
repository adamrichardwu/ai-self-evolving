from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Self-Evolving MVP"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    redis_url: str = "redis://localhost:6379/0"
    language_background_loop_enabled: bool = True
    language_thought_interval_seconds: float = 5.0
    local_model_path: str | None = "modelscope_cache/Qwen/Qwen2___5-0___5B-Instruct"
    local_model_max_new_tokens: int = 160
    local_model_top_p: float = 0.88
    local_model_repetition_penalty: float = 1.08
    llm_api_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_timeout_seconds: float = 30.0
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    celery_local_data_dir: str = ".celery"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def resolved_celery_broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def resolved_celery_result_backend(self) -> str:
        if self.celery_result_backend:
            return self.celery_result_backend
        if self.resolved_celery_broker_url == "filesystem://":
            return Path(self.celery_local_data_dir).resolve().joinpath("results").as_uri()
        return self.redis_url


settings = Settings()
