# Project Roadmap

> Long-term roadmap for the Crypto & World Cup Information Platform. The authoritative design
> rationale lives in [`architecture.md`](architecture.md) and the granular issue list in
> [`taskbook.md`](taskbook.md). This document gives the strategic view: where the project is
> going, what is built versus planned, and what is learned at each stage.
>
> **Status:** 
>**V1.0.0 is complete.** All milestones M0–M7 are implemented and merged into a
> protected `main`. This roadmap was reconciled against a live repository audit at V1 closeout:
> the codebase, the test suite (52 tests green on Python 3.12, after fixing a merge-conflict marker
> that had been blocking collection), and the tooling gates (`ruff`, `mypy --strict`) were all
> verified directly.
> **V2 in progress:** the SQLite storage swap and the price-history feature have landed; client
> `Protocol`s complete the DIP seam. Remaining V2 work: `float`→`Decimal` (TD-02) and a real
> USD→Toman rate source (TD-04).
---

## Project Vision

A Python 3.12+ terminal application that delivers cryptocurrency prices (BTC, ETH, SOL) and
football tournament data through a clean, layered architecture. The project exists for two
reasons at once: to be a genuinely useful CLI tool, and to serve as a portfolio-grade
demonstration of professional software engineering — Clean Architecture, SOLID (especially
Dependency Inversion), separation of concerns, and test-driven growth.

The guiding architectural principle is **dependency inversion**: application logic never talks
to JSON files or HTTP APIs directly; it depends on abstractions. This single decision is what
allows the project to evolve through six planned versions — JSON to SQLite to PostgreSQL, CLI to
REST API to web dashboard — by swapping implementations rather than rewriting the system.

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
- **Status detail:** Delivered. 52 tests (models, storage against a real `tmp_path`, services via
  in-memory fakes, config) pass on Python 3.12; `ruff` and `mypy --strict` are clean.
---

## Version Roadmap (V1-V6)

> V1 is the current build target (M0-M7). V2-V6 are **Planned** future versions; their scope is
> directional and will be re-specified when each is reached.

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

### Version 2 - SQLite *(in progress)*
- **Status:** the storage swap has landed — `SQLiteRepository` with a normalized schema
  (`price_history`, `tournament`, `match`), a new per-coin price-history feature, and the
  client-side DIP seam completed (TD-09 / TD-10). Remaining: `float`→`Decimal` (TD-02) and a real
  USD→Toman rate source (TD-04).
- **Features:** durable, queryable persistence replacing flat JSON; per-coin price history.
- **Architectural changes:** the repository interface evolved from key→dict to a domain-specific
  contract (ADR-011 / decisions ADR-015); JSON retired. Client `Protocol`s added so services depend
  on abstractions on both sides.
- **Technologies introduced:** `sqlite3`, SQL basics, `typing.Protocol`, generics (`Cached[T]`).
- **Learning objectives:** relational storage, the payoff *and limits* of the repository
  abstraction, structural vs nominal typing.

### Version 3 - OOP & Service Refactor *(Planned)*
- **Features:** cleaner internals; no major user-facing change.
- **Architectural changes:** extract a caching-strategy object; introduce richer result/error
  types instead of returning bare models.
- **Technologies introduced:** design-pattern refinements.
- **Learning objectives:** deeper SOLID application, refactoring discipline.

### Version 4 - FastAPI REST API *(Planned)*
- **Features:** expose the existing services over HTTP.
- **Architectural changes:** a new presentation layer (HTTP routes) reusing the *same* services -
  the central proof that the layering was worth it.
- **Technologies introduced:** FastAPI, Pydantic, Uvicorn (ASGI).
- **Learning objectives:** REST design, request validation, the web request lifecycle.

### Version 5 - Web Dashboard *(Planned)*
- **Features:** a browser UI consuming the V4 API.
- **Architectural changes:** a frontend client layer; clean client-server separation.
- **Technologies introduced:** a web frontend (framework TBD).
- **Learning objectives:** client-server architecture, frontend-backend integration.

### Version 6 - Production Hardening *(Planned)*
- **Features:** authentication, async processing, containerized deployment.
- **Architectural changes:** PostgreSQL + SQLAlchemy via the repository seam; async I/O at the
  base-client seam; auth layer; CI/CD; automated testing in pipeline.
- **Technologies introduced:** PostgreSQL, SQLAlchemy, async/await (`httpx`), Docker, CI/CD.
- **Learning objectives:** ORMs, asynchronous programming, containerization, authentication,
  deployment, continuous integration.

---

## Planned Improvements

These are recorded in the technical debt register (see [`architecture.md`](architecture.md) section 8)
and scheduled against the versions above: migrate JSON -> SQLite (TD-01, V2); `float` -> `Decimal`
for money (TD-02, V2); replace manual dependency wiring with a composition helper if it grows
unwieldy (TD-03, V3); adopt a proper USD->Toman rate source (TD-04, V2/V3); add CI and pre-commit
hooks (TD-05, V6); support multiple football competitions (TD-06, post-V1); extract a cache
strategy object (TD-07, V3); move synchronous `requests` to async `httpx` (TD-08, V6).

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