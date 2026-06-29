# Project Roadmap

> Long-term roadmap for **MarketPulse** (originally the "Crypto & World Cup" CLI). The authoritative
> design rationale lives in [`architecture.md`](architecture.md) and the historical V1 issue list in
> [`taskbook.md`](taskbook.md). This document gives the strategic view: where the project is going,
> what is built versus planned, and what is learned at each stage.
>
> **Status:** V1–V9 are complete. The project has evolved from a JSON-backed learning CLI into a
> fully-async, multi-channel market-data platform. Details below.
>
> **Legacy status notes (V1–V7):** 
>**V1.0.0 is complete.** All milestones M0–M7 are implemented and merged into a
> protected `main`. This roadmap was reconciled against a live repository audit at V1 closeout:
> the codebase, the test suite (49 tests green on Python 3.12, after fixing a merge-conflict marker
> that had been blocking collection), and the tooling gates (`ruff`, `mypy --strict`) were all
> verified directly.
> **V2.0.0 is complete.** The SQLite storage swap, price-history feature, and client DIP seams
> have landed. Remaining V2 work (`float`→`Decimal` TD-02 and native Wallex Toman rate source TD-04)
> are also fully shipped!
> **V3.0.0 is complete.** The OOP and service refactoring is fully implemented, introducing the `Result` type, `CacheStrategyProtocol`, and a DI Container.
> **V4.0.0 is complete.** The FastAPI REST API presentation layer was added, proving the architecture's decoupling by reusing existing services untouched.
> **V5.0.0 is complete.** The Web Dashboard with HTMX and the Dynamic Assets domain refactoring have shipped.
> **V6.0.0 is complete.** The Telegram Bot integration has shipped, providing a new UI channel for the same core services.
> **V7.0.0 is complete.** Production hardening landed with SQLAlchemy ORM, PostgreSQL support, Docker containerization, and fully asynchronous architecture.
---

## Project Vision

**MarketPulse** is a Python 3.12+, fully-async platform that delivers real-time prices for crypto,
fiat, precious metals, and global stocks through three channels — a web dashboard, a Telegram bot,
and a CLI — over one shared core. It began as a "Crypto & World Cup" learning CLI; the football
half was retired in the V8 pivot, and the crypto half grew into a swapwallet-style market platform.

The guiding architectural principle is **dependency inversion**: application logic never talks to a
database or an HTTP API directly; it depends on abstractions. This is what let the project evolve
through nine versions — JSON → SQLite → SQLAlchemy/PostgreSQL, CLI → REST → web → bot, sync → async —
by swapping implementations behind stable seams rather than rewriting the system.

The project is built deliberately, one issue per feature branch, each merged via pull request
into a protected `main`, following a concept -> plan -> code -> review loop for every component.
Readability is prioritized over cleverness, and every conscious compromise is recorded as
tracked technical debt rather than hidden.

---

## Learning Objectives

The project is structured so that each phase introduces a coherent set of concepts exactly when
the work naturally requires them, rather than front-loading theory. Across the full V1 build the
intended learning spans: Python project and package structure; modules and imports; dataclasses
and type hints; object-oriented design; abstract base classes and interfaces; API integration;
JSON processing; file handling and atomic writes; error and exception management; logging;
dependency and configuration management; clean architecture and SOLID principles; separation of
concerns; and testing fundamentals (unit tests, fixtures, mocking).

The deeper objective is *software design thinking* — learning to reason about trade-offs, design
seams for future change, and recognize when a compromise is acceptable versus when it is debt.

---

## Milestone Overview

| Milestone | Theme | Objective | Status |
| --- | --- | --- | --- |
| M0 | Bootstrap / Scaffolding | Establish a runnable, installable, tooled project skeleton | ✅ Completed |
| M1 | Foundations | Cross-cutting utilities: exceptions, logging, configuration | ✅ Completed |
| M2 | Domain Models | Typed dataclasses for crypto and football domains | ✅ Completed |
| M3 | Storage Layer | Repository interface + JSON implementation | ✅ Completed |
| M4 | API Clients | Base HTTP client + crypto and football adapters | ✅ Completed |
| M5 | Service Layer | Orchestration, caching, dependency injection | ✅ Completed |
| M6 | Presentation | rich renderers + interactive menu, full wiring | ✅ Completed |
| M7 | Tests & Docs | Unit tests across layers; final documentation | ✅ Completed |
---

