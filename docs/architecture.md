# Architecture & Governance — Crypto & World Cup Information Platform

> **Status:** Version 1 (frozen). This document is the source of truth for the project's
> architecture and the decisions behind it. Changes to any frozen decision require a new
> ADR entry with justification — they are not revised casually mid-implementation.

---

## 1. Overview

A Python terminal application that delivers real-time cryptocurrency prices (BTC, ETH, SOL)
and football tournament data through a clean, layered architecture. Its primary purpose is to
serve as a portfolio-grade demonstration of professional software engineering in Python —
Clean Architecture, SOLID (especially Dependency Inversion), separation of concerns, and
test-driven growth — while remaining a genuinely useful CLI tool.

The central architectural bet is **dependency inversion**: application logic never talks to
JSON files or HTTP APIs directly. It talks to *abstractions*. That single decision is what
makes every planned future migration (JSON → SQLite → PostgreSQL, CLI → FastAPI → web) a
matter of swapping implementations rather than rewriting the system.

---

## 2. Layered Architecture

Dependencies flow in **one direction only**. A lower layer never imports an upper layer.

```
[ User ] → [ Presentation ] → [ Service ] → [ Clients (external APIs) ]
                                   ↓
                             [ Storage (JSON) ]
        ( Utilities & Configuration available to every layer )
```

| Layer | Location | Responsibility |
| --- | --- | --- |
| Presentation | `src/app/presentation/`, `main.py` | The only layer the user touches. Reads input, calls services, renders with `rich`. Contains **no** business logic and **no** I/O beyond the terminal. |
| Service | `src/app/services/` | Orchestration and business rules (cache-then-fetch, staleness). Depends only on *interfaces* of the layers below, injected via constructors. |
| Data | `src/app/clients/`, `src/app/storage/` | Two kinds of data access — external (API adapters) and internal (persistence) — each hidden behind its own abstraction. |
| Utility | `src/app/utils/`, `src/app/config/` | Cross-cutting concerns: logging, exceptions, configuration. Imported by all layers. |

**Interaction rule:** Presentation → Service → Data, never the reverse. This strict direction
is what gives the system its testability and replaceability.

---

## 3. Folder Structure

```
crypto-worldcup-platform/
├── src/app/
│   ├── main.py                 # Entry point: wires dependencies, starts CLI
│   ├── config/settings.py      # Loads config from env + settings file
│   ├── models/                 # crypto.py, football.py — typed dataclasses
│   ├── services/               # crypto_service.py, football_service.py
│   ├── clients/                # base_client.py + crypto/football adapters
│   ├── storage/                # base_repository.py (interface) + json_repository.py
│   ├── presentation/           # menu.py, renderers.py
│   └── utils/                  # logger.py, exceptions.py
├── tests/                      # mirrors the source tree
├── data/                       # runtime files (gitignored; folders kept via .gitkeep)
│   ├── cache/  settings/  history/  logs/
├── docs/                       # this document and related governance artifacts
├── assets/                     # static files (e.g., ASCII banners)
├── .env.example  .gitignore  .python-version
├── pyproject.toml  README.md  LICENSE  CHANGELOG.md  CONTRIBUTING.md
```

**Why `src/` layout:** it prevents accidentally importing the un-installed package, forcing the
editable install (`pip install -e .`) that mirrors how the package behaves when distributed.

**Why physically separate `clients/`, `services/`, `storage/`:** the separation enforces the
layered architecture — you cannot blur a boundary without an obvious cross-folder import that a
reviewer will catch.

---

## 4. Architecture Decision Records (ADRs)

Each ADR records the *reasoning* behind a load-bearing decision, not merely the outcome.

### ADR-001 — Layered architecture, one-directional dependencies
- **Context:** must survive five future versions (SQLite → OOP refactor → FastAPI → web → Postgres/async/Docker) without rewrites.
- **Options considered:** (a) flat single-module script; (b) MVC; (c) layered with dependency inversion.
- **Trade-offs:** the flat script is fastest but collapses under growth; MVC suits request-response web apps but doesn't cleanly isolate external data sources; layered costs more files and indirection now.
- **Final decision:** layered (Presentation → Service → Data), lower layers never importing upper.
- **Rationale:** the indirection is paid once; it is what makes each future migration a swap rather than a rewrite.

