# Personal Learning OS: последовательные ТЗ для Codex

Репозиторий: <https://github.com/Zaplavnov/Personal-Learning-OS>

Документ составлен по состоянию ветки `main` после коммита `e152def6b79dbd724baea60e4051e5bd094f2d4d` от 11 июля 2026 года.

## 1. Что сейчас находится в репозитории

В репозитории уже есть хорошая продуктовая основа:

- `docs/product_concept.md` — полное продуктовое видение;
- `docs/product_overview.md` — краткое описание продукта;
- `docs/technical_architecture.md` — целевая архитектура и этапы;
- `UI/Personal-Learning-OS-UI/` — работающий интерактивный UI-прототип;
- `UI/Personal-Learning-OS-UI.zip` — архив того же прототипа.

Текущий UI уже показывает:

- экран «Сегодня»;
- пространства обучения;
- карту знаний;
- материалы;
- календарь;
- AI-наставника;
- окно повторения;
- light/dark theme.

Но сейчас это именно прототип:

- почти весь интерфейс находится в одном `app/page.tsx`;
- переходы между разделами реализованы через локальный React state, а не через маршруты;
- данные захардкожены в компонентах;
- серверной предметной модели ещё нет;
- `db/schema.ts` пуст;
- backend отсутствует;
- Docker Compose для всего продукта отсутствует;
- UI основан на Vinext/Cloudflare-стартере с D1/Worker-заготовками, тогда как продуктовая архитектура предполагает self-hosted Next.js + FastAPI + PostgreSQL;
- в Git одновременно лежат распакованный UI и ZIP с его копией.

## 2. Принятое направление базовой версии

Для первого реально работающего сервиса предлагается:

```text
Frontend: Next.js + React + TypeScript
Backend: FastAPI + SQLAlchemy 2 + Alembic
Database: PostgreSQL
Local infrastructure: Docker Compose
Tests: Pytest + frontend lint/typecheck + Playwright smoke later
```

На первом этапе сознательно не добавлять:

- физические микросервисы;
- Kubernetes;
- Kafka;
- сложную авторизацию;
- pgvector и embeddings до появления данных;
- полноценный RAG;
- автоматическое распознавание всех типов материалов;
- двустороннюю запись в Obsidian;
- ML-персонализацию.

Сервис личный и self-hosted, поэтому до появления многопользовательского сценария использовать режим одного локального пользователя. При этом у предметных таблиц сразу может быть `user_id`, чтобы не закрыть путь к авторизации в будущем.

## 3. Как использовать задания

1. Выполнять задания строго по порядку.
2. Каждое задание отправлять Codex отдельным сообщением.
3. После каждого задания проверять результат локально и коммитить его отдельно.
4. Не смешивать соседние этапы в один большой PR.
5. Перед каждым следующим этапом сообщать Codex, что предыдущий уже реализован и находится в текущей ветке.

---

# ТЗ 1. Привести репозиторий и frontend к рабочей структуре

## Готовый промпт для Codex

