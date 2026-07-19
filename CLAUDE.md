# CLAUDE.md

Автоматизация анализа вакансий и откликов hh.ru. Аналог `../kwork` (fscout), но легче: без BMAD, пайплайн в скилле `hh-scan`.

Для сессий улучшения скиллов: очередь слабостей и идей — `BACKLOG.md`.

## Команды

```bash
python3 src/scan.py                                      # скан → data/vacancies.json
python3 src/scan.py --query "rust" --no-state            # отладка одним запросом
python3 src/fetch_vacancy.py --limit 40                  # полные тексты → data/enriched.json
python3 src/apply.py --input data/to-apply.json          # dry-run откликов
python3 src/apply.py --input data/to-apply.json --send   # реальная отправка
python3 src/inbox.py                                     # входящие: сводка attention/awaiting
python3 src/chat_send.py --chat-id N --text-file f --expect-last-id M [--send]  # сообщение в чат
python3 src/chat_leave.py --rejected [--send]            # чистка чатов (только по команде юзера)
```

## Архитектура

```
┌──────────────────────────────────────────────────────────┐
│  /hh-scan  (skill — главная точка входа)                  │
│  scan → enrich → score(LLM) → report → CONFIRM → apply    │
└───────────────┬──────────────────────────────────────────┘
                │            ┌──────────────────────────────┐
                │            │  /hh-test-apply (skill)      │
                │            │  вакансии с testPresent:     │
                │            │  headed Playwright,          │
                │            │  исполняет opus-субагент     │
                │            ├──────────────────────────────┤
                │            │  /hh-inbox (skill)           │
                │            │  ответы работодателей:       │
                │            │  src/inbox.py (сбор) →       │
                │            │  ИИ-вопросы: авто-ответ;     │
                │            │  человеческие: согласование; │
                │            │  текст — chat_send.py (REST),│
                │            │  кнопки/анкеты — Playwright  │
                │            └──────────────────────────────┘
   ┌────────────▼─────────────┐
   │ src/hh_session.py        │  куки Chrome (browser_cookie3) + HH-Lux-InitialState парсер
   │ src/scan.py              │  поиск: QUERIES × {Россия-remote, Казань} → префильтр → vacancies.json
   │ src/fetch_vacancy.py     │  vacancyView: description+keySkills → enriched.json (кэш data/details/)
   │ src/apply.py             │  POST /applicant/vacancy_response, dry-run по умолчанию
   │ src/chatik.py            │  REST чатика: chat_data (история) + send
   │ src/chat_send.py         │  отправка в чат: dry-run дефолт, race-check по last-id
   │ src/applied_log.py       │  единственный писатель applied.json (схема/enum/валидация)
   └──────────────────────────┘
```
Критерии оценки — `profile/profile.md`; факты для анкет/тестов — `profile/candidate-facts.md`.

**Граница python/LLM:** python — только механика (HTTP, парсинг, фильтры по спискам). Скоринг, письма, решения — LLM внутри скилла. Оценочные критерии живут ТОЛЬКО в `profile/profile.md`.

## Доступ к hh.ru (выстрадано@2026-07-09)