### ADR-002 — Storage strategy: JSON behind a Repository interface
- **Context:** V1 persists to JSON; V2 → SQLite, V6 → PostgreSQL.
- **Options considered:** (a) read/write JSON directly in services; (b) abstract `Repository` interface with a JSON implementation.
- **Trade-offs:** direct JSON is simpler today but welds the storage format into business logic, making migration a rewrite; the interface adds one abstraction layer.
- **Final decision:** abstract `Repository`; JSON is one implementation.
- **Rationale:** this interface is the migration seam — V2 adds `SQLiteRepository` implementing the same contract and the services never change.

### ADR-003 — Cryptocurrency API provider
- **Context:** need USD price and 24h change for BTC/ETH/SOL.
- **Options considered:** CoinGecko (free, no key for basic use), CoinMarketCap (richer, key required), Binance (trading-oriented).
- **Trade-offs:** CoinGecko minimizes setup friction and secret-handling but has rate limits and no SLA; CoinMarketCap adds headroom at the cost of key management; Binance is overkill for spot prices.
- **Final decision:** **CoinGecko for V1**, behind the adapter.
- **Rationale:** lowest friction for a learning project; the adapter quarantines the choice so a swap costs one file.
- **Open item:** verify current free-tier terms and exact endpoint at the start of Milestone M4.

### ADR-004 — Football / World Cup data provider
- **Context:** need fixtures, results, scores, team names, and tournament progress for one competition.
- **Options considered:** Football-Data.org (free tier, key required, limited competitions), API-Football (richer, stricter free limits).
- **Trade-offs:** Football-Data.org is well-documented and free but its free tier constrains *which* competitions are available — so the displayed tournament is bounded by the tier, not freely chosen; API-Football offers more but rate-limits harder.
- **Final decision:** **Football-Data.org for V1**, single competition chosen at M4 from what the free tier serves, behind the adapter.
- **Rationale:** documentation quality and free access suit learning; adapter isolation protects the design.
- **Open item:** confirm live terms and select the competition at M4 start.

### ADR-005 — Toman conversion source
- **Context:** `price_toman` is required but no native Toman crypto feed is assumed.
- **Options considered:** (a) native Toman crypto feed; (b) compute Toman = USD × a USD→Toman rate; (c) configurable static fallback rate.
- **Trade-offs:** a native feed is most "real" but adds a second fragile integration to V1; computing from a rate keeps one source of truth for crypto prices but is only as accurate as the rate; a static rate always works but drifts from reality.
- **Final decision:** **compute from a USD→Toman rate** sourced at M4, with a configurable fallback rate (clearly labeled approximate) if no reliable free rate API is found.
- **Rationale:** keeps V1 shippable without a second fragile integration; honesty about approximation is acceptable for a display-only value.

### ADR-006 — Cache strategy
- **Context:** avoid redundant API calls and provide a fallback when an API is unreachable.
- **Options considered:** (a) no cache; (b) simple time-threshold (TTL) cache in JSON; (c) sophisticated invalidation/event-based cache.
- **Trade-offs:** no cache hammers rate-limited APIs and dies offline; TTL is trivial and meets needs but is coarse; sophisticated invalidation is premature for V1.
- **Final decision:** **TTL cache** — each entry stores `fetched_at`; the service compares against `cache_ttl_seconds`; stale triggers refetch; on API failure, serve cache if present.
- **Rationale:** the simplest thing that satisfies both freshness and offline-fallback requirements.

### ADR-007 — Configuration strategy
- **Context:** config spans secrets (API keys), environment-specific values (URLs, paths), and user-tunable defaults.
- **Options considered:** (a) hardcoded constants; (b) env vars + `.env` for secrets, settings file for non-secret defaults.
- **Trade-offs:** hardcoding leaks secrets and resists per-environment change; the env+file split adds a small loading layer.
- **Final decision:** secrets and environment values from environment variables / a gitignored `.env`; non-secret defaults (e.g., cache TTL) from a settings file; loaded once in `config/settings.py`.
- **Rationale:** the twelve-factor "config in the environment" norm; keeps secrets out of history.

### ADR-008 — Logging strategy
- **Context:** need diagnosis without polluting the CLI or leaking secrets.
- **Options considered:** (a) `print`; (b) stdlib `logging` with file + console handlers.
- **Trade-offs:** `print` cannot do levels, routing, or rotation; `logging` needs a small one-time setup.
- **Final decision:** stdlib `logging`, rotating file handler to `data/logs/`, console handler at a higher threshold; configured once in `utils/logger.py`; API keys never logged.
- **Rationale:** standard, dependency-free, and matches the project's "logging where appropriate" standard.

