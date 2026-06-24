import os
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text

DB_URL = os.getenv("DB_URL", "sqlite:///./dev.db")

engine = create_engine(DB_URL, echo=False)

def _add_column_if_missing(conn, table: str, column: str, col_def: str) -> None:
    try:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}"))
        conn.commit()
    except Exception:
        pass  # column already exists

def init_db():
    # Import models so SQLModel knows them
    from app.models.user import User  # noqa: F401
    from app.models.investigation import Investigation  # noqa: F401
    from app.models.api_config import APIConfig  # noqa: F401
    from app.models.case import Case  # noqa: F401
    from app.models.intelligence_report import IntelligenceReport  # noqa: F401
    from app.models.team import Team, TeamMember  # noqa: F401
    from app.models.case_comment import CaseComment  # noqa: F401
    from app.models.case_note import CaseNote  # noqa: F401
    from app.models.watchlist import WatchlistTarget  # noqa: F401
    from app.models.tracking_link import TrackingLink  # noqa: F401
    from app.models.tracking_hit import TrackingHit  # noqa: F401
    from app.models.audit_log import AuditLog  # noqa: F401
    SQLModel.metadata.create_all(engine)

    # Idempotent column additions for existing tables
    with engine.connect() as conn:
        _add_column_if_missing(conn, "watchlist", "has_alert", "INTEGER NOT NULL DEFAULT 0")
        _add_column_if_missing(conn, "watchlist", "alert_message", "TEXT NOT NULL DEFAULT ''")
        # auditlog was created by old stub model — add missing columns
        _add_column_if_missing(conn, "auditlog", "user_id", "INTEGER")
        _add_column_if_missing(conn, "auditlog", "username", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "auditlog", "action", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "auditlog", "entity_type", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "auditlog", "entity_id", "INTEGER")
        _add_column_if_missing(conn, "auditlog", "ip", "TEXT NOT NULL DEFAULT ''")

def get_session():
    return Session(engine)