```markdown
Работаем в репозитории Personal-Learning-OS. Сначала изучи `docs/product_concept.md`, `docs/product_overview.md`, `docs/technical_architecture.md` и текущий UI в `UI/Personal-Learning-OS-UI`.

Задача: превратить текущий UI-прототип в нормальную основу frontend-приложения, не меняя выбранный дизайн «Тихий фокус».

### Целевая структура

Создай структуру:

personal-learning-os/
├── apps/
│   └── frontend/
├── docs/
├── infrastructure/
├── .env.example
├── docker-compose.yml
└── README.md

На этом шаге `docker-compose.yml` может содержать только frontend либо быть подготовленным для следующих сервисов, но команда локального запуска frontend должна работать.

### Что сделать

1. Перенеси исходники из `UI/Personal-Learning-OS-UI` в `apps/frontend`.
2. Удали из рабочей архитектуры зависимость от Vinext, Wrangler, Cloudflare Worker, D1 и Sites-скриптов.
3. Переведи frontend на стандартные команды Next.js:
   - `npm run dev` → `next dev`;
   - `npm run build` → `next build`;
   - `npm run start` → `next start`;
   - добавь `lint` и `typecheck`.
4. Не меняй визуальный стиль, light/dark theme и основную композицию экранов.
5. Раздели огромный `app/page.tsx`:
   - `app/(app)/layout.tsx` — общий shell;
   - `app/(app)/today/page.tsx`;
   - `app/(app)/spaces/page.tsx`;
   - `app/(app)/graph/page.tsx`;
   - `app/(app)/materials/page.tsx`;
   - `app/(app)/calendar/page.tsx`;
   - `app/(app)/tutor/page.tsx`;
   - `components/layout/`;
   - `components/ui/`;
   - `features/` для крупных предметных блоков.
6. Навигацию реализуй через реальные маршруты Next.js, а не через `useState<Page>`.
7. Вынеси демонстрационные данные в `src/mocks` или `lib/mock-data.ts`. Компоненты не должны содержать большие inline-массивы.
8. Приведи `globals.css` к читаемому форматированию. Сохрани CSS variables обеих тем. Не заменяй дизайн на стандартный шаблон Tailwind.
9. Исправь metadata:
   - язык `ru`;
   - title `Personal Learning OS`;
   - осмысленное description.
10. Удали ZIP-копию UI из репозитория. Исходники должны существовать в одном месте.
11. Обнови корневой README: назначение проекта, структура, требования, команды запуска.
12. Добавь `.env.example`, даже если на этом этапе переменных мало.

### Ограничения

- Не добавляй backend.
- Не добавляй базу данных.
- Не реализуй авторизацию.
- Не подключай внешние API.
- Не переделывай дизайн.
- Не оставляй два конкурирующих frontend-каркаса.

### Критерии приёмки

- `cd apps/frontend && npm ci` проходит;
- `npm run lint` проходит;
- `npm run typecheck` проходит;
- `npm run build` проходит;
- все пункты sidebar открывают отдельные URL;
- light/dark theme работает и сохраняется после reload;
- страницы адаптируются под desktop и mobile;
- в Git нет `node_modules`, `.next`, `dist`, `.wrangler`, архивов с копиями исходников.

### В конце работы

Покажи:

1. итоговое дерево файлов;
2. список удалённых Cloudflare/Vinext-зависимостей;
3. команды проверки и их результаты;
4. какие места пока используют mock data.
```

## Результат этапа

Чистый frontend с настоящим routing и сохранённым дизайном. Он всё ещё работает на mocks, но готов к подключению API.

---

# ТЗ 2. Поднять backend, PostgreSQL и общий Docker Compose

## Готовый промпт для Codex

```markdown
Предыдущий этап завершён: frontend находится в `apps/frontend` и собирается стандартным Next.js.

Задача: создать backend-фундамент Personal Learning OS и поднять frontend + backend + PostgreSQL одной командой Docker Compose.

Сначала изучи `docs/technical_architecture.md`. Реализуй модульный монолит, но не создавай физические микросервисы.

### Целевая структура backend

apps/backend/
├── app/
│   ├── api/
│   │   └── v1/
│   ├── core/
│   ├── db/
│   ├── modules/
│   ├── common/
│   └── main.py
├── alembic/
├── tests/
├── pyproject.toml
├── alembic.ini
└── Dockerfile

### Стек

- Python 3.12;
- FastAPI;
- Pydantic v2 + pydantic-settings;
- SQLAlchemy 2 async;
- asyncpg;
- Alembic;
- pytest + pytest-asyncio;
- Ruff;
- PostgreSQL 16.

### Что сделать

1. Создай FastAPI application factory или аккуратную точку входа.
2. Добавь конфигурацию через environment variables.
3. Добавь единый формат ошибок API:

   {
     "error": {
       "code": "string_code",
       "message": "Human readable message",
       "details": {}
     }
   }

4. Добавь request ID и структурированные логи.
5. Реализуй endpoints:
   - `GET /health/live`;
   - `GET /health/ready`;
   - `GET /api/v1/meta`.
6. Создай базовые таблицы:
   - `users`;
   - `outbox_events`;
   - `jobs`.
7. Для single-user MVP добавь idempotent seed локального пользователя. Не делай login/password.
8. Настрой Alembic и создай первую миграцию.
9. Добавь CORS только для адреса frontend из environment.
10. Создай корневой `docker-compose.yml`:
    - `postgres`;
    - `backend`;
    - `frontend`.
11. Добавь healthchecks и зависимости запуска.
12. Добавь named volume для PostgreSQL.
13. Добавь `.env.example` со всеми переменными без секретных значений.
14. В frontend создай типизированный API client и страницу/индикатор состояния backend. Не подключай предметные mocks к API на этом этапе.
15. Обнови README командами:
    - запуск через Docker Compose;
    - запуск frontend/backend отдельно;
    - миграции;
    - тесты.

### Ограничения

- Не добавляй Redis и MinIO, пока они не используются.
- Не добавляй Celery/Dramatiq.
- Не добавляй LLM.
- Не реализуй полноценную auth-систему.
- Не используй SQLite как production/local-compose database.

### Критерии приёмки

- `docker compose up --build` поднимает три сервиса;
- frontend доступен и показывает, что backend готов;
- `/health/live` отвечает без обращения к БД;
- `/health/ready` проверяет соединение с PostgreSQL;
- `alembic upgrade head` выполняется;
- seed повторяем и не создаёт дубли;
- backend tests проходят;
- Ruff проходит;
- frontend lint/typecheck/build продолжают проходить.

### В конце работы

Покажи архитектуру backend, список env variables, миграцию, команды проверки и их фактические результаты.
```