### ADR-009 — Monetary value representation
- **Context:** prices are displayed, not used in user-facing arithmetic, in V1.
- **Options considered:** (a) `float`; (b) `Decimal`.
- **Trade-offs:** `float` carries rounding error but is simple and adequate for display; `Decimal` is correct for money but adds ceremony V1 does not need yet.
- **Final decision:** **`float` in V1**, as a conscious, documented choice (see TD-02), to revisit with the V2 database migration.
- **Rationale:** display-only data does not justify `Decimal` ceremony now; recording it as debt keeps the decision honest.

### ADR-010 — Dependency management strategy
- **Context:** need reproducible installs, clean imports, separated dev tooling, no config sprawl.
- **Options considered:** (a) `requirements.txt` only; (b) `pyproject.toml` as single source with optional-dependency groups, `src/` layout, editable install.
- **Trade-offs:** `requirements.txt` is familiar but carries no metadata, entry points, or tool config; `pyproject.toml` centralizes everything at a slight familiarity cost.
- **Final decision:** **`pyproject.toml` canonical**, runtime vs. `dev` extras separated, `src/` layout, editable install, Ruff/pytest/mypy configured in the same file.
- **Rationale:** modern standard; one source of truth; the `src/` layout prevents importing the un-installed package.

### Remaining open questions
All three live external-provider questions — crypto endpoint terms (ADR-003), football competition
selection (ADR-004), and Toman rate source (ADR-005) — are deliberately deferred to **Milestone M4**,
each absorbed by the adapter pattern so they cannot destabilize earlier milestones. No open question
blocks Milestone M1.

---

## 5. Data Flow

1. **User request** — a menu selection becomes a service method call.
2. **API request** — the service asks a client; the client builds the request, sends it through `base_client` (timeout + retry), receives JSON, and maps it into model objects before returning.
3. **Processing** — the client's mapping step turns raw external JSON into our typed models, where USD→Toman conversion and formatting happen, so the rest of the app never sees raw API shapes.
4. **Storage** — after a successful fetch, the service hands models to the repository, which writes them atomically to JSON with a `fetched_at` timestamp for staleness checks.
5. **Error handling** — failures raise a *custom* exception at the layer where they occur; the service logs and decides on a fallback (serve cache if available); the presentation layer catches anything reaching it and shows a friendly message — never a raw traceback.

---

## 6. Version 1 Frozen Scope

### In scope
- **Crypto:** USD price, computed Toman price, 24h change %, last-update timestamp for **exactly** BTC, ETH, SOL; refresh-on-demand; view single coin; view all coins.
- **Football:** completed matches, upcoming matches, scores, dates/times, team names, tournament progress for **one** competition.
- **Storage:** JSON persistence of cached crypto data, cached football data, settings, user preferences, and request history — all behind the repository interface.
- **Cross-cutting:** environment-based configuration, custom exception hierarchy, file + console logging, timeout + retry on external calls, TTL cache-then-fetch with offline fallback.
- **Interface:** interactive `rich` CLI menu.
- **Quality:** unit tests for models, storage, and services with external boundaries mocked; committed README, architecture doc, and changelog.

### Out of scope
Any database (SQLite/PostgreSQL) — V2/V6. Any web/HTTP API (FastAPI) — V4. Web dashboard — V5.
Auth, async, Docker, CI/CD — V6. Coins beyond BTC/ETH/SOL. Multiple tournaments or live in-match
updates. `Decimal` money arithmetic. Pre-commit hooks. Concurrent/multi-user access. Streaming,
notifications, alerts. Any feature not explicitly listed as in scope. **Scope is frozen.**

---

## 7. Definition of Done

**Functional** — every menu path works (all coins, single coin, refresh, completed + upcoming
football with scores/times); crypto shows USD, Toman, 24h change, and timestamp for all three coins;
stale cache refetches, fresh cache is served, and an unreachable API falls back to cache or a clear
message — never a crash or raw traceback.

**Technical** — fresh-clone install via `pip install -e ".[dev]"` succeeds; the app creates its own
required directories on startup; runs via the `crypto-wc` entry point; no secret appears anywhere in
Git history.

**Architecture** — one-directional dependencies intact (no upward imports, no logic in the UI, no
external schema past the clients); all persistence flows through the repository interface; all
external access flows through adapter clients with timeout + retry.

**Testing** — pytest suite green; models, storage, and services covered; external boundaries mocked
(no test hits a live API).

