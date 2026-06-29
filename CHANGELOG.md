# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [9.0.0] — 2026-06-29 — Swapwallet-style coin list & group-ready bot

### Added — Phase 1: Global coin list (CoinGecko)
- **Added** `CoinGeckoClient` behind a new `MarketDataClientProtocol`: logos,
  market cap, 24h volume, market-cap rank, and a 7-day sparkline in one request
- **Extended** `CryptoPrice` and the storage layer with `market_cap`,
  `volume_24h`, `rank`, `image_url`, and `sparkline` (persisted for offline use)
- **Reworked** `CryptoService` to source the crypto list from CoinGecko and
  enrich each coin with a Toman price from Wallex (direct pair or USDT-rate
  conversion); metals/fiat/bourse and stale-cache fallback preserved
- **Redesigned** the web coin list: rank column, sortable headers, compact
  market cap/volume, inline SVG 7-day sparklines, responsive column hiding
- **Added** `COINGECKO_API_KEY` setting (optional CoinGecko Demo key)

### Added — Phase 2: Telegram bot optimized for groups
- **Added** `app/bot/search.py` — pure, unit-tested query matching with Persian
  aliases (بیتکوین→BTC, تتر→USDT, طلا→XAUT, …) and filler-word stripping
- **Added** free-text price answers via @mention, reply-to-bot, or any private
  message; stays silent on unrelated group chatter
- **Added** auto-greeting with usage help when the bot is added to a group
  (`ChatMemberHandler`), a context-aware `/help`, and the `/p` alias for `/price`
- **Added** the slash-command menu via `set_my_commands` (private + group scope)
- **Improved** inline query: shared search logic, coin-logo thumbnails, and a
  graceful "no results" / "market unavailable" fallback
- **Added** `docs/telegram-bot.md` — BotFather setup, privacy mode, and group usage

### Added — Phase 3: Persian names, coin detail page, live-data docs
- **Added** Persian asset names to the web coin list: the service now localizes
  each CoinGecko coin with the Wallex Persian name when available
- **Added** a coin detail page (`/coin/{symbol}`): header card, market-cap /
  volume / rank stats, an interactive TradingView chart for crypto (with a
  7-day sparkline fallback), and recent observations from stored history
- **Made** asset names in the list clickable, linking to their detail page
- **Documented** the network egress domains required for live data in the
  README (CoinGecko, Wallex, ExchangeRate, Yahoo)

### Fixed
- **Auto-migrate the SQLite/Postgres schema on startup**: `initialize()` now adds
  any model columns missing from an existing table (lightweight `ADD COLUMN`, no
  Alembic). Fixes `OperationalError: no such column: price_history.image_url`
  when running against a database created before the v9 columns existed.

### Tests
- New tests for the CoinGecko client, the source-merge logic (incl. Persian
  name override), the new model fields, the bot search helpers, the web
  dashboard/detail routes, and the startup schema migration.
  **Result: 64 tests, 64 passed.**

---

## [8.0.0] — 2026-06-19 — MarketPulse Transformation

### Changed — Phase 1: Codebase Cleanup
- **Fixed** broken import syntax in `bot/main.py` (missing closing parenthesis after `InlineQueryHandler`)
- **Added** `image_url: str = ""` field to `CryptoPrice` model to match template usage
- **Renamed** FastAPI app title from "Crypto & World Cup API" to "MarketPulse API"
- **Cleaned** stale docstrings referencing football/worldcup from `settings.py`
- **Removed** duplicate `_DEFAULT_CACHE_TTL_SECONDS` assignment in `settings.py`
- **Updated** `README.md` to reflect MarketPulse brand and current feature set

### Removed — Phase 2: Iran Bourse Dropped
- **Removed** `IranBourseClient` and `iran_bourse_client.py` entirely — TSETMC API was unreliable and returned empty data in testing
- **Removed** `IranBourseClientProtocol` from `protocols.py`
- **Removed** `IRAN_BOURSE` from `AssetType` enum
- **Removed** Iran bourse tab from web dashboard
- **Cleaned** all references from `CryptoService`, `Container`, templates, and tests

### Fixed — Tests
- Removed all football/worldcup references from test suite (`test_models.py`, `test_services.py`, `test_config.py`, `test_routes.py`, `test_sqlalchemy_repository.py`)
- Added `FakeBourseClient` to service tests to match updated `CryptoService` signature
- Fixed timestamp comparison bug in `test_latest_reflects_most_recent_batch`
- Added two new tests for the `image_url` field on `CryptoPrice`
- **Result: 35 tests, 35 passed**

---

## [1.0.0] — 2026-06-14

First stable release. A Python 3.12 terminal application delivering live
cryptocurrency prices (BTC, ETH, SOL) and football tournament data through a
clean, layered, offline-first architecture. All milestones M0–M7 complete;
every clause of the V1 Definition of Done met and verified end-to-end,
including the offline-fallback path against a disconnected network.

### Added

- **Domain models** — frozen, validated dataclasses: a `Coin` enum and
  `CryptoPrice`; `Team`, `Match`, `Tournament`, and a `MatchStatus` enum. Value
  objects whose invariants are enforced at construction (e.g. scores exist iff a
  match has started; timestamps must be timezone-aware).
- **Storage layer** — a `BaseRepository` abstraction (the migration seam) with a
  `JSONRepository` implementation: atomic writes via temp file + `os.replace`, a
  `{fetched_at, schema_version, data}` envelope, and key-safety validation.
- **API clients** — a shared `BaseAPIClient` (session reuse, explicit
  connect/read timeouts, exponential-backoff retries on idempotent requests) and
  two adapters: CoinGecko (crypto) and Football-Data.org (football). Each maps
  raw API JSON into typed domain models — an anti-corruption layer — and
  validates its API key at point of use.
- **Service layer** — crypto and football services implementing cache-then-fetch
  with TTL staleness and offline fallback; client and repository injected via the
  constructor; deserialization re-validates cached data through the models.
- **Presentation layer** — `rich` renderers (pure formatting) and an interactive
  CLI menu that dispatches to services and catches application errors at the
  boundary, so the user never sees a raw traceback.
- **Composition root** — `main.py` wires every layer in dependency order
  (settings → directories → logging → data → services → menu) and degrades
  gracefully when the football API key is absent.
- **Foundations** — environment-based frozen `Settings` loader, a custom
  `AppError` exception hierarchy with boundary translation, and centralized
  rotating-file + console logging.
- **Configuration** — `USD_TO_TOMAN_RATE` setting added to support the ADR-005
  conversion with a configurable fallback rate.
- **Tests** — 52 passing across model invariants, the JSON repository (real
  temporary-directory fixture), and all four service orchestration branches
  (fresh / stale / offline-fallback / total-failure) using in-memory fakes. No
  test touches a live API or the real filesystem outside its fixture.
- **Documentation** — production README, architecture document with ten ADRs and
  a technical-debt register, completed taskbook, and V1 release notes.

### Notes

- **Tooling gates green at release:** `ruff` clean, `mypy --strict` passing,
  `pytest` all green.
- **Known debt** is tracked openly in `docs/architecture.md` §8 (TD-01 through
  TD-10), led by the planned V2 SQLite migration behind the existing repository
  interface.

[1.0.0]: https://github.com/your-org/crypto-worldcup-platform/releases/tag/v1.0.0