## Результат этапа

Проект запускается одной командой и имеет настоящий backend с PostgreSQL, но пока без предметных сущностей.

---

# ТЗ 3. Первая предметная вертикаль: Learning Space и Learning Goal

## Готовый промпт для Codex

```markdown
Frontend, FastAPI и PostgreSQL уже подняты. Задача: реализовать первую полную вертикаль Learning Space + Learning Goal от миграции до UI.

### Предметные правила

Learning Space — долгосрочная область обучения.
Learning Goal — конкретная цель внутри пространства.
У пространства может быть несколько целей, но только одна текущая active goal.

### Backend

Создай модуль `learning_spaces` с разделением domain/application/infrastructure/api без избыточного enterprise boilerplate.

Таблицы:

learning_spaces:
- id UUID PK;
- user_id FK users;
- title;
- description nullable;
- color nullable;
- status: active | archived;
- created_at;
- updated_at.

learning_goals:
- id UUID PK;
- learning_space_id FK;
- title;
- description nullable;
- priority integer;
- status: active | paused | completed;
- target_date nullable;
- expected_capabilities JSONB default [];
- completion_criteria JSONB default [];
- created_at;
- updated_at.

Обеспечь правило «не больше одной active goal на пространство» на уровне application logic и, если разумно, partial unique index.

Endpoints:

- `POST /api/v1/learning-spaces`;
- `GET /api/v1/learning-spaces`;
- `GET /api/v1/learning-spaces/{space_id}`;
- `PATCH /api/v1/learning-spaces/{space_id}`;
- `POST /api/v1/learning-spaces/{space_id}/goals`;
- `PATCH /api/v1/learning-goals/{goal_id}`;
- `POST /api/v1/learning-goals/{goal_id}/activate`.

Добавь Pydantic schemas, repositories, use cases и тесты правил.

### Frontend

1. Подключи страницу `/spaces` к API.
2. Реализуй создание пространства.
3. Реализуй detail route `/spaces/[spaceId]`.
4. Реализуй создание и активацию цели.
5. Сохрани визуальный стиль текущего прототипа.
6. Добавь loading, empty, error states.
7. Удали mocks пространства и цели только после подключения API.
8. Используй серверные данные, а не localStorage.

### Seed

Добавь dev seed:

- пространство «Линейная алгебра»;
- цель «Понять геометрический смысл линейных преобразований».

Seed должен быть idempotent и запускаться отдельной командой.

### Критерии приёмки

- созданное пространство сохраняется после перезапуска контейнеров;
- можно создать цель и сделать её активной;
- активация новой цели деактивирует или ставит на паузу предыдущую;
- detail route работает после прямого reload;
- API не позволяет обращаться к объектам другого user_id;
- backend unit/API tests проходят;
- frontend lint/typecheck/build проходят;
- в UI нет захардкоженного количества пространств и целей.

Не добавляй пока материалы, концепции, календарь и AI.
```

## Результат этапа

Появляется первый настоящий пользовательский объект: можно создать направление обучения и сформулировать текущую цель.

---

# ТЗ 4. Материалы, учебная сессия и заметка с таймкодом

## Готовый промпт для Codex

