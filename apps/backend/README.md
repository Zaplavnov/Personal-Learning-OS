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

## Concepts и knowledge graph

Модуль `app/modules/concepts` хранит концепции и типизированные семантические связи внутри Learning Space. API поддерживает CRUD концепций, создание/удаление связей и read model `/api/v1/knowledge-graph`. Knowledge graph не смешивается с отдельным графом учебного пути.

## Knowledge State v0 и повторения

`app/modules/knowledge_state/scoring.py` — изолированный rule-based расчёт без LLM. Состояние всегда восстанавливается из упорядоченной истории `concept_evidence`: для каждого сигнала к выбранной шкале прибавляется `score_delta × strength`, результат ограничивается диапазоном 0–100. Положительное evidence повышает confidence на `0.08 × strength`, отрицательное снижает на `0.04 × strength`; confidence остаётся в диапазоне 0–1.

Сила по умолчанию прозрачна: `viewed=0.15`, `note_created=0.30`, `user_explanation=0.65`, `review_answer=0.70`, `task_solved=0.85`, `applied_in_project=1.0`, `manual_adjustment=0.50`. Для слабых действий верхняя граница strength принудительно ограничена, поэтому просмотр не может сделать концепцию освоенной.

Review использует выбранные пользователем result и self-rating. Сила retrieval равна `min(1, 0.45 + interval_days / 60)`. Следующий интервал детерминирован:

- `failed` — 1 день;
- `partial` — от 3 до 7 дней в зависимости от stability;
- `passed` — от 7 до 27 дней в зависимости от stability.

Attempt, два evidence-сигнала, новый review item, обновлённый state и outbox-события `review.answered`/`knowledge_state.updated` фиксируются одной транзакцией.
