---
name: hh-scan
description: Скан вакансий hh.ru, LLM-скоринг по profile.md, отчёт, отклики после подтверждения. Триггеры: "/hh-scan", "проскань hh", "новые вакансии".
---

# hh-scan: пайплайн анализа вакансий и откликов

Рабочий каталог: `/home/max/automations/hh`. Все шаги последовательны.

## step-1: Скан

```bash
python3 src/scan.py
```

Читает QUERIES×CONTOURS (удалёнка-Россия + Казань), префильтрует стоп-лист/джунов/зарплатный пол, дедупит по `data/seen-ids.json`. Выход `data/vacancies.json`. Если kept=0 — сообщить юзеру, конец.

## step-2: Обогащение

```bash
python3 src/fetch_vacancy.py --limit 40
```

Полный текст + keySkills для 40 свежайших → `data/enriched.json` (кэш `data/details/`).

## step-3: LLM-скоринг (субагенты sonnet)

Раздели вакансии из `data/enriched.json` на батчи по 10. На каждый батч — Task-субагент `sonnet` параллельно. Промпт субагенту:

> Прочитай /home/max/automations/hh/profile/profile.md (профиль соискателя: стек, штрафы, стоп-лист, шкала 0–10).
> Оцени вакансии (JSON ниже). Для каждой верни строго JSON-массив:
> `[{"id":<id>,"score":<0-10>,"reason":"<1-2 предложения почему>","hook":"<конкретное совпадение опыта для сопроводительного или null>","resume":"senior-en|lead-ru|head-ru"}]`
> resume: `lead-ru`/`head-ru` для русскоязычных лид/менеджерских вакансий, иначе `senior-en`.
> Вакансии: <батч: id, name, company, salary, area, workFormats, experience, keySkills, description до 1500 символов, responsesCount, testPresent>

Собери результаты → `data/scored.json` (merge с enriched, сортировка по score desc).

## step-4: Отчёт юзеру

Markdown-таблица топа (score ≥ 5): score, название+ссылка, компания, вилка, формат, конкуренция, reason. Кандидаты на отклик = score ≥ 7 и `testPresent: false` и не `closed`. Сохранить `data/report-<дата>.md`, показать юзеру суть в чате.

## step-5: Подтверждение (ОБЯЗАТЕЛЬНО)

AskUserQuestion (multiSelect или список id): какие вакансии откликать. **Без явного подтверждения юзера отклики не отправляются — никогда.** Отклик — внешнее действие.

## step-6: Сопроводительные

Для подтверждённых — письма по правилам profile.md (раздел «Сопроводительное письмо»), используя `hook` из скоринга.
- ≤15 писем: пиши сам (Opus-задача), не субагентам.
- >15 писем: sonnet-субагенты батчами по ~10 (дать: правила писем из profile.md + candidate-facts.md + hook и полный текст вакансии), затем ОБЯЗАТЕЛЬНЫЙ свой ревью каждого драфта: сверка фактов/hook'ов с candidate-facts.md (галлюцинированный опыт = хуже отсутствия письма), правка штампов.
Собери `data/to-apply.json`:
`[{"id":..., "letter":"...", "resume":"senior-en"}]`
Покажи письма юзеру перед отправкой (в том же подтверждении или отдельным сообщением).

## step-7: Отправка

```bash
python3 src/apply.py --input data/to-apply.json          # dry-run, проверить payload
python3 src/apply.py --input data/to-apply.json --send   # реальная отправка
```

При блокере (captcha/limit) скрипт сам останавливается — сообщить юзеру, не ретраить.
Вакансии с `testPresent: true` в to-apply.json не включать — POST их не берёт (тест в UI). Для них есть скилл `hh-test-apply` (headed Playwright + opus-субагент) — предложи юзеру запустить его.
Итог сверяй по `verifiedInNegotiations` в выводе скрипта (факт с hh), не по локальным ok/fail.

## step-8: Входящие

После отправки предложи юзеру `/hh-inbox` — отработка ответов работодателей (отказы, ИИ-опросники, человеческие вопросы). Логично запускать и в начале каждого сеанса, до нового скана.

## step-9: Состояние

Добавь id всех обработанных (kept из step-1) в `data/seen-ids.json` (union, JSON-массив int). Обнови `data/scan-state.json`: `{"lastScanTime": "<ISO>", "lastKept": N, "applied": M}`. Краткая сводка юзеру: найдено/оценено/топ/отправлено.

## Ошибки

- `no _xsrf cookie` / HTTP 403 на hh.ru → юзер разлогинен в Chrome, попросить залогиниться на hh.ru.
- Lux state не парсится → hh изменил разметку; посмотреть `page.html` руками, поправить `_LUX_RE` в `src/hh_session.py`.
