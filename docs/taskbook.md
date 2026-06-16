# Task Book & Project Roadmap

> Static project board for the Crypto & World Cup Information Platform. The
> authoritative design rationale lives in [`architecture.md`](architecture.md);
> this file is the execution roadmap.
>
> **Status: V1 COMPLETE.** All milestones M0–M7 are merged into a protected
> `main`. Every issue below was delivered via a PR using Conventional Commits.

**Difficulty legend:** ⚪ Trivial · 🟢 Easy · 🟡 Medium · 🔴 Hard

---

## Milestone overview

| Milestone | Theme | Status |
| --- | --- | --- |
| M0 | Bootstrap / Project Scaffolding | ✅ Complete (merged) |
| M1 | Foundations (Config / Logging / Exceptions) | ✅ Complete (merged) |
| M2 | Domain Models | ✅ Complete (merged) |
| M3 | Storage Layer | ✅ Complete (merged) |
| M4 | API Clients | ✅ Complete (merged) |
| M5 | Service Layer | ✅ Complete (merged) |
| M6 | Presentation (CLI) | ✅ Complete (merged) |
| M7 | Tests & Documentation | ✅ Complete (merged) |

---

## Milestone M0 — Bootstrap
**Epic:** Project Scaffolding

- [x] **#1 — Create GitHub repository and protect main** — ⚪ · 15 min
- [x] **#2 — Add root documentation files** — 🟢 · 30 min
- [x] **#3 — Add `.gitignore` and `.env.example`** — 🟢 · 20 min
- [x] **#4 — Create full folder tree with `__init__.py` and `.gitkeep`** — 🟢 · 25 min
- [x] **#5 — Configure `pyproject.toml`** — 🟡 · 30 min
- [x] **#6 — Set up Python environment and verify editable install** — 🟢 · 20 min
- [x] **#7 — Add minimal runnable entry point** — 🟢 · 20 min
- [x] **#8 — Commit approved architecture doc** — ⚪ · 10 min

> **M0 closeout:** audit findings C-1 (commit architecture doc) and C-2 (README
> setup/usage) closed via `docs:` PRs. Branch protection verified. Clean Go.

---

## Milestone M1 — Foundations
**Epic:** Cross-Cutting Foundations

- [x] **#9 — Custom exception hierarchy** (`utils/exceptions.py`) — 🟢 · 25 min
- [x] **#10 — Logging setup** (`utils/logger.py`) — 🟡 · 30 min
- [x] **#11 — Settings loader** (`config/settings.py`) — 🟡 · 30 min

> **M1 closeout:** `main.py` wires settings → ensure directories → logging →
> startup log, with graceful `ConfigError` handling. Dual-handler smoke tests
> passed.

---

## Milestone M2 — Domain Models
**Epic:** Domain Modeling

- [x] **#12 — Crypto models** (`models/crypto.py`) — 🟢 · 25 min
  `Coin` enum (BTC/ETH/SOL carrying symbol + full name) and a frozen
  `CryptoPrice` value object. Fields: `symbol`, `name`, `price_usd`,
  `price_toman`, `change_24h`, `last_updated`. Money as `float` (ADR-009).
- [x] **#13 — Football models** (`models/football.py`) — 🟡 · 30 min
  `Team`, `Match`, `Tournament` frozen dataclasses + `MatchStatus` enum
  (SCHEDULED / LIVE / FINISHED). Invariant: scores exist iff the match has
  started. `Tournament.matches` is a tuple for honest immutability.

---

## Milestone M3 — Storage Layer
**Epic:** Persistence

- [x] **#14 — Repository interface** (`storage/base_repository.py`) — 🟡 · 25 min
  Abstract `BaseRepository` with `save` / `load` / `exists` / `delete`. The
  migration seam (ADR-002).
- [x] **#15 — JSON repository** (`storage/json_repository.py`) — 🔴 · 45 min
  Atomic writes (temp file + `os.replace`), the
  `{fetched_at, schema_version, data}` envelope, key-safety validation, and
  `OSError`/`json` → `StorageError` translation.

---

## Milestone M4 — API Clients
**Epic:** External Integrations

- [x] **#16 — Base HTTP client** (`clients/base_client.py`) — 🔴 · 45 min
  Shared `requests.Session`, explicit connect/read timeouts, backoff retries on
  idempotent GETs and retryable statuses, exception → `APIError` mapping.
