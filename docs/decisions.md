# Architecture Decision Log

> A log of the significant architectural and process decisions made on the Crypto & World Cup
> Information Platform. Each entry records not just *what* was decided but *why*, and what it
> commits the project to. This log complements the ADR section in
> [`architecture.md`](architecture.md); where IDs overlap they describe the same decision.
>
> **Verification note:** Compiled from the established project plan and development record, not a
> live repository audit. All decisions below were agreed and applied during the M0–M1 sessions.
> Dates are given as relative project phase rather than calendar dates, which were not tracked.

---

## ADR-001 — Layered Architecture with One-Directional Dependencies
- **Phase:** Planning (pre-M0).
- **Context:** The project must evolve through six planned versions (JSON → SQLite → PostgreSQL,
  CLI → REST → web) without ground-up rewrites. A naive single-module script would not survive
  that evolution.
- **Alternatives considered:** (a) a flat single-module script; (b) the MVC pattern; (c) a layered
  architecture with dependency inversion.
- **Decision:** Adopt four layers — Presentation, Service, Data, Utility — with dependencies
  flowing strictly downward (Presentation → Service → Data); utilities and config are available to
  all layers, and lower layers never import upper ones.
- **Rationale:** The flat script is fastest to start but collapses under growth; MVC suits
  request-response web frameworks but does not cleanly isolate external data sources; layering with
  inversion pays a one-time indirection cost in exchange for making every future migration a swap
  of implementations rather than a rewrite.
- **Consequences:** More files and more indirection up front. Physical folder separation
  (`clients/`, `services/`, `storage/`) enforces the boundaries so they cannot be blurred without
  an obvious cross-layer import a reviewer will catch. This decision underpins ADR-002 and ADR-003.

## ADR-002 — JSON Storage Behind a Repository Interface
- **Phase:** Planning (pre-M0). **Status:** interface and implementation are **Planned (M3)** — the
  *decision* is fixed; the code is not yet written.
- **Context:** V1 persists to JSON, but V2 targets SQLite and V6 targets PostgreSQL.
- **Alternatives considered:** (a) read/write JSON directly inside services; (b) define an abstract
  `Repository` interface with a JSON implementation behind it.
- **Decision:** All persistence will go through an abstract `Repository` interface; JSON is one
  implementation.
- **Rationale:** Writing JSON directly inside services would weld the storage format into business
  logic, making the V2 migration a rewrite. The interface is the migration seam: V2 adds a
  `SQLiteRepository` implementing the same contract and services do not change.
- **Consequences:** One extra abstraction layer in V1; near-zero migration cost later. JSON-specific
  concerns (atomic writes, datetime serialization, the `{fetched_at, schema_version, data}`
  envelope) are confined to the JSON implementation.

## ADR-003 — Adapter Pattern for External APIs
- **Phase:** Planning (pre-M0). **Status:** clients are **Planned (M4)**.
- **Context:** Third-party APIs change shape and may be replaced; their JSON must not contaminate
  the rest of the app.
- **Alternatives considered:** (a) call APIs and consume their raw JSON throughout the app;
  (b) wrap each API in a client that maps responses into our own models.
- **Decision:** Each client calls one API and maps its response into our domain models; external
  schemas never leak past the client.
- **Rationale:** If service code consumed raw API JSON, an API schema change or provider swap would
  ripple across the codebase. Confining mapping to the client makes such changes touch exactly one
  file.
- **Consequences:** A mapping layer to maintain per provider; isolation of provider risk. Chosen
  providers (CoinGecko, Football-Data.org) are quarantined behind this seam.

## ADR-004 — Rich Terminal CLI as the V1 Presentation Layer
- **Phase:** Planning (pre-M0). **Status:** renderers/menu are **Planned (M6)**; `rich` is already a
  dependency and used for the M0/M1 startup banner.
- **Context:** V1 needs a clean, human-readable interface, and the presentation layer must be
  replaceable by an HTTP API (V4) and a web UI (V5).
- **Alternatives considered:** (a) plain `print` output; (b) the `rich` library for formatted
  tables and panels; (c) a TUI framework such as Textual.
- **Decision:** Use `rich` for formatted output, kept in a thin presentation layer that only calls
  services and renders.
- **Rationale:** Plain `print` produces unreadable tabular data; a full TUI framework is heavier
  than V1 needs and would entangle the UI with application logic. `rich` gives professional output
  with minimal coupling.
