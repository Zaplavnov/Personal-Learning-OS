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

## Первая учебная вертикаль

Модуль `app/modules/materials` реализует поток:

```text
материал → активная учебная сессия → заметка → завершение с reflection
```

Поддерживаются ссылки на видео, статьи, книги/главы, notebooks и repositories. События `material.created`, `learning_session.started`, `note.created` и `learning_activity.completed` записываются в transactional outbox; worker на этом этапе не запускается.
