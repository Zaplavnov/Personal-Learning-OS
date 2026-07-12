# Personal Learning OS

Личная self-hosted система глубокого обучения: материалы, заметки, динамическая карта концепций, повторение, календарь и AI-наставник. Репозиторий содержит Next.js frontend и FastAPI backend, организованный как модульный монолит.

## Структура

```text
Personal-Learning-OS/
├── apps/
│   ├── backend/        # FastAPI, SQLAlchemy async, Alembic
│   └── frontend/       # Next.js App Router
├── docs/               # продуктовая и техническая документация
├── infrastructure/     # инфраструктурные заготовки следующих этапов
├── .env.example
├── docker-compose.yml
└── README.md
```

На текущем этапе используются только PostgreSQL, backend и frontend. Redis, MinIO, workers, LLM и полноценная авторизация намеренно не добавлены.

## Требования

- Docker с Compose plugin;
- для запуска без Docker: Python 3.12 и Node.js 22.13+.

## Запуск всего стека

При необходимости скопируйте `.env.example` в `.env` и измените локальные значения. Значения по умолчанию уже позволяют запустить development-стек:

```bash
docker compose up --build
```

После запуска:

- frontend: <http://localhost:3000>;
- backend API: <http://localhost:8000>;
- OpenAPI: <http://localhost:8000/docs>;
- PostgreSQL: `localhost:5432`.

Backend-контейнер перед запуском API выполняет `alembic upgrade head` и идемпотентный seed локального пользователя. Остановка: `docker compose down`. Для удаления локальных данных PostgreSQL: `docker compose down -v`.

### Первый запуск с демонстрационным учебным циклом

После старта сервисов выполните идемпотентный demo seed и откройте экран Today:

```bash
docker compose exec backend python -m app.db.seed_demo
docker compose exec backend alembic current
```

Откройте <http://localhost:3000/today>. Демонстрационные данные включают пространство «Линейная алгебра», активную цель, три материала, активную учебную сессию, четыре заметки, семь связанных концепций с разными knowledge states, два due review и дневной календарь. Повторный запуск команды не создаёт дубли и не возвращает завершённые reviews в pending.

## Отдельный запуск backend

Запустите PostgreSQL 16 и задайте `DATABASE_URL`, затем:

```bash
cd apps/backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8000
```

Миграции и seed можно повторять безопасно:

```bash
alembic upgrade head
python -m app.db.seed
```

Демонстрационные Learning Space и Learning Goal добавляются отдельной идемпотентной командой:

```bash
python -m app.db.seed_learning_spaces
```

Полный demo seed:

```bash
python -m app.db.seed_demo
```

## Отдельный запуск frontend

```bash
cd apps/frontend
npm ci
npm run dev
```

Для другого адреса API задайте `NEXT_PUBLIC_API_URL` до запуска или сборки frontend.

## Проверки

Backend:

```bash
cd apps/backend
ruff check .
ruff format --check .
pytest
```

Frontend:

```bash
cd apps/frontend
npm run lint
npm run typecheck
npm run build
npx playwright install chromium
npm run test:e2e
```

E2E ожидает запущенный Compose-стек и demo seed.

Health endpoints:

- `GET /health/live` — проверяет только жизнь процесса и не обращается к БД;
- `GET /health/ready` — выполняет проверку соединения с PostgreSQL;
- `GET /api/v1/meta` — возвращает имя, версию и окружение API.

Реализованные продуктовые вертикали:

- Learning Space и Learning Goal;
- материал → учебная сессия → заметка с transactional outbox.
- concepts и типизированный knowledge graph.
- rule-based Knowledge State и self-rated reviews;
- детерминированный scheduler, Today read model и календарь.

## Backup PostgreSQL

Для обычного восстановления рекомендуется логический backup:

```bash
docker compose exec -T postgres pg_dump --clean --if-exists -U plos -d plos > plos-backup.sql
docker compose exec -T postgres psql -U plos -d plos < plos-backup.sql
```

Перед файловым backup named volume остановите сервисы, чтобы получить согласованный снимок:

```bash
docker compose down
docker run --rm -v personal-learning-os_postgres_data:/volume -v "${PWD}:/backup" alpine tar czf /backup/postgres-data.tar.gz -C /volume .
docker compose up -d
```

В PowerShell вместо `${PWD}` используйте `$($PWD.Path)`, а для logical restore — `Get-Content plos-backup.sql | docker compose exec -T postgres psql -U plos -d plos`. Для восстановления volume остановите Compose, распакуйте архив в пустой `personal-learning-os_postgres_data` и снова запустите сервисы. Не используйте `docker compose down -v`, пока backup не проверен.

Продуктовое и архитектурное описание находится в [docs](docs/).
