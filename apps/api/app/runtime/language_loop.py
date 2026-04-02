from threading import Event, Thread

from apps.api.app.services.language import run_background_language_cycles
from packages.infra.db.session import SessionLocal


class LanguageBackgroundLoop:
    def __init__(self, interval_seconds: float) -> None:
        self.interval_seconds = interval_seconds
        self._stop_event = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = Thread(target=self._run, name="language-background-loop", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            try:
                with SessionLocal() as session:
                    run_background_language_cycles(session)
            except Exception:
                continue