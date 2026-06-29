# Architecture & Governance — MarketPulse

> **Status:** Living document. It is the source of truth for the project's architecture and the
> decisions behind it. Load-bearing decisions are recorded as ADRs (below and in
> [`decisions.md`](decisions.md)); they are revised by adding a new ADR, not by quietly rewriting
> an old one.
>
> **History note.** The project began as a "Crypto & World Cup" learning CLI and evolved, version
> by version, into **MarketPulse** — a multi-channel market-data platform. The early ADRs and the
> technical-debt register below are kept as an honest record of that journey; sections 1, 3, 5, 6
> and 9 describe the system **as it is today**.

---

## 1. Overview

**MarketPulse** is a Python 3.12+, fully-async platform that delivers real-time prices for
cryptocurrencies, fiat currencies, precious metals, and global stock indices through three
presentation channels over one shared core: a **web dashboard** (FastAPI + Jinja2 + HTMX), a
**Telegram bot** (python-telegram-bot), and an interactive **CLI** (`rich`).

The central architectural bet is **dependency inversion**: application logic never talks to a
database or an HTTP API directly — it talks to *abstractions*. That single decision is what let
the project migrate (JSON → SQLite → SQLAlchemy/PostgreSQL, CLI → REST → web → bot, sync → async)
by swapping implementations behind stable seams rather than rewriting the system.

It is **offline-first**: every external call is cached with a TTL, and an unreachable API serves
the last good cache instead of crashing.

---

## 2. Layered Architecture

Dependencies flow in **one direction only**. A lower layer never imports an upper layer.

```
[ Web · Telegram bot · CLI ]   →   [ CryptoService ]   →   [ Clients (external APIs) ]
                                          ↓
                                  [ Repository (SQLAlchemy) ]
            ( Utilities & Configuration available to every layer )
```

| Layer | Location | Responsibility |
| --- | --- | --- |
| Presentation | `src/app/api/`, `src/app/bot/`, `src/app/presentation/` | The channels users touch — web, bot, CLI. Read input, call the service, render. **No** business logic. |
| Service | `src/app/services/` | Orchestration and business rules (cache-then-fetch, multi-source merge, staleness). Depends only on *interfaces* of the layers below, injected via constructors. |
| Data | `src/app/clients/`, `src/app/storage/` | External (API adapters) and internal (persistence) access, each hidden behind its own abstraction. |
| Utility | `src/app/utils/`, `src/app/config/` | Cross-cutting concerns: logging, exceptions, configuration, the DI container. |

**Interaction rule:** Presentation → Service → Data, never the reverse.

---

## 3. Folder Structure

