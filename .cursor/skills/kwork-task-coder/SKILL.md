---
name: kwork-task-coder
description: Реализует продакшен-срез P{N} в kwork_mob по СЛЕДУЮЩИЕ_ЗАДАЧИ.md и ТЗ. Use when the user says делай P{N}, implement batch, or implement tasks from СЛЕДУЮЩИЕ_ЗАДАЧИ.
---

# Kwork Task Coder

## Когда использовать

«Делай P24», «реализуй срез», «пиши prod code по ТЗ».

## Workflow

1. Прочитать `СЛЕДУЮЩИЕ_ЗАДАЧИ.md` — батч P{N}.
2. **Проверить grep/чтение кода** — задачи не должны быть уже готовы.
3. Реализовать минимальный diff по ТЗ (`чтоготовосегодня.md` + `.claude/ТЗ.txt`).
4. Тесты slice для backend (`pytest tests/test_*_slice.py`).
5. `python scripts/export_openapi.py` при изменении API.
6. Дописать **Итерация {N}** в `чтоготовосегодня.md`.
7. Обновить `СЛЕДУЮЩИЕ_ЗАДАЧИ.md` (сделано + P{N+1}).
8. `git commit` + `git push origin main`.

## Стек

| Область | Путь |
|---------|------|
| Backend | `backend/orchestrator/` |
| Web-seller | `apps/web-seller/` |
| Web-admin | `apps/web-admin/` |
| Mobile | `apps/mobile/` |

## Правила кода

- Минимальный diff, существующие паттерны.
- Без новых зависимостей без запроса.
- Комментарии только для неочевидной бизнес-логики.
- Не трогать ops/доки кроме `чтоготовосегодня.md` и OpenAPI.

## Коммит

`P{N}: краткое описание на английском`
