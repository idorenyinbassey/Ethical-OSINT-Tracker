import os
from sqlmodel import SQLModel, create_engine, Session

DB_URL = os.getenv("DB_URL", "sqlite:///./dev.db")

engine = create_engine(DB_URL, echo=False)

def init_db():
    # Import models so SQLModel knows them
    from app.models.user import User  # noqa: F401
    from app.models.investigation import Investigation  # noqa: F401
    from app.models.api_config import APIConfig  # noqa: F401
    from app.models.case import Case  # noqa: F401
    from app.models.intelligence_report import IntelligenceReport  # noqa: F401
    from app.models.team import Team, TeamMember  # noqa: F401
    SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)