- **Consequences:** `rich` is confined to the presentation layer; it is deliberately **not** used
  in logging or other layers, to preserve the UI/utility boundary.

## ADR-005 — `pyproject.toml` as the Single Source of Truth
- **Phase:** M0. **Status:** Implemented.
- **Context:** The project needs reproducible installs, clean imports, separated dev tooling, and
  no proliferation of config files.
- **Alternatives considered:** (a) `requirements.txt` only; (b) `pyproject.toml` with
  optional-dependency groups, `src/` layout, and editable install; (c) a heavier dependency
  manager (e.g. Poetry).
- **Decision:** `pyproject.toml` is canonical: project metadata, runtime dependencies, a `dev`
  optional-dependency group, and tool configuration (Ruff, pytest, mypy) all live there. The
  package uses a `src/` layout and is installed editable.
- **Rationale:** `requirements.txt` carries no metadata, entry points, or tool config; an external
  manager adds tooling overhead unjustified for a learning project. One standard file is the modern
  Python norm and keeps the source of truth singular.
- **Consequences:** A single place to understand and change the project's definition. The `src/`
  layout prevents accidentally importing the un-installed package, forcing the editable install
  that mirrors real distribution.

## ADR-006 — Toolchain: Ruff + pytest + mypy (strict)
- **Phase:** M0. **Status:** Implemented (configured); test suite itself is **Planned (M7)**.
- **Context:** "PEP8-compliant" needed a concrete enforcement mechanism rather than a stated
  aspiration.
- **Alternatives considered:** (a) separate flake8 + black + isort; (b) Ruff as a unified
  linter/formatter; plus pytest for tests and mypy for typing.
- **Decision:** Ruff for linting and formatting, pytest for testing, mypy in strict mode for type
  checking — all configured in `pyproject.toml`.
- **Rationale:** Ruff replaces several tools with one fast tool and removes style ambiguity; strict
  mypy makes the type hints load-bearing rather than decorative.
- **Consequences:** A clear, fast pre-merge quality gate (`ruff check`, `ruff format`, `mypy src`,
  `pytest`). Strict typing requires full annotations throughout.

## ADR-007 — Git Workflow: Feature-Branch-Per-Issue via Protected `main`
- **Phase:** M0. **Status:** Implemented.
- **Context:** Even as a solo learner, the project should practice professional version-control
  discipline and keep `main` always working.
- **Alternatives considered:** (a) commit directly to `main`; (b) a long-lived `develop` branch
  plus feature branches (Git Flow); (c) short-lived feature branches merged into a protected `main`
  via PR (trunk-based-ish).
- **Decision:** One short-lived feature branch per issue (`phase-N/<short-desc>`), merged into a
  protected `main` only via pull request, using Conventional Commits.
- **Rationale:** Direct commits to `main` lose the self-review discipline; full Git Flow is
  overhead unnecessary at this scale. The PR — even when solo — is where the code review checklist
  is applied. Conventional Commits teach disciplined history and enable future changelog automation.
- **Consequences:** Every change is reviewable and revertible; `main` stays deployable. Branch
  protection enforces the rule mechanically rather than by habit.

## ADR-008 — Package Structure: `src/` Layout Mirroring the Layers
- **Phase:** M0. **Status:** Implemented.
- **Context:** The folder structure should physically express the architecture and prevent import
  mistakes.
- **Alternatives considered:** (a) a flat package at the repo root; (b) a `src/app/` package with
  sub-packages per layer (`config`, `models`, `services`, `clients`, `storage`, `presentation`,
  `utils`).
- **Decision:** Use `src/app/` with one sub-package per architectural concern, a `tests/` tree
  mirroring it, and a `data/` tree whose folders are tracked via `.gitkeep` while contents are
  gitignored.
- **Rationale:** A root-level flat package can be imported without installation, masking packaging
  problems. The per-layer sub-package split makes a layering violation visible as an obvious import.
- **Consequences:** Cross-layer dependencies are self-evident in import statements; the structure
  doubles as architectural documentation.

## ADR-009 — Error Handling: Custom Exception Hierarchy with Boundary Translation
- **Phase:** M1. **Status:** Implemented (`utils/exceptions.py`).
- **Context:** Library exceptions (`requests`, `json`, `OSError`) must not propagate across layers,
  or the service/presentation layers would become coupled to lower-level implementation details.