```markdown
Learning Space и Learning Goal уже работают через API. Теперь реализуй первую реально полезную учебную вертикаль:

материал → учебная сессия → заметка.

### Scope MVP

Поддержать только:

- URL/YouTube как ссылку без обязательного transcript ingestion;
- статью;
- книгу/главу как вручную созданную запись;
- собственный notebook/repository как ссылку.

Не загружать PDF и видеофайлы на этом этапе.

### Data model

materials:
- id UUID;
- user_id;
- learning_space_id;
- type: video | article | book | notebook | repository | other;
- title;
- url nullable;
- author nullable;
- description nullable;
- status: active | completed | archived;
- estimated_minutes nullable;
- metadata JSONB default {};
- created_at;
- updated_at.

learning_sessions:
- id UUID;
- material_id;
- user_id;
- started_at;
- ended_at nullable;
- start_position_seconds nullable;
- end_position_seconds nullable;
- reflection nullable;
- status: active | completed | abandoned.

notes:
- id UUID;
- user_id;
- learning_space_id;
- material_id nullable;
- learning_session_id nullable;
- body TEXT;
- source_position_seconds nullable;
- note_type: insight | question | gap | example | general;
- created_at;
- updated_at.

### API

- CRUD create/list/detail/update для materials;
- `POST /materials/{id}/sessions`;
- `POST /learning-sessions/{id}/complete`;
- `POST /notes`;
- `PATCH /notes/{id}`;
- `GET /materials/{id}/notes`;
- фильтр материалов по learning_space_id и type.

### Frontend

1. Подключи `/materials` к API.
2. Добавь modal/drawer создания материала.
3. Создай `/materials/[materialId]`.
4. На detail page реализуй:
   - данные материала;
   - кнопку «Начать сессию»;
   - таймер длительности текущей сессии;
   - поле позиции/таймкода для video;
   - быстрое создание заметки;
   - список заметок;
   - завершение сессии с короткой reflection.
5. Не пытайся обходить ограничения YouTube iframe. Для MVP достаточно ссылки/встраивания там, где это разрешено.
6. Оптимистичный UI допустим, но ошибка API должна быть видимой.

### Domain events

После операций записывай в `outbox_events`:

- `material.created`;
- `learning_session.started`;
- `note.created`;
- `learning_activity.completed`.

Сейчас события только сохраняются транзакционно. Worker пока не нужен.

### Тесты

- нельзя создать session для чужого material;
- одновременно допускается не более одной active session пользователя;
- complete session идемпотентен либо возвращает понятную domain error;
- timestamp не может быть отрицательным;
- note корректно связывается с material/session/space;
- outbox event создаётся в той же транзакции.

### Критерии приёмки

Пользователь может создать материал, открыть его, начать сессию, сохранить заметку с таймкодом, завершить сессию и увидеть данные после reload.

Не добавляй embeddings, transcript, LLM и object storage.
```

## Результат этапа

Сервис впервые можно использовать во время реального занятия.

---

# ТЗ 5. Концепции, связи и привязка заметок

## Готовый промпт для Codex

```markdown
Материалы, сессии и заметки уже работают. Теперь перенеси центр системы с заметок на концепции.

### Data model

concepts:
- id UUID;
- user_id;
- learning_space_id;
- title;
- normalized_title;
- short_description nullable;
- formal_definition nullable;
- user_explanation nullable;
- status: discovered | learning | stable | archived;
- created_at;
- updated_at.

concept_relations:
- id UUID;
- source_concept_id;
- target_concept_id;
- relation_type: prerequisite | related | contrasts | part_of | applies_to;
- description nullable;
- created_at;
- unique constraint на пару + relation_type.

concept_note_links:
- concept_id;
- note_id;
- link_type: evidence | question | gap | example | mention;
- created_at;
- composite unique constraint.

concept_aliases:
- id;
- concept_id;
- alias;
- normalized_alias;
- unique в рамках пользователя/пространства.

### Правила

- relation не может ссылаться сама на себя;
- нельзя связывать концепции разных пользователей;
- дубликаты title/alias в одном space должны возвращать понятный конфликт;
- merge/split пока не реализовывать, только предусмотреть чистые модели.

### API

- CRUD concepts;
- add/delete relation;
- link/unlink note;
- graph endpoint `GET /learning-spaces/{id}/concept-graph`;
- concept detail read model, включающий relations, linked notes и materials через notes.

### Frontend

1. Сделай `/graph?spaceId=...` работающим на API.
2. Можно оставить текущую простую CSS-визуализацию либо подключить React Flow, если это существенно упрощает интерактивность. Не трать время на физический layout уровня production.
3. Реализуй `/concepts/[conceptId]`:
   - описание;
   - user explanation;
   - входящие/исходящие связи;
   - заметки и источники;
   - открытые вопросы/пробелы.
4. В material note flow добавь выбор существующей концепции или быстрое создание новой.
5. Удали concept mocks.

### Seed

Добавь небольшой связный граф линейной алгебры, но только в dev seed.

### Тесты и приёмка

- заметка связывается с одной или несколькими концепциями;
- graph endpoint возвращает nodes и edges стабильного контракта;
- клик по узлу открывает real detail route;
- удаление relation не удаляет concepts;
- удаление note корректно удаляет link;
- API и frontend tests проходят.

Не добавляй автоматическое извлечение концепций, embeddings или AI suggestions. Все действия пока ручные.
```

