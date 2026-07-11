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

## Демонстрационные Learning Space и Goal

После применения миграций seed можно запускать повторно:

```bash
python -m app.db.seed_learning_spaces
```
