"""Database engine and session management."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.sqlalchemy_url,
    # Neon's free tier scales compute to zero after ~5 minutes idle, which kills
    # pooled connections. pool_pre_ping validates a connection before handing it
    # out and transparently replaces dead ones; without it, wake-ups surface as
    # intermittent "server closed the connection unexpectedly" errors.
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=5,
    echo=settings.DEBUG and not settings.is_production,
    connect_args={"connect_timeout": 15},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a session that always gets closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