## Milestone Status (detail)

### M0 - Bootstrap (Completed)
- **Major components:** repository, branch protection, folder tree, `pyproject.toml`, virtual
  environment, editable install, console entry point, root documentation.
- **Key deliverables:** an installable package that runs (`crypto-wc`), full `src/` layout,
  tooling configured (Ruff, mypy, pytest), and - after the governance audit - a committed
  `docs/architecture.md` and an updated README.
- **Status detail:** completed and merged, including the two post-audit `docs:` follow-up PRs
  that closed findings C-1 (architecture doc) and C-2 (README setup/usage).

### M1 - Foundations (Completed)
- **Major components:** custom exception hierarchy (`utils/exceptions.py`), centralized logging
  (`utils/logger.py`), frozen settings loader (`config/settings.py`), and a foundation
  integration in `main.py`.
- **Key deliverables:** an anti-fragile startup sequence (load settings -> ensure directories ->
  configure logging -> emit startup log), with graceful `ConfigError` handling and verified
  dual-handler logging behavior.
- **Status detail:** completed and merged. Verified via REPL checks (Liskov substitution,
  immutability, `ConfigError` translation) and three startup smoke tests.

### M2 - Domain Models (Completed)
- **Objective:** define `CryptoPrice`/`Coin` enum and `Team`/`Match`/`Tournament`/`MatchStatus` as
  typed dataclasses.
- **Status detail:** Delivered. Frozen, slotted dataclasses with construction-time validation; the
  `Match` invariant (scores exist iff the match has started) and a tuple-typed `Tournament.matches`
  enforce honest immutability.

### M3 - Storage Layer (Completed)
- **Objective:** an abstract `BaseRepository` plus a JSON implementation behind it (the migration seam).
- **Status detail:** Delivered. `JSONRepository` writes atomically (temp file + `os.replace` + fsync),
  wraps every record in a `{fetched_at, schema_version, data}` envelope, validates key names, and
  translates `OSError`/`json` failures into `StorageError`.

### M4 - API Clients (Completed)
- **Objective:** a shared HTTP base client plus CoinGecko and Football-Data.org adapters.
- **Status detail:** Delivered. `BaseAPIClient` owns session reuse, timeouts, backoff retries, and
  `requests`→`APIError` translation; each adapter maps raw JSON into domain models (anti-corruption
  layer) and validates its API key at point of use.

### M5 - Service Layer (Completed)
- **Objective:** cache-then-fetch orchestration with TTL staleness and offline fallback.
- **Status detail:** Delivered. Both services share a `cache_policy.is_fresh` helper, depend on the
  injected `BaseRepository` abstraction, and re-validate cached data through the models on read.

### M6 - Presentation (Completed)
- **Objective:** `rich` renderers and an interactive menu, fully wired in the composition root.
- **Status detail:** Delivered. Pure renderers, an `AppError`-catching menu, and a `main.py` that
  wires every layer in dependency order and degrades gracefully without a football key.

### M7 - Tests & Documentation (Completed)
- **Objective:** unit tests across layers with external boundaries mocked, plus final docs.
- **Status detail:** Delivered. 49 tests (models, storage against a real `tmp_path`, services via
  in-memory fakes, config) pass on Python 3.12; `ruff` and `mypy --strict` are clean.
---

## Version Roadmap (V1–V10)

> V1–V9 are shipped; V10 is planned. The per-version detail below is kept as a historical record of
> how the platform was built, one seam at a time.

### Version 1 - JSON-backed CLI ✅ *(shipped — V1.0.0)*
- **Features:** crypto prices (USD, Toman, 24h change, timestamp) for BTC/ETH/SOL with refresh,
  single-coin, and all-coins views; football completed/upcoming matches with scores, times, teams,
  and tournament progress for one competition; JSON persistence; interactive `rich` CLI.
- **Architectural changes:** establishes the four-layer architecture (Presentation, Service, Data,
  Utility) with one-directional dependencies and the repository/adapter seams.
- **Technologies introduced:** `requests`, `rich`, `python-dotenv`, `json`, `pathlib`, `logging`,
  `dataclasses`, `pytest`, `ruff`, `mypy`.
