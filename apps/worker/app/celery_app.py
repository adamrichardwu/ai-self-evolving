from pathlib import Path

from celery import Celery

from apps.api.app.core.settings import settings

celery_app = Celery(
	"ai_self_evolving",
	broker=settings.resolved_celery_broker_url,
	backend=settings.resolved_celery_result_backend,
	include=[
		"apps.worker.app.tasks.autobiography",
		"apps.worker.app.tasks.core_capability",
		"apps.worker.app.tasks.evaluation",
	],
)
celery_app.conf.task_default_queue = "default"

if settings.resolved_celery_broker_url == "filesystem://":
	base_dir = Path(settings.celery_local_data_dir).resolve()
	broker_queue = base_dir / "broker" / "queue"
	broker_processed = base_dir / "broker" / "processed"
	result_dir = base_dir / "results"

	for path in (broker_queue, broker_processed, result_dir):
		path.mkdir(parents=True, exist_ok=True)

	celery_app.conf.broker_transport_options = {
		"data_folder_in": str(broker_queue),
		"data_folder_out": str(broker_queue),
		"data_folder_processed": str(broker_processed),
	}
