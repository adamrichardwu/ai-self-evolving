from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = "sqlite+pysqlite:///./local.db"


class Base(DeclarativeBase):
	pass


engine = create_engine(
	DATABASE_URL,
	future=True,
	connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
	session = SessionLocal()
	try:
		yield session
	finally:
		session.close()


def _ensure_sqlite_schema() -> None:
	if not DATABASE_URL.startswith("sqlite"):
		return

	with engine.begin() as connection:
		tables = {
			row[0]
			for row in connection.execute(
				text("SELECT name FROM sqlite_master WHERE type='table'")
			).all()
		}

		if "language_summaries" in tables:
			existing_columns = {
				row[1]
				for row in connection.execute(text("PRAGMA table_info(language_summaries)")).all()
			}
			column_definitions = {
				"counterpart_name": "VARCHAR(128) NOT NULL DEFAULT ''",
				"relationship_type": "VARCHAR(64) NOT NULL DEFAULT ''",
				"identity_status": "VARCHAR(32) NOT NULL DEFAULT 'unanchored'",
			}
			for column_name, definition in column_definitions.items():
				if column_name not in existing_columns:
					connection.execute(
						text(f"ALTER TABLE language_summaries ADD COLUMN {column_name} {definition}")
					)

		if "evolution_runs" in tables:
			existing_columns = {
				row[1]
				for row in connection.execute(text("PRAGMA table_info(evolution_runs)")).all()
			}
			column_definitions = {
				"baseline_benchmark_score": "FLOAT NOT NULL DEFAULT 0.0",
				"benchmark_score": "FLOAT NOT NULL DEFAULT 0.0",
				"utility_score": "FLOAT NOT NULL DEFAULT 0.0",
				"verdict": "VARCHAR(32) NOT NULL DEFAULT 'needs_review'",
				"benchmark_results_json": "JSON NOT NULL DEFAULT '[]'",
			}
			for column_name, definition in column_definitions.items():
				if column_name not in existing_columns:
					connection.execute(
						text(f"ALTER TABLE evolution_runs ADD COLUMN {column_name} {definition}")
					)


def init_db() -> None:
	from packages.consciousness.language import persistence as _language_persistence  # noqa: F401
	from packages.consciousness.runtime import persistence as _runtime_persistence  # noqa: F401
	from packages.evolution import persistence as _evolution_persistence  # noqa: F401

	Base.metadata.create_all(bind=engine)
	_ensure_sqlite_schema()