- **Alternatives considered:** (a) raise and catch built-in/library exceptions directly; (b) a flat
  set of unrelated custom exceptions; (c) a hierarchy rooted at a single application base class.
- **Decision:** Define `AppError` as the base for all deliberately-raised application errors, with
  `ConfigError`, `StorageError`, and `APIError` subclasses. Each layer translates foreign
  exceptions into the appropriate type at its boundary.
- **Rationale:** Catching library exceptions in the service layer leaks the implementation (e.g.
  that a client uses `requests`), defeating the adapter pattern. A hierarchy lets callers choose
  precision — catch one specific type, a family, or all application errors via `AppError` — while a
  single base lets the top level handle anticipated failures and let genuine bugs surface loudly.
- **Consequences:** A consistent error vocabulary across the app. Exception chaining (`from exc`)
  preserves root causes for debugging. Subclasses are intentionally minimal (docstring-only, no
  custom fields) until a caller needs more — extension is deferred, not pre-built.

## ADR-010 — Logging: Centralized, Configured Once, Dual-Handler
- **Phase:** M1. **Status:** Implemented (`utils/logger.py`).
- **Context:** The app needs a complete diagnostic trail without polluting the CLI, and logging
  must be configured consistently rather than ad hoc per module.
- **Alternatives considered:** (a) `print` statements; (b) `logging.basicConfig` scattered per
  module; (c) a single `setup_logging` configuring the root logger once, with module-level
  `getLogger(__name__)` everywhere.
- **Decision:** Configure the root logger exactly once at startup via `setup_logging`, attaching a
  rotating file handler (`data/logs/app.log`, DEBUG and up) and a console handler (WARNING and up).
  Modules obtain loggers via a `get_logger` helper. Setup is idempotent (`handlers.clear()` first).
- **Rationale:** `print` cannot do levels, routing, or rotation; per-module `basicConfig` produces
  duplicated handlers and inconsistent formats. Configuring the permissive root once and letting
  the two handlers filter per destination gives a full file trail and a clean console
  simultaneously. The idempotency guard prevents the classic duplicate-log-line bug.
- **Consequences:** Routine INFO/DEBUG lands in the file but not on screen — verified behavior.
  Logging calls use lazy `%`-style formatting, never f-strings. Secrets are never logged (policy
  stated in the module docstring). The log directory parameter will be supplied by `Settings`.

## ADR-011 — Configuration: Centralized, Immutable, Environment-Sourced
- **Phase:** M1. **Status:** Implemented (`config/settings.py`).
- **Context:** Configuration spans secrets (API keys), environment-specific values (data directory),
  and tunable non-secret defaults (cache TTL); it must be loaded and validated in one place.
- **Alternatives considered:** (a) hardcoded constants; (b) scattered `os.getenv` calls throughout
  the code; (c) a single immutable settings object built once at startup from the environment.
- **Decision:** A `frozen` `Settings` dataclass built by a `from_env` classmethod that loads `.env`,
  applies defaults, validates, and translates malformed values into `ConfigError`. Subdirectory
  paths are `@property` values derived from a single `data_dir`. `ensure_directories` creates
  runtime folders idempotently.
- **Rationale:** Hardcoding leaks secrets and resists per-environment change; scattered `getenv`
  calls make it impossible to answer "what configuration is this run using?" from one place and
  complicate testing. One immutable, injected object is inspectable and testable, and freezing it
  prevents accidental mutation of shared config. Deriving subpaths from `data_dir` keeps a single
  source of truth for the data layout.
- **Consequences:** Nothing except `settings.py` reads the environment. API keys default to empty
  and are validated at point of use (in the M4 clients), so the app is runnable through M1–M3
  without keys. This decision also implements the runtime-directory creation rule (see ADR-012).

## ADR-012 — Runtime Directories Are Created, Never Assumed
- **Phase:** Planning correction (caught in the M0 audit); **Status:** Implemented in M1 via
  `Settings.ensure_directories`.
- **Context:** `data/` contents are gitignored and Git does not track empty directories, so a fresh
  clone lacks `data/cache`, `data/logs`, etc. Code that assumed those directories existed would
  crash on first write after a clone.
