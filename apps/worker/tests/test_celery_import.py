from apps.worker.app.celery_app import celery_app


def test_celery_app_name() -> None:
    assert celery_app.main == "ai_self_evolving"
