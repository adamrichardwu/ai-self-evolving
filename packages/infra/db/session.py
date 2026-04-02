from collections.abc import Generator

from sqlalchemy import create_engine
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


def init_db() -> None:
	Base.metadata.create_all(bind=engine)