- [x] **#17 — Crypto client** (`clients/crypto_client.py`) — 🔴 · 45 min
  CoinGecko (ADR-003), single-request fetch for all coins, mapping to
  `CryptoPrice`, USD→Toman conversion via injected rate (ADR-005).
- [x] **#18 — Football client** (`clients/football_client.py`) — 🔴 · 45 min
  Football-Data.org (ADR-004), status mapping, defensive per-match parsing,
  point-of-use API-key validation.

> **M4 closeout:** ADR open items resolved — CoinGecko endpoint confirmed
> (ADR-003), competition selected (ADR-004), USD→Toman rate sourced with a
> configurable fallback (ADR-005 / TD-04).

---

## Milestone M5 — Service Layer
**Epic:** Orchestration

- [x] **#19 — Crypto service** (`services/crypto_service.py`) — 🟡 · 35 min
  Cache-then-fetch with TTL staleness (ADR-006); client + repository injected;
  offline fallback to cache; re-validating deserialization.
- [x] **#20 — Football service** (`services/football_service.py`) — 🟡 · 35 min
  The same orchestration pattern applied to `Tournament`.

---

## Milestone M6 — Presentation (CLI)
**Epic:** User Interface

- [x] **#21 — Renderers** (`presentation/renderers.py`) — 🟡 · 40 min
  `rich` tables for coins and matches. Pure formatting, no logic.
- [x] **#22 — Interactive menu** (`presentation/menu.py`) — 🟡 · 40 min
  Input loop dispatching to services; `AppError` caught at the UI boundary.
- [x] **#23 — Wire dependencies in `main.py`** — 🟡 · 30 min
  Composition root constructs and injects all dependencies and launches the
  menu (TD-03). Required a `refactor:` to `Settings` adding `usd_to_toman_rate`.

---

## Milestone M7 — Tests & Documentation
**Epic:** Quality & Documentation

- [x] **#24 — Model tests** — 🟢 · 30 min
  Invariants, happy paths, immutability; grouped by model, keyword construction.
- [x] **#25 — Storage tests** — 🟡 · 40 min
  Round-trip, missing-key, corrupted-file, future-schema, idempotent delete,
  unsafe-key rejection — using a real `tmp_path` fixture.
- [x] **#26 — Service tests** — 🔴 · 45 min
  In-memory fakes for client + repository; all four orchestration branches
  (fresh / stale / offline-fallback / total-failure).
- [x] **#27 — Finalize README and architecture docs** — 🟢 · 30 min
  README updated to full V1 usage; ADRs reconciled; CHANGELOG released.

> **M7 closeout:** 52 tests green (reduced to 49 in V2). Ruff clean, mypy strict passing. End-to-end
> run verified including the offline-fallback path against a downed network.

---

## Milestone V2 — SQLite & Price History
**Epic:** Durable, queryable storage · **Status:** 🚧 In progress

- [x] **Client Protocols** (`clients/protocols.py`) — `CryptoClientProtocol` /
  `FootballClientProtocol`; services typed against them; the test `type: ignore` removed and the
  unavailable-football stand-in now implements a real interface (TD-09 / TD-10).
- [x] **Repository interface redesign** (`storage/base_repository.py`) — evolve from generic
  key→dict to domain-specific methods; add the generic `Cached[T]` envelope (ADR-011).
- [x] **SQLiteRepository** (`storage/sqlite_repository.py`) — normalized schema
  (`price_history`, `tournament`, `match`), append-only prices, snapshot-only tournament,
  `sqlite3` → `StorageError` translation (TD-01).
- [x] **Price-history feature** — `CryptoService.get_price_history`, `render_price_history`,
  and a new menu option.
- [x] **Tests** — SQLite repository suite (`tests/test_sqlite_repository.py`); service fake updated
  to the new interface; config tests isolated from a real `.env`. JSON repo + its tests retired.
- [x] **Money → `Decimal`** (TD-02) — complete.
- [x] **Real USD→Toman rate source** (TD-04) — complete.

> **V2 status:** All tasks completed! 49 tests green; `ruff` + `mypy --strict` clean. Storage swapped from JSON to SQLite, floats to Decimal, and fiat API replaced natively.

---

## Definition of Done (V1) — met

Full criteria in [`architecture.md`](architecture.md) §7. Verified at release:
every menu path works; crypto shows USD/Toman/24h/timestamp for BTC/ETH/SOL;
cache serves-fresh / refetches-stale / falls-back-offline without crashing;
fresh-clone editable install runs via `crypto-wc`; no secret in history;
Ruff + mypy strict + pytest all green; docs committed; every issue closed via
PR into protected `main`.