**Documentation** — README documents setup and usage; `docs/architecture.md` committed; CHANGELOG
reflects the V1 release; `.env.example` lists all required variables.

**Code quality** — Ruff reports no lint/format violations; mypy strict passes; meaningful names;
proper error handling and logging present.

**Git workflow** — every M0–M7 issue closed via a merged PR into a protected `main`; Conventional
Commits used.

**Review** — each PR self-reviewed against the code review checklist before merge; branch protection
verified as actually enforced.

---

## 8. Technical Debt Register

Intentional, recorded compromises — each with a trigger for repayment. Acknowledged debt is
professional; hidden debt is negligence. TD-01 through TD-08 were frozen at design time; TD-09
and TD-10 were discovered during M5/M6 integration and added at V1 closeout.

| ID | Description | Reason | Impact | Severity | Recommended Resolution | Planned Version |
| --- | --- | --- | --- | --- | --- | --- |
| TD-01 | JSON storage, no concurrency safety | Single-user CLI; atomic writes cover the single-writer case | Breaks under concurrent/web access | Medium | Move to SQLite behind the same repository interface | V2 |
| TD-02 | Money as `float` | Display-only in V1; `Decimal` ceremony unjustified now | Rounding error if values ever drive arithmetic | Low | Switch to `Decimal` alongside the DB migration | V2 |
| TD-03 | Manual dependency wiring in `main.py` | Few components; explicit wiring reads more clearly than a container for a learner | Wiring grows verbose as components multiply | Low | Introduce a small composition/DI helper if it becomes unwieldy | V3 |
| TD-04 | Toman price may use a configurable fallback rate | Keeps V1 shippable without a second fragile integration | Displayed Toman value may be approximate | Medium | Adopt a proper rate source | V2/V3 |
| TD-05 | No CI, pre-commit hooks, or automated deployment | Automation is explicitly a V6 concern; adding now is scope creep | Quality gates run manually; human error possible | Low | Add CI pipeline + pre-commit | V6 |
| TD-06 | Single hardcoded football competition | Multi-tournament is out of V1 scope; free tier constrains the choice anyway | Users cannot choose the tournament | Low | Multi-tournament support with a richer tier/source | Post-V1 |
| TD-07 | TTL cache, not sophisticated invalidation | Meets V1 freshness needs simply | Coarse freshness control | Low | Extract a cache strategy object if warranted | V3 |
| TD-08 | Synchronous HTTP (`requests`) | Simpler to learn and sufficient for a CLI | Blocks during slow calls; unsuitable for high concurrency | Low | Move to async (`httpx`) at the `base_client` seam | V6 |
| TD-09 *(Resolved)* | Services depend on concrete clients, not an abstraction | Clients were built before the need for substitution was felt; YAGNI at the time | Test fakes require a `# type: ignore`; the DIP seam is incomplete on the client side | Medium | Extract a `CryptoClientProtocol` / `FootballClientProtocol` and type services against it | V2 |
| TD-10 *(Resolved)* | Ad-hoc unavailable-client stand-in in `main.py` | Graceful football degradation needed a no-key path; a quick stand-in shipped V1 | Structural (not nominal) compatibility; mirrors the TD-09 smell in the composition root | Low | Fold into the TD-09 protocol so the stand-in implements a real interface | V2 |

> **Closeout note (retired risks, not debt).** During development, the storage layer (M3) and
> client layer (M4) were merged ahead of their dedicated test suites, which were scheduled under
> M7. Those were tracked *process risks*, not architectural debt, and were fully retired when M7
> landed: 41 tests green, covering models, storage (real `tmp_path` fixture), and all four service
> orchestration branches. They are recorded here only so the history is honest; they impose no
> ongoing obligation.
---

## 9. Future Roadmap

| Version | Goal | Key change | Technologies introduced |
| --- | --- | --- | --- |
| V2 | Durable, queryable storage | New repository implementation only | `sqlite3` |
| V3 | Cleaner internals | Cache strategy object, richer error/result types | (design patterns) |
| V4 | Expose services over HTTP | New presentation layer (routes) reusing existing services | FastAPI, Pydantic, Uvicorn |
| V5 | Browser UI | Frontend consuming the V4 API | (web frontend) |
| V6 | Production hardening | DB swap, auth, async, containerization, CI/CD | PostgreSQL, SQLAlchemy, async I/O, Docker |

The through-line: because V1 separates presentation, service, and data behind interfaces, each
future version replaces or adds **one** layer without rewriting the others.