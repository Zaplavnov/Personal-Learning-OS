from sqlalchemy.dialects import postgresql

from app.core.config import Settings
from app.db.seed import build_local_user_statement


def test_local_user_seed_is_idempotent() -> None:
    statement = build_local_user_statement(Settings())
    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "ON CONFLICT (email) DO UPDATE" in sql
    assert "users" in sql
