"""
Database Connection Management
Translation Quality Analytics & Continuous Improvement Platform

Provides thread-safe SQLAlchemy 2.0 engine, scoped session factory, and lifecycle helpers.
"""

import logging
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import config
from src.database.models import Base

logger = logging.getLogger(__name__)


def create_db_engine(db_url: Optional[str] = None) -> Engine:
    """
    Creates and configures an SQLAlchemy engine with production connection pooling.
    
    Args:
        db_url: Optional database URL override. Defaults to config.database_url.
    """
    target_url = db_url or config.database_url
    
    # Configure pooling based on database dialect
    if target_url.startswith("sqlite"):
        return create_engine(
            target_url,
            connect_args={"check_same_thread": False},
            echo=False
        )
    
    return create_engine(
        target_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=False
    )


# Primary engine and sessionmaker
engine: Engine = create_db_engine()
SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager providing a transactional database session.
    Commits on success, rolls back on exception, and reliably closes.
    """
    session: Session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error(f"Database transaction error: {exc}", exc_info=True)
        raise
    finally:
        session.close()


def init_db(target_engine: Optional[Engine] = None) -> None:
    """
    Initializes database tables and constraints.
    Creates all defined ORM tables if they do not already exist.
    """
    eng = target_engine or engine
    logger.info("Initializing database schema via SQLAlchemy metadata...")
    Base.metadata.create_all(bind=eng)
    logger.info("Database schema initialized successfully.")


def check_db_health(target_engine: Optional[Engine] = None) -> dict:
    """
    Health check executing a trivial SELECT 1 to verify database connectivity.
    
    Returns:
        dict: Status ('healthy' or 'unhealthy') and connection details or error message.
    """
    eng = target_engine or engine
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "url": str(eng.url).split("@")[-1] if "@" in str(eng.url) else str(eng.url)}
    except Exception as exc:
        logger.warning(f"Database health check failed: {exc}")
        return {"status": "unhealthy", "error": str(exc)}
