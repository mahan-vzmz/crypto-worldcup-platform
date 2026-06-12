# Engineering Handoff

> **Purpose.** This document is the bridge between development sessions. It is written so a
> fresh session (with no prior conversation context) can resume work immediately and correctly.
> Read this together with [`architecture.md`](architecture.md) (design rationale, ADRs, frozen
> scope, Definition of Done) and [`taskbook.md`](taskbook.md) (the issue-by-issue roadmap).

**Last updated:** end of Milestone M1 (Foundations).
**Branch state:** all work below is merged into a protected `main`.

---

## 1. Project in one paragraph

A Python 3.12+ terminal application that displays cryptocurrency prices (BTC, ETH, SOL) and
football tournament data, built as a portfolio-grade demonstration of clean, layered architecture.
Dependencies flow one direction only: Presentation → Service → Data, with Utilities and Config
available to all layers. Persistence is JSON behind a repository interface (the seam for a future
SQLite/PostgreSQL migration). External APIs sit behind adapter clients. The project is built
issue by issue, each on its own feature branch, merged via PR into a protected `main` using
Conventional Commits. The mentoring style is deliberate: concept → plan → code → review for every
piece, readability over cleverness, and every compromise recorded as tracked debt.

---

## 2. Current project status — what is built, integrated, and verified

### Phase 0 — Scaffolding (Milestone M0) ✅
- Repository created; `main` branch protection enabled; PR-per-issue workflow established.
- `.gitignore`, `.env.example`, `LICENSE` (MIT), `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md` committed.
- Full `src/app/...` package tree with `__init__.py` files; `tests/` mirror; `data/{cache,settings,history,logs}/`
  folders tracked via `.gitkeep` (contents gitignored).
- `pyproject.toml` is the canonical config: `src/` layout, runtime deps (`requests`, `rich`,
  `python-dotenv`), dev extras (`pytest`, `ruff`, `mypy`, `types-requests`), and Ruff/pytest/mypy
  configuration. Editable install (`pip install -e ".[dev]"`) verified.
- `crypto-wc` console entry point works.
- Post-audit closeout: `docs/architecture.md` committed (audit finding C-1); README setup/usage
  updated (finding C-2). Phase 0 closed with a clean Go.

### Phase 1 — Foundations (Milestone M1) ✅

**Issue #9 — `src/app/utils/exceptions.py` (custom exception hierarchy).**
`AppError` is the base for every deliberately-raised application error. Subclasses: `ConfigError`,
`StorageError`, `APIError`. The governing rule: each layer translates foreign exceptions (e.g.
`requests`, `json`, `OSError`) into one of these at its boundary, so lower-level libraries never
leak upward. Classes are docstring-only (no custom fields yet — deferred until a caller needs them).
*Verified:* Liskov substitution confirmed in REPL — a subclass instance is caught by `except AppError`.

**Issue #10 — `src/app/utils/logger.py` (centralized logging).**
`setup_logging(log_dir, *, console_level=WARNING, file_level=DEBUG)` configures the **root** logger
**once**. Root level is `DEBUG` (permissive gate); the two handlers do the filtering:
- Rotating file handler → `<log_dir>/app.log`, DEBUG and up, ~1 MB rollover, 3 backups, verbose format
  (`timestamp | level | logger name | message`).
- Console handler → WARNING and up only, terse format (`level | message`), so routine INFO/DEBUG
  never clutters the CLI.
Idempotent via `root_logger.handlers.clear()` before re-adding (prevents duplicate-line bug on
repeated calls). `get_logger(name)` is a thin wrapper over `logging.getLogger` so the codebase
depends on our `utils`, not `logging` directly. Logging calls must use lazy `%`-style formatting
(`logger.info("x=%s", v)`), never f-strings.

**Issue #11 — `src/app/config/settings.py` (frozen settings loader).**
`Settings` is a `@dataclass(frozen=True)` — immutable after load. `Settings.from_env()` is the
alternative constructor: it calls `load_dotenv()`, reads env vars with defaults, validates, and
translates malformed values into `ConfigError` (with `from exc` chaining). Fields: `data_dir`,
`cache_ttl_seconds`, `crypto_api_key`, `football_api_key`. Subdirectory paths (`cache_dir`,
`settings_dir`, `history_dir`, `logs_dir`) are `@property` methods **derived from `data_dir`** — one
source of truth. `ensure_directories()` creates all runtime folders idempotently
(`mkdir(parents=True, exist_ok=True)`) — this is the concrete implementation of ADR-006 (runtime
directories are created, never assumed, so a fresh clone works).
*Verified:* immutability raises `FrozenInstanceError` on reassignment; a bad `CACHE_TTL_SECONDS`
raises `ConfigError` (not `ValueError`) in REPL.

**Defaults:** `DATA_DIR` → `data`; `CACHE_TTL_SECONDS` → `300`. API keys default to `""` and are
**not** validated at load time — validation is deferred to the point of use in the clients (M4),
so the app is runnable through M1–M3 without keys.

---

## 3. Architecture & verification state

### The `main.py` startup sequence (the composition root)
`src/app/main.py` wires the foundation in a deliberately ordered sequence. Ordering is significant
and is the "anti-fragile" property of startup:

1. **Load settings** — `Settings.from_env()`. If it raises `ConfigError`, print the message to
   **stderr** (logging is not configured yet, so we cannot log it) and `sys.exit(1)`. The handler
   catches **only** `ConfigError` — unexpected exceptions are deliberately left to surface so real
   bugs crash loudly rather than being swallowed.
2. **Ensure directories** — `settings.ensure_directories()`, before logging writes anything.
3. **Configure logging** — `setup_logging(settings.logs_dir)`.
4. **Emit startup log** — `get_logger(__name__).info(...)` with lazy `%`-formatting.
5. Show the `rich` banner ("Foundation initialized successfully!") only after a clean start.

`main.py` is the one place permitted to import across multiple layers — that is correct for a
composition root, not a boundary violation. It will grow as services/clients/menu are added (the
seed of TD-03, manual wiring), which is acceptable until it becomes unwieldy.

### Smoke tests performed and passed
- **Happy path:** `crypto-wc` shows only the `rich` banner on screen; the startup `INFO` line
  appears in `data/logs/app.log` but **not** on the console — proving the dual-handler level routing
  (file = DEBUG+, console = WARNING+) works as designed.
- **Graceful failure:** `CACHE_TTL_SECONDS=abc crypto-wc` prints `Configuration error: ...` to
  stderr, shows no banner, and exits with status `1` (confirmed via `echo $?`). No traceback —
  fails loud but clean.
- **Runtime-directory correction (ADR-006):** deleting `data/{cache,settings,history,logs}` and
  re-running recreates all four folders and runs cleanly — proving the app stands up its own
  runtime structure on a fresh checkout.

---

## 4. Conventions the next session must preserve

- **Mentoring loop:** for each issue — explain the concept and any new Python features, present an
  implementation plan, give the complete file, then review the result against the checklist and note
  any deliberate seams/debt. Readability over cleverness. One question at a time when clarifying.
- **Exception translation at boundaries:** clients raise `APIError`; storage raises `StorageError`;
  config raises `ConfigError`. Never let `requests` / `json` / `OSError` leak upward. Use `from exc`.
- **Logging:** module-level `get_logger(__name__)`; configure only in `main.py`; lazy `%` formatting;
  never log secrets.
- **Config:** nothing reads `os.environ` except `settings.py`. Inject `Settings`; don't reach for globals.
- **Money:** `float` in V1 (ADR-009, debt TD-02). **Coins are exactly BTC, ETH, SOL** — scope is frozen.
- **Workflow:** one feature branch per issue (`phase-N/<short-desc>`), Conventional Commits
  (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`), PR into protected `main`, "Closes #N".
- **Skills/tooling:** before writing files, run Ruff (`ruff check .`, `ruff format .`), `mypy src`,
  and `pytest`. Keep lines ≤ 88. Full type hints; mypy is strict.
- **Scope discipline:** do not add features, dependencies, or abstractions beyond the current issue.
  Build the seam, not the speculative feature. Record any compromise in the debt register.

---

## 5. Precise next steps — where to pick up the knife

**Milestone M2 — Domain Models.** Goal: model the domain as typed dataclasses so every layer above
passes typed objects, not raw dicts. No external calls, no storage — pure data definitions. Both
issues depend only on M0 scaffolding and can be done in either order; recommend #12 first.

### Issue #12 — `src/app/models/crypto.py` (do first) — 🟢 ~25 min
Define the cryptocurrency domain types:
- A coin identifier enum (the three supported coins: BTC, ETH, SOL — frozen scope) carrying symbol
  and full name.
- A `CryptoPrice` dataclass with: `symbol` (str), `name` (str), `price_usd` (float), `price_toman`
  (float), `change_24h` (float, percentage), `last_updated` (datetime).
- Money is `float` per ADR-009. Use type hints throughout. Consider `@dataclass(frozen=True)` for
  immutability consistency with `Settings` — discuss the trade-off in the plan before deciding.

### Issue #13 — `src/app/models/football.py` — 🟡 ~30 min
Define the football domain types:
- `Team` (name; optional code/id).
- `MatchStatus` enum: SCHEDULED / LIVE / FINISHED.
- `Match` (home `Team`, away `Team`, optional `home_score`/`away_score` as `Optional[int]`, kickoff
  `datetime`, `status`).
- `Tournament` (name, `list[Match]`, tournament-progress info such as current stage/round).

**Reminder for M2:** these models become the mapping target for the API clients in M4 and the
serialization payload for the JSON repository in M3, so field names chosen here ripple forward — name
them well. The JSON envelope (`{fetched_at, schema_version, data}`) and datetime serialization are
M3 concerns, not M2; keep these files to pure model definitions.

After M2 merges, proceed to **M3 (Storage Layer): #14 repository interface, then #15 JSON repository.**

---

## 6. Quick-start checklist for the new session

1. Read `docs/architecture.md`, then this file, then `docs/taskbook.md`.
2. Confirm local env: `pip install -e ".[dev]"`, then `crypto-wc` (should show the banner; startup
   line lands in `data/logs/app.log`).
3. Start Issue #12 with the standard loop: concept → plan → code → review.
4. Branch `phase-2/crypto-models`; commit `feat: add cryptocurrency domain models`; PR "Closes #12".