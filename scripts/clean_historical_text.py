import argparse
import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.consciousness.goals.persistence import GoalRecord
from packages.consciousness.language.persistence import LanguageSummaryRecord
from packages.consciousness.runtime.persistence import RuntimeTraceRecord
from packages.consciousness.self_model.persistence import SelfModelRecord
from packages.infra.db.session import SessionLocal, init_db


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _normalize_mixed_spacing(text: str) -> str:
    normalized = _normalize_whitespace(text)
    if not normalized:
        return ""
    normalized = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", normalized)
    normalized = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[，。！？；：,.!?;:])", "", normalized)
    normalized = re.sub(r"(?<=[，。！？；：,.!?;:])\s+(?=[\u4e00-\u9fff])", "", normalized)
    return normalized


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return _normalize_mixed_spacing(value)
    if isinstance(value, Mapping):
        return {key: _sanitize_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_sanitize_value(item) for item in value]
    return value


@dataclass(slots=True)
class CleanupStats:
    rows_changed: int = 0
    fields_changed: Counter | None = None

    def __post_init__(self) -> None:
        if self.fields_changed is None:
            self.fields_changed = Counter()


def _update_record_fields(record: Any, field_names: list[str], stats: CleanupStats, apply_changes: bool) -> None:
    row_changed = False
    for field_name in field_names:
        current_value = getattr(record, field_name)
        cleaned_value = _sanitize_value(current_value)
        if cleaned_value == current_value:
            continue
        row_changed = True
        stats.fields_changed[field_name] += 1
        if apply_changes:
            setattr(record, field_name, cleaned_value)
    if row_changed:
        stats.rows_changed += 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Sanitize historical summary and goal text in local.db")
    parser.add_argument("--apply", action="store_true", help="Persist changes instead of running in dry-run mode")
    args = parser.parse_args()

    init_db()
    session = SessionLocal()

    targets: list[tuple[str, Any, list[str]]] = [
        ("language_summaries", LanguageSummaryRecord, ["summary_text", "last_focus"]),
        ("goals", GoalRecord, ["title", "description", "success_criteria"]),
        ("runtime_traces", RuntimeTraceRecord, ["current_focus", "dominant_goal", "summary_text", "thought_focus"]),
        ("self_models", SelfModelRecord, ["attention_json", "goals_json"]),
    ]

    try:
        report: dict[str, CleanupStats] = {}
        for label, model, field_names in targets:
            stats = CleanupStats()
            records = session.scalars(select(model)).all()
            for record in records:
                _update_record_fields(record, field_names, stats, apply_changes=args.apply)
            report[label] = stats

        if args.apply:
            session.commit()
        else:
            session.rollback()

        mode = "apply" if args.apply else "dry-run"
        print(f"historical_text_cleanup mode={mode}")
        total_rows = 0
        total_fields = 0
        for label, stats in report.items():
            total_rows += stats.rows_changed
            total_fields += sum(stats.fields_changed.values())
            print(
                f"{label}: rows_changed={stats.rows_changed} "
                f"fields_changed={dict(stats.fields_changed)}"
            )
        print(f"totals: rows_changed={total_rows} fields_changed={total_fields}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())