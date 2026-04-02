from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from apps.api.app.routes.autobiography import router as autobiography_router
from apps.api.app.routes.consciousness_evaluation import router as consciousness_evaluation_router
from apps.api.app.routes.health import router as health_router
from apps.api.app.routes.language import router as language_router
from apps.api.app.routes.self_model import router as self_model_router
from apps.api.app.routes.social import router as social_router
from apps.api.app.routes.tasks import router as tasks_router
from apps.api.app.core.settings import settings
from apps.api.app.runtime.language_loop import LanguageBackgroundLoop
from packages.infra.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    loop = None
    if settings.language_background_loop_enabled:
        loop = LanguageBackgroundLoop(settings.language_thought_interval_seconds)
        loop.start()
        app.state.language_background_loop = loop
    try:
        yield
    finally:
        if loop is not None:
            loop.stop()


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
    static_console_dir = Path(__file__).resolve().parent / "static" / "console"

    app.include_router(health_router)
    app.include_router(autobiography_router, prefix=settings.api_prefix)
    app.include_router(language_router, prefix=settings.api_prefix)
    app.include_router(tasks_router, prefix=settings.api_prefix)
    app.include_router(self_model_router, prefix=settings.api_prefix)
    app.include_router(social_router, prefix=settings.api_prefix)
    app.include_router(consciousness_evaluation_router, prefix=settings.api_prefix)
    app.mount("/console", StaticFiles(directory=static_console_dir, html=True), name="console")
    return app


app = create_app()
