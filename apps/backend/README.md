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

## Scheduler v0

Модуль `app/modules/scheduler` строит live read model `GET /api/v1/today` и материализованный календарь. Порядок кандидатов фиксирован: overdue review → открытый gap/question → активная material session → слабый prerequisite/concept → active goal → новый материал. Чистая функция сортирует кандидаты и берёт не более пяти действий, сумма которых не превышает `available_minutes`; не поместившиеся действия не переносятся как долг.

```bash
python -m app.db.seed_demo
```

Demo seed добавляет воспроизводимый полный цикл и безопасен для повторного запуска.

## Learning Path

`app/modules/learning_paths` — отдельная проекция существующего concept graph под конкретную Learning Goal. Модуль разделён на domain rules, application use cases, SQLAlchemy infrastructure, API schemas/routes и заменяемый planner interface.

Правила v0:

- `sequence`, `prerequisite`, `optional_branch` и `remediation` участвуют в availability и обязаны оставаться acyclic; `returns_to` — визуальная связь возврата и не блокирует узлы;
- required predecessor должен быть completed/skipped до открытия следующего узла; optional ветка не блокирует основной маршрут;
- completion policy поддерживает верхнеуровневые `all` и `any` с условиями `resource_type/minimum_completed`, `dimension/minimum_score` и `evidence_type/minimum_count`;
- завершение узла двигает current position, но не выставляет Knowledge State;
- active path меняется с optimistic `expected_version`; каждое структурное изменение создаёт snapshot;
- rule engine создаёт remediation suggestion при слабом отсутствующем prerequisite, но применяет её только после Accept.

Основные контракты находятся под `/api/v1/learning-paths`, генерация draft — `POST /api/v1/learning-goals/{goal_id}/path/generate-draft`, история — `/learning-paths/{path_id}/versions`. Полный detail read model возвращает goal, nodes/edges/resources, concept state, progress, current/available nodes, blockers, pending suggestions и последнюю версию.
