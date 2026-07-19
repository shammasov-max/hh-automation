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
                │            │  src/inbox.py (чтение) →     │
                │            │  ИИ-вопросы: авто-ответ;     │
                │            │  человеческие: согласование  │
                │            │  с юзером; отправка —        │
                │            │  Playwright (opus)           │
                │            └──────────────────────────────┘
   ┌────────────▼─────────────┐
   │ src/hh_session.py        │  куки Chrome (browser_cookie3) + HH-Lux-InitialState парсер
   │ src/scan.py              │  поиск: QUERIES × {Россия-remote, Казань} → префильтр → vacancies.json
   │ src/fetch_vacancy.py     │  vacancyView: description+keySkills → enriched.json (кэш data/details/)
   │ src/apply.py             │  POST /applicant/vacancy_response, dry-run по умолчанию
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
- Переписка (выстрадано@2026-07-09): `chatik.hh.ru/api/chat/messages?chatId=<любой>` → SSR-конфиг, внутри `chats.chats.items` — чаты с lastMessage/unreadCount/`workflowTransition.applicantState`/`participantDisplay.isBot`, но ТОЛЬКО ~20 последних (выстрадано@2026-07-18: found=282, пагинация мертва). Полное покрытие — пагинация `hh.ru/applicant/negotiations?filter=all&page=N` (работает честно, найдено@2026-07-19: topicList+vacanciesShort дают chatId/lastState/имена, но не текст сообщений) — оба канала ходит `src/inbox.py`. Полная история и ОТПРАВКА сообщений через REST недоступны (SPA/websocket) — отправка только Playwright'ом. Сопроводительное письмо отклика видно в чате как первое сообщение от юзера — это и есть верификация доставки письма.
- hash'и резюме юзера захардкожены в `apply.py::RESUMES` (6 резюме, дефолт senior-en). Если юзер пересоздаст резюме — обновить со страницы `hh.ru/applicant/resumes`.

## Данные

```
data/
├── seen-ids.json      # дедуп между сканами (union после каждого прогона)
├── scan-state.json    # lastScanTime, счётчики
├── vacancies.json     # текущий скан после префильтра
├── enriched.json      # + description/keySkills
├── scored.json        # + score/reason/hook (LLM)
├── to-apply.json      # подтверждённые юзером: id+letter+resume
├── applied.json       # state-машина переписки: id+name+company+resume+letter+ts, topicId/chatId,
│                      #   status (закрытый enum) + lastContact (курсор) + dialog[] — контракт в skill hh-inbox step-4;
│                      #   сырые HTTP-ответы сюда НЕ писать (раздули файл до 34МБ, срезано@2026-07-19 → data/archive/)
├── inbox.json         # снимок чатов по откликам (src/inbox.py; прошлый → inbox-prev.json)
├── details/{id}.json  # кэш полных текстов (ТОЛЬКО description/keySkills — имён вакансий тут нет)
├── archive/           # вынесенное из горячего пути (сырые response, пре-миграционные копии)
└── report-<дата>.md   # отчёты
```

## Правила

- **Отклики отправлять только после явного подтверждения юзера** (step-5 скилла). Dry-run всегда первым.
- Троттлинг: scan 1.5с/страница, fetch 1.2с/вакансия, apply 8с/отклик. Не ужимать.
- profile.md — единственный источник критериев оценки; правки критериев = правки этого файла, не промптов в скилле.