## Результат этапа

Материалы и заметки начинают собираться вокруг концепций — появляется главное отличие продукта от обычного заметочника.

---

# ТЗ 6. Knowledge State v0 и осмысленное повторение

## Готовый промпт для Codex

```markdown
Концепции и связи уже работают. Реализуй rule-based Knowledge State v0 и очередь повторений без LLM.

### Измерения состояния

Для каждой concept отслеживать шкалы 0–100:

- recall;
- explanation;
- structure;
- comparison;
- application;
- hypothesis_generation;
- stability.

Также хранить confidence расчёта 0–1 и `last_evidence_at`.

### Data model

concept_evidence:
- id UUID;
- concept_id;
- user_id;
- evidence_type: viewed | note_created | user_explanation | review_answer | task_solved | applied_in_project | manual_adjustment;
- dimension;
- score_delta;
- strength 0..1;
- source_type;
- source_id nullable;
- metadata JSONB;
- occurred_at.

concept_states:
- concept_id PK;
- все семь dimension scores;
- confidence;
- last_evidence_at;
- next_review_at nullable;
- version integer;
- updated_at.

review_items:
- id UUID;
- concept_id;
- review_type: recall | explain | compare | apply | structure;
- prompt;
- expected_points JSONB default [];
- status: pending | completed | skipped;
- due_at;
- created_at.

review_attempts:
- id UUID;
- review_item_id;
- answer TEXT;
- self_rating 1..5;
- result: failed | partial | passed;
- feedback nullable;
- created_at.

### Scoring v0

Сделай прозрачный отдельный scoring service с чистыми функциями и unit tests.

Для MVP:

- пользователь сам выбирает failed/partial/passed или self-rating;
- никакой LLM-оценки;
- успешный review увеличивает соответствующее измерение и stability;
- неуспешный уменьшает confidence/score умеренно, без обнуления;
- повторение через больший интервал даёт больше evidence strength;
- viewed и note_created дают только слабое evidence;
- applied_in_project и task_solved дают сильное evidence;
- хранить историю evidence, не только итоговый процент.

Алгоритм интервала может быть простой эвристикой, но должен быть документирован и детерминирован.

### API

- получить state концепции;
- получить timeline evidence;
- создать manual evidence;
- получить due reviews;
- создать review item вручную;
- submit attempt;
- skip/reschedule review.

### Frontend

1. На concept detail покажи многомерное состояние, confidence и объяснение «почему система так считает».
2. Создай полноценный route `/reviews` и review session.
3. Подключи существующий modal/дизайн повторения к реальным review items.
4. После ответа state должен обновляться без reload.
5. На graph используй state для визуальных статусов узлов.

### События

- `review.answered`;
- `knowledge_state.updated`.

### Критерии приёмки

- один и тот же набор evidence всегда даёт один state;
- state можно восстановить/пересчитать из evidence;
- пользователь видит происхождение оценки;
- слабое действие «просмотрено» не делает концепцию освоенной;
- review attempt обновляет state и следующий due date транзакционно;
- unit tests покрывают scoring edge cases.

Не добавляй LLM evaluation и генерацию вопросов. Review prompt пока создаётся вручную или из фиксированных шаблонов.
```

## Результат этапа

Система начинает отличать знакомство с темой от способности объяснить или применить её.

---

# ТЗ 7. Экран «Сегодня», базовый scheduler и первый цельный MVP

## Готовый промпт для Codex

