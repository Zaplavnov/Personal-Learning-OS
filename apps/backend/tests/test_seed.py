from sqlalchemy.dialects import postgresql

from app.core.config import Settings
from app.db.seed import build_local_user_statement
from app.db.seed_learning_spaces import GOAL_ID, SPACE_ID


def test_local_user_seed_is_idempotent() -> None:
    statement = build_local_user_statement(Settings())
    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "ON CONFLICT (email) DO UPDATE" in sql
    assert "users" in sql


def test_learning_space_seed_uses_stable_ids() -> None:
    assert str(SPACE_ID) == "10000000-0000-4000-8000-000000000001"
    assert str(GOAL_ID) == "20000000-0000-4000-8000-000000000001"
