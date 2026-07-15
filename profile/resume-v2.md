# Резюме (target v2) — senior-en

> Базируется на дословном слепке `resume.md` (hh.ru senior-en, обновлено 2026-05-11).
> Применены правки 1–13 (согласовано 2026-07-13): SOL→SUI, Flaps = 2.5M, GitHub = shammasov-max,
> «Customizable resource model to source» оставлен как в оригинале по решению юзера.
> Правка 14 (2026-07-14) — статус поиска работы, требует подтверждения.
> Этот файл — образец для переноса на hh.ru.

## Поля hh (метаданные)

- **Заголовок:** Senior Fullstack Engineer / Фулстек-разработчик (TypeScript, Node.js, React)
- **Зарплата:** 280 000 ₽ на руки
- **Статус поиска работы:** «Активно ищу работу» ⚠️ **правка 14** — сейчас стоит `has_job_offer` («Предложили работу, пока думаю», выставлен 2025-12-21). Рекрутёр видит этот статус: он читается как «кандидат почти нанят / торгуется» и снижает интерес. Если оффера на руках нет — поменять. Если есть и это осознанно — оставить.
- **Видимость резюме:** `clients` (видно компаниям, зарегистрированным на hh.ru) — проверить в UI, что это то, что нужно; более закрытая настройка обнулит findability
- **Регион:** Казань · **Переезд:** нет · **Командировки:** готов
- **Формат работы:** REMOTE + ON_SITE (удалённо; офис/гибрид — Казань)
- **Занятость:** полная, частичная, проектная · **График:** полный день
- **Спец. роли hh:** Programmer, developer (96); Development team leader (104)
- **Портфолио / personalSite:** https://github.com/shammasov-max
- **Языки:** Русский — родной, Английский — B2 — средне-продвинутый
- **Фото:** загружено ✅ · **Рекомендация:** Павел Алешкевич (генеральный директор, ООО ТетраСофт) ✅ — оба сигнала на месте, не трогать
- **Контакты:** +7 977 766-60-76 (telegram: @shammasov), miramaxis@gmail.com

## Ключевые навыки (keySkills, 32)

TypeScript, JavaScript, Node.js, React.js, Next.js, React Native, Nest.js, Fastify, PostgreSQL, ClickHouse, Redis, MongoDB, MySQL, Rust, Go, Python, FastAPI, LLM, RAG, LangChain, Docker, CI/CD, Playwright, REST API, REST, JSON API, SQL, NoSQL, Git, ООП, Team management, Teamleading

> Если hh упрётся в лимит навыков — выкидывать с хвоста в порядке: JSON API → NoSQL → ООП.

## Обо мне

Senior/lead fullstack engineer: 18 years in production, 8+ years as tech lead / CTO. I build fintech and high-load systems end-to-end and stay hands-on in the code.

Core stack: TypeScript / Node.js, React / Next.js (SSR) / React Native. I also ship Go and Rust where they pay off (indexers, hot-path services) and Python for AI/LLM services.

AI/LLM in production: RAG, agents, tool calling, pgvector, FastAPI.

Data: PostgreSQL, ClickHouse (billions of events/day), Redis, MongoDB.

Delivery: Docker, CI/CD, feature flags, Playwright E2E; comfortable in distributed async teams (US/Europe).

## Опыт работы

### Senior Fullstack Engineer / Tech Lead — Aftermath Finance (crypto brokerage, SUI blockchain) (2024-12 → 2026-04) · http://aftermath.finance

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

## Чек-лист переноса на hh.ru (senior-en)

- ⏳ Поля UI: формат работы (+Удалённо), зарплата (280 000 net), заголовок, портфолио-ссылка
- ⏳ Статус поиска работы: `has_job_offer` → «Активно ищу работу» (если оффера нет); проверить настройку видимости резюме
- ⏳ keySkills: удалить только Flash Actionscript и Web Application Development; добавить Next.js, React Native, Fastify, Redis, MySQL→оставить, Rust, Go, FastAPI, LLM, RAG, LangChain, Docker, CI/CD, Playwright (REST, JSON API, ООП, SQL, Git, NoSQL — сохранить, фильтры HR по ним бинарны)
- ⏳ «Обо мне»: заменить целиком
- ⏳ Опыт: Aftermath (титул+текст), «-» → «Independent contractor, remote» (название+титул+текст), stablix (титул+текст), btce (текст), ТетраСофт (клиенты+conflicting), Flaps (титул+текст), вставить позицию Genestack (2018-03→2018-06)
- ⏳ Скобки в заголовках позиций («crypto brokerage, SUI blockchain», «Stellar fintech», «game development studio») — hh не имеет поля под это: вписать первой строкой описания либо оставить в названии компании
- 📌 После правок: сверить канон с тремя другими резюме (btce-даты, Flaps 2.5M/30 чел, вуз Воронеж) или скрыть их
