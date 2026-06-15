# Engineering Handoff

> **Purpose.** This document is the bridge between development sessions. It is written so a
> fresh session (with no prior conversation context) can resume work immediately and correctly.
> Read this together with [`architecture.md`](architecture.md) (design rationale, ADRs, frozen
> scope, Definition of Done, technical-debt register), [`taskbook.md`](taskbook.md) (the
> issue-by-issue execution record), and [`v1-release-note.md`](v1-release-note.md) (the V1
> closeout). [`roadmap.md`](roadmap.md) holds the strategic V1–V6 view.

**Last updated:** V1.0.0 closeout — all milestones M0–M7 complete and merged.
**Branch state:** V1 work merged into a protected `main`.

---

## 1. Project in one paragraph

A Python 3.12+ terminal application that displays cryptocurrency prices (BTC, ETH, SOL) and
football tournament data, built as a portfolio-grade demonstration of clean, layered architecture.
Dependencies flow one direction only: Presentation → Service → Data, with Utilities and Config
available to all layers. Persistence is JSON behind a repository interface (the seam for a future
SQLite/PostgreSQL migration). External APIs sit behind adapter clients (an anti-corruption layer).
The project is built issue by issue, each on its own feature branch, merged via PR into a protected
`main` using Conventional Commits. The mentoring style is deliberate: concept → plan → code →
review for every piece, readability over cleverness, and every compromise recorded as tracked debt.

---

## 2. Current project status — what is built, integrated, and verified

**V1 is feature-complete.** The full four-layer architecture is implemented end to end: a user can
run `crypto-wc`, view all coins / a single coin / the World Cup table, and the app caches every
fetch, falls back to stale cache when an API is down, and never surfaces a raw traceback. All
milestones below are merged.

| Milestone | Theme | Status |
| --- | --- | --- |
| M0 | Bootstrap / Scaffolding | ✅ Complete |
| M1 | Foundations (exceptions, logging, settings) | ✅ Complete |
| M2 | Domain Models (crypto, football) | ✅ Complete |
| M3 | Storage Layer (repo interface + JSON impl) | ✅ Complete |
| M4 | API Clients (base + CoinGecko + Football-Data) | ✅ Complete |
| M5 | Service Layer (cache-then-fetch orchestration) | ✅ Complete |
| M6 | Presentation (rich renderers + menu + wiring) | ✅ Complete |
| M7 | Tests & Documentation | ✅ Complete |

### What physically exists in `src/app/`
- `utils/exceptions.py` — `AppError` base with `ConfigError` / `StorageError` / `APIError`.
- `utils/logger.py` — `setup_logging` (rotating file at DEBUG+, console at WARNING+) and
  `get_logger`. Idempotent; lazy `%`-formatting; never logs secrets.
- `config/settings.py` — frozen `Settings` with `from_env()`, derived directory `@property`s, and
  `ensure_directories()`. Fields: `data_dir`, `cache_ttl_seconds`, `usd_to_toman_rate`,
  `crypto_api_key`, `football_api_key`.
- `models/crypto.py` — `Coin` enum (BTC/ETH/SOL carrying symbol + full name) and frozen `CryptoPrice`
  with construction-time validation.
- `models/football.py` — frozen `Team`, `Match`, `Tournament` and a `MatchStatus` enum
  (SCHEDULED/LIVE/FINISHED). Invariant: scores exist iff the match has started. `Tournament.matches`
  is a tuple (honest immutability).
- `storage/base_repository.py` — abstract `BaseRepository` (`save`/`load`/`exists`/`delete`); the
  migration seam (ADR-002).
- `storage/json_repository.py` — `JSONRepository`: atomic writes (temp file + `os.replace` + fsync),
  the `{fetched_at, schema_version, data}` envelope, key-safety regex, schema-version mismatch →
  treated as missing, `OSError`/`json` → `StorageError`.
- `clients/base_client.py` — `BaseAPIClient`: shared `requests.Session`, `(5s, 15s)` timeouts,
  urllib3 `Retry` (backoff 0.5, statuses {429,500,502,503,504}, GET only), every `requests`
  exception → `APIError`. Context-manager support.
- `clients/crypto_client.py` — CoinGecko `/simple/price` adapter; maps to `CryptoPrice`; derives
  Toman from the injected USD→Toman rate (ADR-005); optional demo-key header.
- `clients/football_client.py` — Football-Data.org v4 `/competitions/WC/matches` adapter; status
  map; defensive per-match parsing (a single bad match is skipped, a structural break raises);
  point-of-use API-key validation.
- `services/cache_policy.py` — shared `is_fresh(envelope, ttl)`; missing/unparseable `fetched_at`
  is treated as stale (safe default). Extracted to keep both services from drifting.
- `services/crypto_service.py` / `services/football_service.py` — cache-then-fetch with TTL and
  offline fallback (ADR-006); client + repository injected; cache deserialization re-runs model
  validation.
- `presentation/renderers.py` — pure `rich` tables for prices and matches (colour-coded change and
  status). No logic, no I/O.
- `presentation/menu.py` — interactive loop dispatching to services; `ConfigError` shown as
  "Unavailable", any other `AppError` shown as a friendly line.
- `main.py` — composition root: settings → directories → logging → repository + clients → services
  → menu. Degrades gracefully when `FOOTBALL_API_KEY` is absent via an unavailable-client stand-in
  (TD-10).

