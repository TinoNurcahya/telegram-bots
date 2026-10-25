"""Repositories package with Dual-Repository factory."""
from typing import Tuple, Any
from src.repositories.database import DatabaseConnection
from src.repositories.coach_repository import ICoachRepository, CoachRepository
from src.repositories.postgres_coach_repository import PostgresCoachRepository


def create_coach_repository(database_url: str = "", database_path: str = "speaking_coach.db") -> Tuple[ICoachRepository, Any]:
    """Factory creating appropriate ICoachRepository and schema initializer.
    
    If database_url starts with 'postgres' or 'postgresql', instantiates PostgresCoachRepository.
    Otherwise, defaults to SQLite CoachRepository.
    """
    if database_url and (database_url.startswith("postgres://") or database_url.startswith("postgresql://")):
        repo = PostgresCoachRepository(dsn=database_url)
        return repo, repo
    else:
        db_conn = DatabaseConnection(db_path=database_path)
        repo = CoachRepository(db_path=database_path)
        return repo, db_conn


__all__ = [
    "DatabaseConnection",
    "ICoachRepository",
    "CoachRepository",
    "PostgresCoachRepository",
    "create_coach_repository",
]