- **Learning objectives:** the full clean-architecture foundation - layering, dependency
  inversion, repository and adapter patterns, configuration and logging, error handling, testing.

### Version 2 - SQLite ✅ *(shipped — V2.0.0)*
- **Status:** Complete. The storage swap landed — `SQLiteRepository` with a normalized schema
  (`price_history`, `tournament`, `match`), a new per-coin price-history feature, and the
  client-side DIP seam completed (TD-09 / TD-10). We also completed `float`→`Decimal` migration (TD-02) and integrated the Wallex API for native Toman rates (TD-04).
- **Features:** durable, queryable persistence replacing flat JSON; per-coin price history.
- **Architectural changes:** the repository interface evolved from key→dict to a domain-specific
  contract (ADR-011 / decisions ADR-015); JSON retired. Client `Protocol`s added so services depend
  on abstractions on both sides.
- **Technologies introduced:** `sqlite3`, SQL basics, `typing.Protocol`, generics (`Cached[T]`).
- **Learning objectives:** relational storage, the payoff *and limits* of the repository
  abstraction, structural vs nominal typing.

### Version 3 - OOP & Service Refactor ✅ *(shipped — V3.0.0)*
- **Status:** Complete. We extracted a `CacheStrategyProtocol` (TD-07), introduced functional `Result` types (`Ok`/`Err`), and replaced manual wiring in `main.py` with a DI `Container` (TD-03).
- **Features:** cleaner internals; no major user-facing change.
- **Architectural changes:** extract a caching-strategy object; introduce richer result/error
  types instead of returning bare models.
- **Technologies introduced:** design-pattern refinements.
- **Learning objectives:** deeper SOLID application, refactoring discipline.

### Version 4 - FastAPI REST API ✅ *(shipped — V4.0.0)*
- **Status:** Complete. We added `fastapi` and `uvicorn`, created an `api/` presentation layer with routers, and tested it comprehensively using `TestClient`.
- **Features:** expose the existing services over HTTP.
- **Architectural changes:** a new presentation layer (HTTP routes) reusing the *same* services -
  the central proof that the layering was worth it.
- **Technologies introduced:** FastAPI, Pydantic (implicitly via FastAPI), Uvicorn (ASGI).
- **Learning objectives:** REST design, request validation, the web request lifecycle, API testing.

### Version 5 - Web Dashboard ✅ *(shipped — V5.0.0)*
- **Status:** Complete. We built a modern, immersive Web Dashboard using Jinja2 and HTMX to consume the FastAPI endpoints. We also refactored the domain (`Coin` enum to dynamic strings) and added `FiatClient` for multi-asset support.
- **Features:** A browser UI displaying live financial markets (Crypto, Fiat, Metals) and multi-league football, with auto-polling and advanced UI elements.
- **Architectural changes:** A frontend client layer cleanly separated from the backend; integration of new data providers seamlessly into the existing `CryptoService`.
- **Technologies introduced:** HTML5, CSS3 (Glassmorphism), Jinja2, HTMX.
- **Learning objectives:** client-server architecture, hypermedia-driven applications (HTMX), frontend-backend integration.

### Version 6 - Telegram Bot Integration ✅ *(shipped — V6.0.0)*
- **Status:** Complete. We added `python-telegram-bot` and a new entry point `crypto-wc-bot`.
- **Features:** A Telegram bot with interactive inline keyboards, inline queries, and a daily scheduled brief.
- **Architectural changes:** Added a new presentation layer that safely consumes the core services without blocking the event loop.
- **Technologies introduced:** `python-telegram-bot`, Telegram Bot API.
- **Learning objectives:** Chatbot integration, background job queues, async wrappers.

### Version 7 - Production Hardening ✅ *(shipped — V7.0.0)*
- **Status:** Complete. We migrated the entire stack to `asyncio` (`httpx`, `asyncpg`), swapped the DB to `SQLAlchemy 2.0`, and containerized the app.
- **Features:** Asynchronous execution, robust ORM, multi-container Docker deployments, PostgreSQL support, GitHub Actions CI.
- **Architectural changes:** PostgreSQL + SQLAlchemy via the repository seam; async I/O at the base-client seam; CI/CD; automated testing in pipeline.
- **Technologies introduced:** PostgreSQL, SQLAlchemy, async/await (`httpx`), Docker, Docker Compose, GitHub Actions.
- **Learning objectives:** ORMs, asynchronous programming, containerization, deployment, continuous integration.

