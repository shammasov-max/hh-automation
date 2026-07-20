# Резюме (канон) — fullstack-en (основное)

> **Что это:** дословный снапшот ОСНОВНОГО резюме с hh.ru — `fullstack-en`
> (hash `0089d497ff029e1ed70039ed1f4b71324f454f`), обновлено **2026-07-20**
> (перенос resume-v2.md, правки 1–15; основное — по указанию юзера@2026-07-20).
> Снято из финального GET (`HH-Lux-InitialState`).
>
> `senior-en` (hash `a9b8705eff071acdfd0039ed1f4a7037456369`) — контентный клон,
> отличия: титул «Senior Fullstack Engineer (TypeScript, Node.js, React)» (hh запрещает
> дубль титула), видимость `clients`, роли 96+104, рекомендация Алешкевич, предпочтительный
> контакт cell_phone. lead-ru / head-ru выровнены по срокам/местам/вузу@2026-07-20.
>
> Расшифровки кодов hh (статус поиска, видимость, регион) — сделаны при выгрузке,
> в самом JSON лежат коды. Сверять с UI, если решение зависит от точного значения.

## Поля hh (метаданные)

- **ФИО:** Шаммасов Максим Тимурович · **Фото:** загружено
- **Заголовок:** Senior Fullstack Engineer / Фулстек-разработчик (TypeScript, Node.js, React)
- **Зарплата:** (не указана — решение юзера@2026-07-20)
- **Статус поиска работы:** `active_search` — «Активно ищу работу» (аккаунт-левел, выставлен 2026-07-20; до этого `has_job_offer` с 2025-12-21)
- **Видимость резюме (accessType):** `everyone` — видно всем (у senior-en — `clients`)
- **Регион:** Казань (код area 88) · **Переезд:** нет · **Командировки:** готов · **Время в пути:** less_than_hour
- **Формат работы:** REMOTE + HYBRID + ON_SITE
- **Занятость:** полная, частичная, проектная (`employment: full, part, project`; `employmentForms: FULL, PART_TIME` — enum PROJECT в employmentForms hh отверг@2026-07-20)
- **Спец. роли hh:** Programmer, developer (96) — без 104 (тимлид-роль есть только у senior-en)
- **Общий стаж (считает hh):** 235 мес (~19.6 лет)
- **Портфолио / personalSite:** https://github.com/shammasov-max (type: personal)
- **Языки:** Русский — L1 - Родной, Английский — B2 — Средне-продвинутый
- **Образование (уровень):** higher
- **Права:** B · **Авто:** есть
- **Рекомендации:** «по запросу» (Алешкевич — в senior-en)
- **Контакты:** +7 977 766-60-76 (telegram: @shammasov; старый 903-номер вычищен@2026-07-20), miramaxis@gmail.com · предпочтительный: email

## Ключевые навыки (keySkills, 30 — лимит hh)

TypeScript, JavaScript, Node.js, React.js, Next.js, React Native, Nest.js, Fastify, PostgreSQL, Clickhouse, Redis, MongoDB, MySQL, Rust, Python, FastAPI, LLM, RAG, LangChain, Docker, CI/CD, Playwright, REST API, REST, SQL, NoSQL, Git, ООП, Team management, Teamleading

> `Clickhouse` — канонизация словаря hh (отправляли `ClickHouse`). Go убран (правка 15).

## Обо мне

Senior/lead fullstack engineer: 18 years in production, 8+ years as tech lead / CTO. I build fintech and high-load systems end-to-end and stay hands-on in the code.

Core stack: TypeScript / Node.js, React / Next.js (SSR) / React Native. I also ship Rust where it pays off (indexers, hot-path services) and Python for AI/LLM services.

AI/LLM in production: RAG, agents, tool calling, pgvector, FastAPI.

Data: PostgreSQL, ClickHouse (billions of events/day), Redis, MongoDB.

Delivery: Docker, CI/CD, feature flags, Playwright E2E; comfortable in distributed async teams (US/Europe).

## Опыт работы

### Senior Fullstack Engineer / Tech Lead — Aftermath Finance (2024-12 → 2026-04) · http://aftermath.finance

Crypto brokerage on SUI blockchain.

- Ported core SUI services from TypeScript to Rust (performance-critical paths).
- Led 2–3 engineers in a distributed team across UTC-5…UTC+3 (US/Europe), async processes.
- Split the main product into Go/Rust on-chain indexers, an SSR Next.js website and a SPA React app with a BFF layer.
- Built Python + LLM services (FastAPI) for SUI smart-contract and on-chain data workflows.
- Delivery: CI/CD with feature flags and Playwright E2E, weekly release cycles; GDPR-aware handling of EU user data.

### Senior Fullstack Engineer — Independent contractor, remote (2022-04 → 2024-12)

Remote contractor for several product teams:

- oshu.io — data architect & backend. Market screener ingesting billions of events/day on ClickHouse, serving aggregated real-time data to traders.
- "Mistery" (Telegram game) — team lead; up to 2.5M MAU.
- stroy-monitoring.ru — built from scratch: construction scheduling & reporting with 3D visualizations and Excel import/export.
- smart-eat.ru — meal planning service, fullstack.

Stack: TypeScript / Node.js (Fastify, NestJS, Hono), React / React Native / Next.js, ClickHouse / PostgreSQL / MongoDB, Playwright automations, Go/Python automations for Stellar blockchain.

### Lead Software Engineer — stablix, centus (Stellar fintech) (2020-03 → 2022-03) · http://app.stablix.io

Achievements:
- Raised $3M via user purchases in the first calendar year after launch.
- 25k users, 100k+ wallets; handled 1M+ fiat buy/sell transactions (Stripe, Coinbase) and submitted ~70M transactions on-chain.
- 2 tokens in the Stellar top-5 by 2021 stats.

Built:
- Proprietary Stellar web wallet; multisig transactions batched into channel stacks to cut the cost of parallel pending signatures; parallel multisend via channel accounts.
- Holder snapshots & activity analytics; deep fiat integration & analytics (Stripe, Coinbase).
- Stellar Smart Contract (SSC) transaction composition; private multisig request tool; node time-travel utils.

Stack: TypeScript, Node.js, React.

### Lead developer — poker.ru group (2019-07 → 2019-11) · http://poker.ru

Short-term contract for a rising startup to top up metrics & value
- Improve tech stack and support a team for a shift
- Requirements management
- Project management, team leadership
- Full-stack development/
- Worked tightly with a group of contributing editors and managers.
- Made a react SPA frontend for a WordPress based site with quick in memory state for SSR. Backed by WP database and CRM back-office

### Lead developer / CTO — btce.com (2018-10 → 2019-07) · http://btce.com

Led a team of JS/PHP/Go engineers building a family of EOS blockchain products:
- nameos.io — decentralized EOS account-name auction platform: open-source smart contract, back office building historical state from on-chain transactions, instant buy, incremental stats snapshots.
- MillenEOS — full-history EOS API node solution; EOS block explorer; btce.com — crypto news aggregator.
- Owned the monorepo and modular interfaces across products; requirements & specs, code review and mentoring, hiring and resource planning; CQRS/database research.

### Senior Software Engineer — Genestack (2018-03 → 2018-06)

Bioinformatics platform. Frontend/backend development; requirements engineering together with colleagues from London and Cambridge University; genome methylation research collaboration with Unilever.

### Principal / Lead fullstack developer — ООО ТетраСофт (2015-11 → 2018-01)

1. Oil rig ERP (clients incl. Gazprom, Novatek, PodzemBurGaz)
Key features:
- Rig document management
- Customizable resource model to source
- Generic reports for resources and domain work-orders
- Offline-first workstations
- Distributed, conflict-free data model - based on immutable logs

Responsibilities:
- Team leadership
- R&D to find a proper tech stack
- CustDev to reconcile conflicting industry-standard requirements

2. Remote Rig monitoring system.
Key features:
- high-performance time series charts
- PDF reports
- video streaming
- complex dashboard
- multilevel access control
- mobile application
- maintain various Operating Systems and devices at different feature sets

### Founder & Tech Lead — Flaps LLC (game development studio) (2008-07 → 2015-01) · http://flaps.ru

- Founded and ran a game studio of up to 30 in-house employees; hands-on tech lead of the games' frontend.
- Built and operated projects with a total audience of up to 2.5 million users.
- Ran free offline programming courses (AS3, OOP basics).

Used stack: AS1, AS2, AS3, Flex, Starling, FeathersUI, Genome2D, AMF, Adobe Media Server, Adobe Air (including native extensions and FlaCC)

### freelancer — Self-employed (2005-06 → 2008-08) · http://AS3.ru

Rich internet applications developer.
Presentations, kiosks, games.

## Образование

- Высшее, 2011 — Институт менеджмента, маркетинга и финансов, Воронеж (ИММиФ), специальность: менеджмент организации

## Служебное (для автоматизации)

- id записей опыта НЕ стабильны: при POST полного массива со вставкой hh сматчил позиционно
  (Genestack получил бывший id ТетраСофта, Flaps — новый id). Верифицировать по контенту, не по id.
- POST записи с `companyId` затирает кастомное имя каноничным именем компании из справочника
  (id 1374476 = «-»: съел «Индивидуальное предпринимательство…» в head-ru). Отвязка: companyId/employerId → null.
- Эндпоинт правки: POST `/applicant/resume/edit?resume=<hash>` (детали протокола — сессия 2026-07-20).
- Сроки/места/вуз во всех 4 резюме = этот канон (синк@2026-07-20). ФБК из head-ru удалён
  по решению юзера@2026-07-20 — состав мест теперь везде канонный. На LinkedIn Smart-eat.ru
  (Sep 2019 – Jun 2020) оставлена отдельной позицией по решению юзера@2026-07-20.
