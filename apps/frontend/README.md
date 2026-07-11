# Personal Learning OS — frontend

Интерфейс Personal Learning OS в визуальном направлении «Тихий фокус». Приложение построено на Next.js App Router и пока работает с демонстрационными данными.

## Команды

```bash
npm ci
npm run dev
npm run lint
npm run typecheck
npm run build
npm run start
```

После `npm run dev` приложение доступно по адресу <http://localhost:3000>.

## Структура

- `app/` — layouts и маршруты;
- `components/layout/` — общий shell, sidebar и тема;
- `components/ui/` — небольшие переиспользуемые компоненты;
- `features/` — крупные предметные экраны;
- `lib/mock-data.ts` — временные демонстрационные данные.

Выбор темы хранится в `localStorage` под ключом `plos-theme`.