### Version 8 - MarketPulse Transformation ✅ *(shipped — V8.0.0)*
- **Goal:** Pivot from the "crypto + football" learning project to a market-data platform called
  MarketPulse, inspired by swapwallet.app.
- **Shipped:** codebase cleanup (broken imports, `image_url` model field, API title, football purge);
  Iran Bourse dropped (TSETMC returned empty data); 35 tests green.

### Version 9 - Swapwallet-style coin list & group-ready bot ✅ *(shipped — V9.0.0)*
- **Features:** a CoinMarketCap-style web coin list (logos, market cap, 24h volume, rank, sortable
  columns, 7-day sparklines); a per-coin detail page (`/coin/{symbol}`) with a TradingView chart and
  stored history; Persian asset names; a Telegram bot optimized for **groups** (mention/reply/free-text
  answers, join-greeting, command menu, `/p` alias, logo thumbnails in inline results).
- **Architectural changes:** `CoinGeckoClient` behind a new `MarketDataClientProtocol`; the service
  merges CoinGecko (global data) with Wallex (Toman + Persian names); `CryptoPrice` extended with
  `market_cap`/`volume_24h`/`rank`/`image_url`/`sparkline`; a pure, tested `bot/search.py`.
- **Technologies introduced:** CoinGecko Markets API, TradingView widgets, inline-SVG sparklines.
- **Learning objectives:** multi-source data merging, graceful degradation, testable bot logic.

### Version 10 - Trade actions, alerts & mobile *(Planned)*
- **Features:** wire the dashboard buy/sell buttons to a real action; per-user price-alert
  subscriptions pushed via the bot; portfolio tracking (buy price, quantity, P&L); a PWA /
  mobile-ready front end.
- **Architectural changes:** notification job in the bot layer atop the existing user model;
  authentication (JWT) and CORS for external clients.
- **Learning objectives:** stateful chatbot flows, background scheduling, cross-platform delivery.

---

## Planned Improvements

and scheduled against the versions above: add CI and pre-commit
hooks (TD-05, V6); support multiple football competitions (TD-06, post-V1); move synchronous `requests` to async `httpx` (TD-08, V6).

---

## Long-Term Evolution Path

The project is intentionally designed so that complexity is added one layer at a time, and each
version replaces or extends a single architectural seam without disturbing the others. The
evolution path in one line: **a single-user JSON CLI grows into a tested, authenticated,
async, containerized client-server platform - without ever requiring a ground-up rewrite**,
because the interfaces (repository, adapter, service injection) were established in V1. The
long-term goal is not the feature set itself but the demonstration that disciplined architecture
makes change cheap.

---

## Skills Learned Per Milestone

| Milestone | Python concepts | Software engineering concepts |
| --- | --- | --- |
| M0 | Packages vs. modules, `__init__.py`, `src/` layout, `pyproject.toml`, virtual environments, editable installs | Project structure, dependency management, tooling, Git workflow, branch protection |
| M1 | Custom exception classes, inheritance, the `logging` module, handlers/formatters, `dataclass(frozen=True)`, `@classmethod`, `@property`, `os.getenv`, `python-dotenv`, exception chaining (`from exc`) | Exception-translation-at-boundaries, centralized configuration, separation of concerns, idempotent startup, fail-loud-but-clean |
| M2  | `dataclasses`, type hints, `Enum`, `Optional`, `datetime` | Domain modeling, typed objects over raw dicts |
| M3  | `abc` abstract base classes, `json`, context managers, atomic file writes | Repository pattern, dependency inversion, serialization |
| M4  | `requests`, sessions, timeouts, retry logic | Adapter pattern, defensive parsing, retry/backoff/timeout policy |
| M5  | Composition, constructor injection | Dependency injection, caching strategy, orchestration |
| M6  | `rich` tables/panels, input loops | Thin presentation layer, UI/logic separation |
| M7  | `pytest`, fixtures, mocking | Unit vs. integration testing, testing at boundaries |