```
crypto-worldcup-platform/
├── src/app/
│   ├── main.py                 # CLI composition root
│   ├── main_bot.py             # Telegram bot entry point
│   ├── api/                    # FastAPI app, routers (dashboard, crypto), dependencies
│   ├── bot/                    # handlers, inline, search, jobs, formatters
│   ├── config/                 # settings.py (frozen Settings) + container.py (DI)
│   ├── models/                 # crypto.py — CryptoPrice dataclass + AssetType enum
│   ├── services/               # crypto_service.py, cache_strategy.py
│   ├── clients/                # base_client + coingecko, crypto (Wallex), fiat, bourse + protocols
│   ├── storage/                # base_repository (interface) + sqlalchemy_repository + models
│   ├── presentation/           # rich CLI renderers + menu
│   ├── templates/              # Jinja2: base, dashboard, coin_detail, partials/
│   └── static/                 # css/style.css, js/main.js
├── tests/                      # mirrors the source tree (no live API, no real DB)
├── docs/                       # this document, decisions, roadmap, handoff, release notes
├── data/                       # runtime files (gitignored): app.db, logs/
├── Dockerfile  docker-compose.yml  .env.example  .python-version
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
- **Final decision:** **CoinGecko for V1**, behind the adapter. Swapped to **Wallex in V2**.
- **Rationale:** lowest friction for a learning project; the adapter quarantines the choice so a swap costs one file. In V2, Wallex provided native USD and Toman prices together.
- **Open item:** verify current free-tier terms and exact endpoint at the start of Milestone M4. (Done in V1; replaced in V2).

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
- **Final decision:** **compute from a USD→Toman rate** sourced at M4, with a configurable fallback rate (clearly labeled approximate) if no reliable free rate API is found. (V1). **Native Wallex Toman pairs** used directly in V2.
- **Rationale:** keeps V1 shippable without a second fragile integration; honesty about approximation is acceptable for a display-only value. V2 eliminated this need entirely.

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

### ADR-011 — V2 storage: SQLite with a normalized schema, and a domain-specific repository
- **Context:** V2 introduces a price-history / query capability. V1's repository was a generic
  key→dict cache (one JSON file per key), which cannot express "give me BTC's last N prices."
- **Options considered:** (a) keep the key→dict interface and store a JSON blob in one SQLite
  column (a true drop-in swap, but SQLite used as a dumb blob store — no queryable history);
  (b) a normalized schema (`price_history`, `tournament`, `match`) behind a domain-specific
  repository interface (`save_prices`/`load_latest_prices`/`get_price_history`/...).
- **Trade-offs:** (a) preserves the "swap, not rewrite" thesis but delivers no real query power;
  (b) delivers history/queries and uses SQL properly, at the cost of evolving the repository
  interface and the services that depend on it.
- **Final decision:** **(b)** — normalized schema + domain-specific `BaseRepository`. JSON is
  retired; SQLite (stdlib `sqlite3`) becomes the sole implementation. The seam still holds: the
  in-memory fake in the tests and `SQLiteRepository` both implement the same ABC.
- **Rationale:** the interface change is justified by a genuine new capability, not gratuitous
  rework. `float`→`Decimal` (TD-02) is deferred to a follow-up within V2.

### ADR-012 — Result pattern over Exception raising in Services
- **Context:** V3 OOP refactoring. `CryptoService` and `FootballService` used to raise `APIError` when offline and cache-miss occurred.
- **Options considered:** (a) Keep raising standard Exceptions; (b) Introduce a Monad-like `Result[T, E]` type (`Ok` / `Err`).
- **Trade-offs:** Exceptions are standard Python but hide failure modes in type signatures; `Result` explicitly forces the caller to handle both success and error cases, improving safety at the cost of slight boilerplate.
- **Final decision:** **Adopt the `Result` pattern** for service layer returns.
- **Rationale:** Aligns with Clean Architecture's emphasis on explicit boundaries.

### ADR-013 — Lightweight Dependency Injection Container
- **Context:** V3 DI refactoring. `main.py` manually wired all dependencies (TD-03).
- **Options considered:** (a) Extract to a factory function; (b) Custom lightweight `Container` class; (c) Third-party library like `dependency-injector`.
- **Trade-offs:** Third-party adds heavy dependency for a simple project; factory function is okay but doesn't store singletons easily; custom class is simple, explicit, and educational.
- **Final decision:** **Custom `Container` class**.
- **Rationale:** Maximizes learning without adding external bloat.

### ADR-014 — API Response Models using native Dataclasses
- **Context:** FastAPI typically uses Pydantic models (`BaseModel`) for defining request/response schemas. V4 exposed the existing services via REST.
- **Options considered:** (a) Wrap domain `dataclasses` in Pydantic `BaseModel`s; (b) Use the existing standard `dataclass`es directly as `response_model`s.
- **Trade-offs:** Pydantic models are FastAPI's native language, offering extensive validation. However, FastAPI (via Pydantic's core) natively supports standard library `dataclass`es. Creating duplicate Pydantic models solely for output would violate DRY without adding value, given the models are read-only at the API boundary.
- **Final decision:** **Use existing `dataclass`es natively.**
- **Rationale:** Simplifies the codebase, avoids redundant schema definitions, and proves that clean domain models don't need web-framework-specific wrappers just to be serialized.

### ADR-015 — CoinGecko as the global crypto source, merged with Wallex
- **Context:** the swapwallet-style coin list needs logos, market cap, 24h volume, rank, and a 7-day
  sparkline — none of which Wallex provides. Wallex, however, provides native Toman prices and
  Persian names, which CoinGecko lacks.
- **Options considered:** (a) Wallex only (no market cap / logos / sparklines); (b) CoinGecko only
  (no Toman / Persian names); (c) **merge** — CoinGecko for the rich global list, Wallex for Toman
  enrichment and localization.
- **Final decision:** **(c)**. `CoinGeckoClient` (behind a new `MarketDataClientProtocol`) owns the
  crypto list; `CryptoService` enriches each coin with the Wallex Toman price (direct TMN pair, else
  converted via the USDT/Toman rate) and the Wallex Persian name when available.
- **Rationale:** each provider does what it is best at; the adapter + protocol seams made adding a
  second source a new file, not a rewrite. Offline-first is preserved: CoinGecko down → Wallex
  crypto entries; all sources down → stale cache.
- **Consequences:** `CryptoPrice` gained `market_cap`, `volume_24h`, `rank`, `image_url`, and
  `sparkline`, all persisted for offline rendering.

### ADR-016 — Group-ready Telegram bot with a pure search core
- **Context:** the bot was private-chat oriented. Groups apply Telegram's privacy mode, so a bot
  only sees commands, @mentions, and replies to its own messages unless privacy is disabled.
- **Options considered:** (a) commands only; (b) require privacy mode off and read all messages;
  (c) **respond to mentions/replies in groups (privacy-on friendly) and free text in private**,
  with optional privacy-off for free-text group answers.
- **Final decision:** **(c)**. Query matching lives in a pure, unit-tested module
  (`app/bot/search.py`) with Persian aliases and filler-word stripping, shared by the inline and
  in-chat handlers. A `ChatMemberHandler` greets groups on join; the command menu is registered via
  `set_my_commands`.
- **Rationale:** keeping the matching logic free of Telegram/network types makes the group behavior
  testable without a bot token, and the same logic powers inline queries and chat replies.
- **Consequences:** behavior depends on the BotFather privacy setting; documented in
  [`telegram-bot.md`](telegram-bot.md).

### Resolved open questions
The original V1 open questions (crypto endpoint terms, football competition, Toman rate source) are
all resolved: football was dropped in the MarketPulse pivot; crypto is CoinGecko + Wallex (ADR-015);
Toman comes from native Wallex pairs.

---

## 5. Data Flow

1. **Request** — a web route, bot handler, or CLI menu calls `CryptoService.get_prices()`.
2. **Cache check** — the service loads the latest cached batch; if fresh (within `CACHE_TTL_SECONDS`) it is returned immediately, no network.
3. **Multi-source fetch** — otherwise the service fetches from each client through `base_client` (async httpx, timeout + retry). Each client maps raw JSON into `CryptoPrice` models (the anti-corruption layer), so no API shape leaks upward.
4. **Merge** — the crypto list comes from **CoinGecko** (logos, market cap, volume, rank, sparkline); each coin is enriched with a **Toman price** and **Persian name** from **Wallex**; fiat (EUR/GBP), metals, and stocks are appended.
5. **Storage** — the merged batch is saved via the repository with a `fetched_at` timestamp; price history is append-only.
6. **Fallback & errors** — failures raise a *custom* exception at their layer; the service degrades gracefully (CoinGecko down → Wallex crypto; all sources down → stale cache; cold cache → `Err`). Presentation never shows a raw traceback.

---

## 6. Current Capabilities

### In scope (shipped)
- **Markets:** a CoinMarketCap-style crypto coin list (USD + Toman price, 24h change, market cap, 24h volume, rank, 7-day sparkline) plus fiat (EUR/GBP), metals (XAUT/PAXG), and global stocks/indices.
- **Web:** dashboard with search, market tabs, sortable columns, 30s HTMX polling, and a per-coin detail page (`/coin/{symbol}`) with a TradingView chart and stored history.
- **Telegram bot:** `/market`, `/price` (+ `/p`), `/watchlist`, inline query, and a daily brief; group-ready (mention/reply/free-text answers, join-greeting, command menu).
- **Storage:** SQLAlchemy 2.0 async (SQLite dev / PostgreSQL prod) behind the repository interface; TTL cache-then-fetch with offline fallback and price history.
- **Cross-cutting:** env-based config, custom exception hierarchy, file + console logging, async timeout + retry, Docker + Docker Compose, GitHub Actions CI.

### Out of scope (for now)
Real trade execution (the dashboard buy/sell buttons are placeholders). Authentication / multi-user accounts. Price-alert subscriptions and portfolio tracking (roadmap). Native mobile app. Live in-market streaming.

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
| TD-01 *(Resolved)* | JSON storage, no concurrency safety | Single-user CLI; atomic writes cover the single-writer case | Breaks under concurrent/web access | Medium | Move to SQLite behind the same repository interface | Done (V2) ✅ |
| TD-02 *(Resolved)* | Money as `float` | Display-only in V1; `Decimal` ceremony unjustified now | Rounding error if values ever drive arithmetic | Low | Switch to `Decimal` alongside the DB migration | Done (V2) ✅ |
| TD-03 *(Resolved)* | Manual dependency wiring in `main.py` | Few components; explicit wiring reads more clearly than a container for a learner | Wiring grows verbose as components multiply | Low | Introduce a small composition/DI helper if it becomes unwieldy | Done (V3) ✅ |
| TD-04 *(Resolved)* | Toman price may use a configurable fallback rate | Keeps V1 shippable without a second fragile integration | Displayed Toman value may be approximate | Medium | Adopt a proper rate source (Wallex) | Done (V2) ✅ |
| TD-05 | No CI, pre-commit hooks, or automated deployment | Automation is explicitly a V7 concern; adding now is scope creep | Quality gates run manually; human error possible | Low | Add CI pipeline + pre-commit | Done (V7) ✅ |
| TD-06 | Single hardcoded football competition | Multi-tournament is out of V1 scope; free tier constrains the choice anyway | Users cannot choose the tournament | Low | Multi-tournament support with a richer tier/source | Post-V1 |
| TD-07 *(Resolved)* | TTL cache, not sophisticated invalidation | Meets V1 freshness needs simply | Coarse freshness control | Low | Extract a cache strategy object if warranted | Done (V3) ✅ |
| TD-08 *(Resolved)* | Synchronous HTTP (`requests`) | Simpler to learn and sufficient for a CLI | Blocks during slow calls; unsuitable for high concurrency | Low | Move to async (`httpx`) at the `base_client` seam | Done (V7) ✅ |
| TD-09 *(Resolved)* | Services depend on concrete clients, not an abstraction | Clients were built before the need for substitution was felt; YAGNI at the time | Test fakes require a `# type: ignore`; the DIP seam is incomplete on the client side | Medium | Extract a `CryptoClientProtocol` / `FootballClientProtocol` and type services against it |  Done (V2) ✅ |
| TD-10 *(Resolved)* | Ad-hoc unavailable-client stand-in in `main.py` | Graceful football degradation needed a no-key path; a quick stand-in shipped V1 | Structural (not nominal) compatibility; mirrors the TD-09 smell in the composition root | Low | Fold into the TD-09 protocol so the stand-in implements a real interface |  Done (V2) ✅ |

