# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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