- `api.hh.ru` анонимно → 403 при любом User-Agent. Открытого API больше нет, нужна OAuth-регистрация приложения. НЕ ходить туда без токена.
- Рабочий канал: сайт `hh.ru` + куки залогиненного Chrome через `browser_cookie3`. Состояние страницы — JSON в `<template id="HH-Lux-InitialState">` (атрибуты тега варьируются — матчить по id, не по полному тегу).
- Выдача с куками авторизована: `userLabels` на вакансии = уже откликался/отказ → префильтр дедупит бесплатно.
- Отклик: POST `https://hh.ru/applicant/vacancy_response/popup`, form-data с `_xsrf` + заголовки `X-Xsrftoken`, `X-Requested-With: XMLHttpRequest`, `Origin`, `Referer` — отвечает JSON. Поля см. `src/apply.py`. Лимит hh: 200 откликов, окно скорее rolling-24h — `negotiations-limit-exceeded` (дефисы!) выбило на 142-м за день при ~58 вчерашних (подтверждено@2026-07-13). Расходовать НЕ агрессивно: порог score≥7 (по profile.md), дневная пачка ≤100 с буфером под тесты/точечные отклики; скрипт стопится по маркерам captcha/limit.
- ⚠️ Ловушка (выстрадано@2026-07-09): POST на путь БЕЗ `/popup` возвращает HTTP 406 (HTML) — выглядит как fail, но отклик ПРИ ЭТОМ СОЗДАЁТСЯ. После любой аномалии сверяйся с фактом: `hh.ru/applicant/negotiations?filter=all` → `applicantNegotiations.topicList[].vacancyId` (в apply.py есть `verify_sent`). Дубль отклика безопасен: `400 {"error":"alreadyApplied"}`. `400 {"error":"unknown"}` (выстрадано@2026-07-13) = вакансия недоступна для прямого отклика (скрытая — GET отдаёт 403 всем, либо спецформа работодателя); это НЕ лимит, ретрай бессмыслен — только UI/ручной разбор.
- Вакансии с `userTestPresent: true` POST'ом не откликаются (нужно пройти тест в UI) — negotiation не создаётся; для них скилл `hh-test-apply`.
- Переписка: REST чатика (найдено@2026-07-19 грепом чанков `remote.chatik.*.js`, детали в `src/chatik.py`) — полная история + отправка, Playwright в переписке нужен только кнопкам бота и анкетам hh. Список откликов — пагинация `hh.ru/applicant/negotiations?filter=all&page=N` (честная; ходит `src/inbox.py`). Старый SSR-конфиг `/api/chat/messages` (~20 чатов, пагинация мертва@2026-07-18) больше не используется. Сопроводительное письмо отклика видно в чате как первое сообщение от юзера — это и есть верификация доставки письма.
- hash'и резюме юзера захардкожены в `apply.py::RESUMES` (4 рабочих, дефолт senior-en; на hh их 6 — ещё legacy-Flex и безымянный черновик, в поиске не участвуют, подтверждено@2026-07-19). Если юзер пересоздаст резюме — обновить со страницы `hh.ru/applicant/resumes`.

## Данные

```
data/
├── seen-ids.json      # дедуп между сканами (union после каждого прогона)
├── scan-state.json    # lastScanTime, счётчики
├── vacancies.json     # текущий скан после префильтра
├── enriched.json      # + description/keySkills
├── scored.json        # + score/reason/hook (LLM)
├── to-apply.json      # подтверждённые юзером: id+letter+resume
├── applied.json       # state-машина переписки: status (закрытый enum) + lastContact (курсор) + dialog[];
│                      #   новые записи: apply.py и applied_log --create (hh-test-apply); ВСЕ писатели —
│                      #   через applied_log.applied_store (flock + атомарная запись; 4 конкурентных
│                      #   read-modify-write теряли записи). Сырые HTTP-ответы сюда НЕ писать
│                      #   (раздули файл до 34МБ, срезано@2026-07-19 → data/archive/)
├── inbox.json         # снимок откликов + history чатов-кандидатов (src/inbox.py; рабочий вход — сводка stdout)
├── details/{id}.json  # кэш полных текстов (ТОЛЬКО description/keySkills — имён вакансий тут нет)
├── archive/           # вынесенное из горячего пути (сырые response, пре-миграционные копии)
└── report-<дата>.md   # отчёты
```

## Правила

- **Отклики отправлять только после явного подтверждения юзера** (step-5 скилла). Dry-run всегда первым.
- Любой Bash с `--send` дополнительно требует подтверждения человека — PreToolUse-хук `.claude/hooks/ask-on-send.sh` (введён@2026-07-19: после ухода отправки с Playwright на REST текстовые правила скилла — единственный барьер, хук возвращает механический).
- Троттлинг: scan 1.5с/страница, fetch 1.2с/вакансия, apply 8с/отклик, inbox 1.5с/страница + 1с/чат, chat_leave 1с. Не ужимать.
- profile.md — единственный источник критериев оценки; правки критериев = правки этого файла, не промптов в скилле.
