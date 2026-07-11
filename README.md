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
```

Health endpoints:

- `GET /health/live` — проверяет только жизнь процесса и не обращается к БД;
- `GET /health/ready` — выполняет проверку соединения с PostgreSQL;
- `GET /api/v1/meta` — возвращает имя, версию и окружение API.

Реализованные продуктовые вертикали:

- Learning Space и Learning Goal;
- материал → учебная сессия → заметка с transactional outbox.

Продуктовое и архитектурное описание находится в [docs](docs/).