```markdown
Learning spaces, materials, sessions, notes, concepts, knowledge state и reviews уже работают. Теперь свяжи их в ежедневный пользовательский цикл через базовый scheduler и экран «Сегодня».

### Цель

Главный экран должен отвечать:

1. Что делать сейчас?
2. Почему именно это?
3. Сколько времени займёт?
4. Какую грань понимания укрепит?

### Data model

calendar_items:
- id UUID;
- user_id;
- learning_space_id nullable;
- item_type: material_session | review | explain | practice | gap_work;
- source_type;
- source_id nullable;
- title;
- planned_start nullable;
- estimated_minutes;
- status: planned | in_progress | completed | skipped;
- flexibility: fixed | flexible;
- priority integer;
- rationale;
- created_at;
- updated_at.

schedule_versions:
- id UUID;
- user_id;
- reason;
- snapshot JSONB;
- created_at.

### Scheduler v0

Реализуй детерминированный heuristic scheduler, который формирует кандидаты из:

- due reviews;
- активной goal;
- незавершённых material sessions;
- concepts с низкими explanation/application;
- notes типа gap/question без закрытия.

Пример приоритета:

- просроченное review;
- активный gap по prerequisite;
- продолжение текущей session;
- действие активной goal;
- новый материал.

Scheduler не должен создавать бесконечный долг. На один день возвращать ограниченный набор действий под `available_minutes`, по умолчанию 45.

### API/read model

Создай `GET /api/v1/today?available_minutes=45`.

Ответ должен включать:

- active space;
- active goal;
- primary action;
- secondary actions;
- due review count;
- open gap count;
- knowledge stability summary;
- next item;
- rationale для каждого действия.

Добавь:

- `GET /api/v1/calendar?from=&to=`;
- `POST /api/v1/calendar/recalculate`;
- `PATCH /api/v1/calendar-items/{id}`.

### Frontend

1. Подключи существующий экран `/today` к read model.
2. Удали все mock-значения с главного экрана.
3. Primary action должен вести в реальный сценарий:
   - review;
   - material session;
   - concept explanation.
4. Покажи rationale человеческим языком.
5. Подключи `/calendar` к реальным calendar items.
6. Реализуй изменение доступного времени на сегодня: 15/30/45/60/90 минут.
7. После завершения действия экран Today обновляется и предлагает следующее.
8. При пустых данных показывай onboarding action: создать пространство или добавить материал.

### End-to-end seed/demo

Создай команду demo seed, которая добавляет:

- пространство «Линейная алгебра»;
- активную цель;
- 2–3 материала;
- несколько заметок;
- 6–8 концепций и связи;
- состояния разной силы;
- due reviews;
- calendar items.

### Critical E2E

Добавь минимальный Playwright test:

1. открыть Today;
2. увидеть действие;
3. начать review;
4. отправить self-rated attempt;
5. вернуться на Today;
6. увидеть обновлённое состояние/следующее действие.

### Критерии готовности MVP

- `docker compose up --build` поднимает весь сервис;
- чистая база проходит migrations и demo seed;
- пользователь проходит полный цикл:
  пространство → цель → материал → сессия → заметка → концепция → повторение → обновление state → новое действие Today;
- UI не зависит от mocks;
- scheduler объясняет выбор;
- backend tests, frontend checks и critical E2E проходят;
- README содержит сценарий первого запуска и backup PostgreSQL volume.

Не добавляй AI-наставника, embeddings и Obsidian sync в этот этап. Экран Tutor может оставаться честно помеченным как «следующий этап», но не должен имитировать работающий AI.
```

## Результат этапа

Это первая версия, которую уже можно использовать для собственного обучения. Она реализует ядро продукта без AI-магии и без преждевременной инфраструктурной сложности.

---

# 4. Что делать после базового MVP

Следующие вертикали лучше добавлять только после нескольких недель личного использования:

1. read-only Obsidian sync;
2. URL/YouTube/PDF ingestion workers;
3. transcript и material segments;
4. pgvector и semantic retrieval;
5. AI-suggestions концепций и связей с обязательным подтверждением;
6. LLM evaluation ответов рядом с self-rating;
7. AI-наставник с provenance и tool calls;
8. адаптивное перепланирование по истории;
9. ML next-best-action после накопления собственных данных.

## Почему AI не входит в первые семь ТЗ

Сейчас важнее проверить сам продуктовый цикл. Если без LLM пользователь не возвращается к материалам, не связывает заметки с концепциями и не проходит повторения, AI только скроет слабость основы. Когда базовая вертикаль работает, AI можно подключать к конкретным узким операциям:

- предложить концепцию для заметки;
- сгенерировать несколько вариантов вопроса;
- оценить ответ вместе с прозрачными критериями;
- найти похожие фрагменты;
- объяснить причину следующего действия.

## Рекомендуемые границы коммитов

```text
1. chore: restructure frontend and remove hosting-specific scaffold
2. feat: add FastAPI and PostgreSQL foundation
3. feat: add learning spaces and goals
4. feat: add materials sessions and notes
5. feat: add concepts and knowledge graph
6. feat: add knowledge state and reviews
7. feat: add scheduler and today orchestration
```

Каждый этап должен оставлять `main` в запускаемом состоянии.