> **Closeout note (retired risks, not debt).** During development, the storage layer (M3) and
> client layer (M4) were merged ahead of their dedicated test suites, which were scheduled under
> M7. Those were tracked *process risks*, not architectural debt, and were fully retired when M7
> landed: 49 tests green, covering models, storage (real `tmp_path` fixture), and all four service
> orchestration branches. They are recorded here only so the history is honest; they impose no
> ongoing obligation.
> **V2 update.** TD-01 (JSON→SQLite) is resolved via `SQLiteRepository` behind the repository seam
> (ADR-011). TD-09 / TD-10 (client-side DIP seam) are resolved via `clients/protocols.py`. 
> TD-02 is resolved by migrating all monetary fields to `Decimal`.
> TD-04 is resolved by replacing CoinGecko and Fiat integrations with a direct integration to Wallex.
> Note that V2 also *evolved* the repository interface itself (ADR-011), so the "services never change"
> framing of the original ADR-002 held for the client seam but not for storage — by design, to add
> the price-history capability.
---

## 9. Version History & Roadmap

| Version | Goal | Status |
| --- | --- | --- |
| V1 | JSON-backed CLI (crypto + football) | ✅ shipped |
| V2 | Durable, queryable storage (SQLite, price history, `Decimal`, Wallex) | ✅ shipped |
| V3 | Cleaner internals (`Result`, cache strategy, DI container) | ✅ shipped |
| V4 | REST API over the existing services (FastAPI) | ✅ shipped |
| V5 | Web dashboard (Jinja2 + HTMX), dynamic multi-asset domain | ✅ shipped |
| V6 | Telegram bot channel | ✅ shipped |
| V7 | Production hardening (SQLAlchemy, PostgreSQL, async, Docker, CI) | ✅ shipped |
| V8 | MarketPulse pivot (drop football, multi-market focus) | ✅ shipped |
| V9 | Swapwallet-style coin list (CoinGecko), group-ready bot, coin detail page, Persian names | ✅ shipped |
| V10 (planned) | Real trade actions, price alerts, portfolio tracking, PWA/mobile | ⏳ planned |

The through-line: because presentation, service, and data sit behind interfaces, each version
replaced or added **one** seam without rewriting the others.