- **Alternatives considered:** (a) commit placeholder files into every runtime directory; (b)
  require manual `mkdir` during setup; (c) have the application create required directories at
  startup, idempotently.
- **Decision:** Track the folder skeleton with `.gitkeep` files, gitignore the contents, and have
  the application create all required directories at startup via `mkdir(parents=True,
  exist_ok=True)`.
- **Rationale:** Committing data placeholders pollutes the repo; manual setup steps are forgotten
  and break onboarding. Self-creating directories make the app work on a clean checkout with no
  manual intervention.
- **Consequences:** Verified by deleting the runtime folders and re-running — the app recreates them
  and starts cleanly. The logger also creates its directory (belt-and-suspenders), but `Settings`
  owns the canonical, centralized creation step.

## ADR-013 — Monetary Values as `float` in V1
- **Phase:** Planning; **Status:** decision fixed, applies to model code that is **Planned (M2)**.
- **Context:** Prices are displayed, not used in user-facing arithmetic, in V1.
- **Alternatives considered:** (a) `float`; (b) `Decimal`.
- **Decision:** Use `float` for monetary values in V1, recorded as deliberate technical debt
  (TD-02), to be revisited with the V2 database migration.
- **Rationale:** `Decimal` is correct for money that participates in arithmetic, but adds ceremony
  V1 does not need for display-only values. Recording the choice as debt keeps it honest rather
  than accidental.
- **Consequences:** Possible floating-point rounding if values ever drive calculations; acceptable
  for display. Slated for change in V2.

## ADR-014 — Future Scalability Strategy: Stable Seams, Deferred Implementation
- **Phase:** Planning (cross-cutting). **Status:** ongoing principle.
- **Context:** The project must be ready for major future change (databases, web API, async, auth)
  without over-engineering V1.
- **Alternatives considered:** (a) build V1 narrowly with no thought to the future; (b) build
  forward-looking infrastructure now; (c) establish abstraction *seams* in V1 but implement only
  what V1 needs behind them.
- **Decision:** Establish the key seams in V1 — the repository interface, the adapter clients,
  constructor-based dependency injection — but implement only V1 behavior behind them. Defer all
  future infrastructure to the version that needs it, tracking each as registered debt.
- **Rationale:** Building narrowly forces rewrites; building future infrastructure now is the scope
  creep the project explicitly guards against. Seams give cheap future change without present
  over-build. The litmus test for each V1 decision is "does this make the next version harder?"
- **Consequences:** V1 carries some extra abstraction it does not strictly need for itself, justified
  by the planned roadmap. Each deferral is recorded in the technical debt register with a target
  version.

## ADR-015 — V2 Storage: SQLite with a Normalized Schema and a Domain Repository
- **Phase:** V2. **Status:** Implemented (`storage/sqlite_repository.py`).
- **Context:** V2 adds a price-history / query capability. V1's repository was a generic
  key→dict cache (one JSON file per key), which cannot answer "give me BTC's last N prices."
- **Alternatives considered:** (a) keep the key→dict interface and store a JSON blob in one
  SQLite column (a true drop-in swap, but SQLite as a dumb blob store — no queryable history);
  (b) a normalized schema (`price_history`, `tournament`, `match`) behind a domain-specific
  repository interface.
- **Decision:** (b). `BaseRepository` evolved from key→dict into domain methods (`save_prices` /
  `load_latest_prices` / `get_price_history` / `save_tournament` / `load_latest_tournament`),
  returning a generic `Cached[T]` envelope. JSON is retired; `SQLiteRepository` (stdlib `sqlite3`)
  is the sole implementation. Prices are append-only (enabling history); the tournament is
  snapshot-only.
- **Rationale:** A flat key-value cache cannot express history or queries, which is the whole
  point of V2. Evolving the interface is justified by a genuine new capability, not rework for its
  own sake. This consciously trades V1's "swap, not rewrite" promise (ADR-002) for real query
  power — the trade-off was made explicitly, not by accident.
- **Consequences:** Services no longer (de)serialize — the repository owns model↔row mapping, so
  the service layer shrank to pure orchestration. The DIP seam still holds: the in-memory test fake
  and `SQLiteRepository` both implement the same ABC. `float`→`Decimal` (TD-02 / ADR-013) remains a
  follow-up within V2. (Corresponds to ADR-011 in `architecture.md`.)