### Verification state (run from a Python 3.12 venv)
- **Tests: 52 passing** (`tests/test_config.py` 8, `tests/test_models.py` 24,
  `tests/test_storage.py` 9, `tests/test_services.py` 11). No test touches a live API or the real
  filesystem outside a `tmp_path` fixture.
  > Note: earlier docs cite "41 tests"; the suite has since grown to 52 (config tests added with the
  > `usd_to_toman_rate` fix). The CHANGELOG / release note figure is stale on this point.
- **`ruff check .`** — clean. **`mypy --strict src`** — clean (24 source files).
- **End-to-end** — menu paths verified, including the offline-fallback path against a downed network.

---

## 3. Known issues found at this handoff (read before continuing)

1. **Merge-conflict markers in `tests/test_services.py`.** A PR-#16 merge left raw
   `<<<<<<< / ======= / >>>>>>>` markers in the `SETTINGS` literal, which was a *syntax error* —
   the entire pytest suite failed to collect, despite the docs claiming green tests. Resolve by
   keeping the `usd_to_toman_rate=90_000.0` line (the field is required on `Settings`).
   **Lesson:** the V1 "all green" claim in the CHANGELOG and release note was not actually true on
   `main`. Always run the suite; never trust the doc.
2. **Stray artifacts.** `cryptowcreview.patch` (a committed review patch) and
   `docs/developments/M0` (an empty 0-byte file beside `M0.md`) are accidental cruft — delete them.
3. **TD-09 / TD-10 (client-side DIP seam incomplete).** Services and `main.py` depend on *concrete*
   client classes; the test fakes need a `# type: ignore[arg-type]`, and `main.py` carries an ad-hoc
   `_UnavailableFootballClient` stand-in. See §5.

---

## 4. Conventions the next session must preserve

- **Mentoring loop:** for each issue — explain the concept and any new Python features, present an
  implementation plan, give the complete file, then review against the checklist and note any
  deliberate seams/debt. Readability over cleverness. One question at a time when clarifying.
- **Exception translation at boundaries:** clients raise `APIError`; storage raises `StorageError`;
  config raises `ConfigError`. Never let `requests` / `json` / `OSError` leak upward. Use `from exc`.
- **Logging:** module-level `get_logger(__name__)`; configure only in `main.py`; lazy `%` formatting;
  never log secrets.
- **Config:** nothing reads `os.environ` except `settings.py`. Inject `Settings`; don't use globals.
- **Money:** `float` in V1 (ADR-009, debt TD-02). **Coins are exactly BTC, ETH, SOL** — V1 frozen.
- **Workflow:** one feature branch per issue, Conventional Commits, PR into protected `main`.
- **Quality gates before any PR:** `ruff check .`, `ruff format .`, `mypy --strict src`, and
  `pytest` — **all green**, run on Python 3.12 (the project requires `>=3.12`; a 3.11 interpreter
  cannot even install it).
- **Scope discipline:** build the seam, not the speculative feature. Record any compromise in the
  debt register (`architecture.md` §8).

---

## 5. Precise next steps — where to pick up the knife

V1 is shipped, so the next work is **V2** (or pre-V2 cleanup). Cheapest high-value items first:

### Immediate cleanup
- Delete `cryptowcreview.patch` and the empty `docs/developments/M0` file.
- Reconcile the test-count figure (52, not 41) in `CHANGELOG.md` and `v1-release-note.md`.
- Add a minimal CI workflow (ruff + mypy + pytest on push) — the single guard that would have caught
  the conflict-marker bug before merge (currently deferred as TD-05).

### V2 — the storage swap (the headline migration the architecture was built for)
1. **TD-09 / TD-10 first (small, enabling refactor).** Extract `CryptoClientProtocol` /
   `FootballClientProtocol` (`typing.Protocol`) and type the services and `main.py` against them.
   This removes the `# type: ignore[arg-type]` in `tests/test_services.py` and lets
   `_UnavailableFootballClient` implement a real interface. It completes the DIP seam on the client
   side, mirroring what `BaseRepository` already does for storage.
2. **TD-01 — `SQLiteRepository`.** Implement the existing `BaseRepository` contract against
   `sqlite3`. Services must not change — that is the proof the seam was worth it. Reuse the storage
   test suite by parametrizing it over both repository implementations.
3. **TD-02 — money to `Decimal`.** Migrate `CryptoPrice` monetary fields alongside the DB work.
4. **TD-04 — a real USD→Toman rate source** instead of the static fallback.

See [`roadmap.md`](roadmap.md) for the full V2–V6 arc and [`architecture.md`](architecture.md) §8.

---

## 6. Quick-start checklist for the new session

1. Read `architecture.md`, then this file, then `taskbook.md` and `v1-release-note.md`.
2. Confirm a **Python 3.12** environment: `python3.12 -m venv .venv && source .venv/bin/activate`,
   then `pip install -e ".[dev]"`.
3. Run the gates: `ruff check .`, `mypy --strict src`, `pytest` — expect all green (52 tests).
4. Run the app: `crypto-wc` (banner/menu appears; the startup INFO line lands in `data/logs/app.log`,
   not the console). Crypto works with no keys; football needs `FOOTBALL_API_KEY`.
5. Pick up from §5. Branch per issue; commit with Conventional Commits; PR into protected `main`.