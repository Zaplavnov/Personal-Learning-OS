# Personal Learning OS — backend

FastAPI-модульный монолит с PostgreSQL, SQLAlchemy 2 async и Alembic.

## Локальная разработка

```bash
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -e ".[dev]"
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload
```

## Проверки

```bash
ruff check .
ruff format --check .
pytest
```
