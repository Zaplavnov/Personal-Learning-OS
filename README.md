# Personal Learning OS

Личная self-hosted система глубокого обучения, которая объединяет учебные материалы, заметки, динамическую карту концепций, адаптивное повторение, календарь и диалог с AI-наставником. Центральный объект продукта — изменяющееся состояние понимания конкретной концепции.

Сейчас в репозитории реализована frontend-основа на Next.js с демонстрационными данными и дизайном «Тихий фокус». Backend, база данных, авторизация и внешние API на этом этапе не подключены.

## Структура

```text
Personal-Learning-OS/
├── apps/
│   └── frontend/       # Next.js frontend
├── docs/               # продуктовая и техническая документация
├── infrastructure/     # заготовка инфраструктуры следующих этапов
├── .env.example
├── docker-compose.yml
└── README.md
```

## Требования

- Node.js 22.13 или новее;
- npm 10 или новее;
- Docker Compose (необязательно, для контейнерного запуска).

## Локальный запуск

```bash
cd apps/frontend
npm ci
npm run dev
```

Откройте <http://localhost:3000>. Корневой URL перенаправит на `/today`.

## Проверка frontend

```bash
cd apps/frontend
npm run lint
npm run typecheck
npm run build
npm run start
```

## Запуск через Docker Compose

```bash
docker compose up --build frontend
```

Приложение будет доступно на <http://localhost:3000>.

Подробнее о продукте и архитектуре: [docs/product_concept.md](docs/product_concept.md), [docs/product_overview.md](docs/product_overview.md), [docs/technical_architecture.md](docs/technical_architecture.md).
