# Task Book & Project Roadmap

> Static project board for the Crypto & World Cup Information Platform. Check items off
> locally as they merge into `main`. The authoritative design rationale lives in
> [`architecture.md`](architecture.md); this file is the execution roadmap.

**Difficulty legend:** ⚪ Trivial · 🟢 Easy · 🟡 Medium · 🔴 Hard

---

## Milestone overview

| Milestone | Theme | Status |
| --- | --- | --- |
| M0 | Bootstrap / Project Scaffolding | ✅ Complete (merged) |
| M1 | Foundations (Config / Logging / Exceptions) | ✅ Complete (merged) |
| M2 | Domain Models | ⬜ Next |
| M3 | Storage Layer | ⬜ Not started |
| M4 | API Clients | ⬜ Not started |
| M5 | Service Layer | ⬜ Not started |
| M6 | Presentation (CLI) | ⬜ Not started |
| M7 | Tests & Documentation | ⬜ Not started |

---

## Milestone M0 — Bootstrap
**Epic:** Project Scaffolding

- [x] **#1 — Create GitHub repository and protect main** — ⚪ · 15 min
  Create the empty remote repo, clone locally, enable branch protection requiring PRs into `main`. *Deps:* none.
- [x] **#2 — Add root documentation files** — 🟢 · 30 min
  `README.md` skeleton, `LICENSE` (MIT), `CONTRIBUTING.md` with workflow and review checklist, `CHANGELOG.md`. *Deps:* #1.
- [x] **#3 — Add `.gitignore` and `.env.example`** — 🟢 · 20 min
  `.gitignore` per requirements; `.env.example` listing required variables with no values. *Deps:* #1.
- [x] **#4 — Create full folder tree with `__init__.py` and `.gitkeep`** — 🟢 · 25 min
  Complete `src/app/...` package tree, `tests/` mirror, `data/` subfolders with `.gitkeep`. *Deps:* #1.
- [x] **#5 — Configure `pyproject.toml`** — 🟡 · 30 min
  Project metadata, runtime deps (`requests`, `rich`, `python-dotenv`), dev deps (`pytest`, `ruff`, `mypy`, `types-requests`), and Ruff/pytest/mypy config. *Deps:* #4.
- [x] **#6 — Set up Python environment and verify editable install** — 🟢 · 20 min
  `.python-version`, `.venv`, `pip install -e ".[dev]"`, confirm the package imports. *Deps:* #5.
- [x] **#7 — Add minimal runnable entry point** — 🟢 · 20 min
  `main.py` that prints a banner and exits cleanly, proving the package runs. *Deps:* #6.
- [x] **#8 — Commit approved architecture doc** — ⚪ · 10 min
  Add the approved architecture document to `docs/architecture.md`. *Deps:* #2.

> **M0 closeout note:** Two follow-up `docs:` PRs closed the audit findings — committing
> the canonical `docs/architecture.md` (finding C-1) and updating the README setup/usage
> section (finding C-2). Branch protection verified. Phase 0 closed with a clean Go.

---

## Milestone M1 — Foundations
**Epic:** Cross-Cutting Foundations

- [x] **#9 — Custom exception hierarchy** (`utils/exceptions.py`) — 🟢 · 25 min
  `AppError` base with `ConfigError`, `StorageError`, `APIError` subclasses. Each layer
  translates foreign exceptions into these at its boundary. *Deps:* M0.
- [x] **#10 — Logging setup** (`utils/logger.py`) — 🟡 · 30 min
  `setup_logging()` configures the root logger once with two handlers — a rotating file
  handler (`data/logs/`, DEBUG+) and a console handler (WARNING+); idempotent via
  `handlers.clear()`. `get_logger()` helper wraps `logging.getLogger`. *Deps:* #9.
- [x] **#11 — Settings loader** (`config/settings.py`) — 🟡 · 30 min
  Frozen `Settings` dataclass; `from_env()` alternative constructor loads `.env`, applies
  defaults, validates and translates bad values to `ConfigError`; subdirectory `@property`
  paths derived from `data_dir`; `ensure_directories()` creates runtime folders idempotently
  (ADR-006). *Deps:* #9.

> **M1 closeout note:** Foundation integration check merged — `main.py` wires settings →
> ensure directories → logging → startup log, with graceful `ConfigError` handling. Dual-handler
> smoke tests passed. Milestone complete.

---

## Milestone M2 — Domain Models
**Epic:** Domain Modeling

- [ ] **#12 — Crypto models** (`models/crypto.py`) — 🟢 · 25 min
  `Coin`/`CryptoPrice` dataclasses + a coin enum. Fields: symbol, name, `price_usd`,
  `price_toman`, `change_24h`, `last_updated`. Money as `float` (ADR-009). *Deps:* M0.
- [ ] **#13 — Football models** (`models/football.py`) — 🟡 · 30 min
  `Team`, `Match`, `Tournament` dataclasses + `MatchStatus` enum
  (SCHEDULED / LIVE / FINISHED). Optional scores, kickoff datetime, tournament progress. *Deps:* M0.

---

## Milestone M3 — Storage Layer
**Epic:** Persistence

- [ ] **#14 — Repository interface** (`storage/base_repository.py`) — 🟡 · 25 min
  Abstract `Repository` with `save` / `load` / `exists`. The migration seam (ADR-002). *Deps:* #9.
- [ ] **#15 — JSON repository** (`storage/json_repository.py`) — 🔴 · 45 min
  Atomic writes (temp file + rename), datetime serialization, the `{fetched_at, schema_version,
  data}` envelope. Translates `OSError` / `json` errors to `StorageError`. *Deps:* #14, #11.

---

## Milestone M4 — API Clients
**Epic:** External Integrations

- [ ] **#16 — Base HTTP client** (`clients/base_client.py`) — 🔴 · 45 min
  Shared `requests.Session`, timeout, retry/backoff, status→exception mapping to `APIError`. *Deps:* #9, #10.
- [ ] **#17 — Crypto client** (`clients/crypto_client.py`) — 🔴 · 45 min
  Call CoinGecko (ADR-003), map response to `CryptoPrice`, USD→Toman conversion (ADR-005),
  validate API key at point of use. *Deps:* #16, #12.
- [ ] **#18 — Football client** (`clients/football_client.py`) — 🔴 · 45 min
  Call Football-Data.org (ADR-004), map to football models, validate API key at point of use. *Deps:* #16, #13.

> **M4 open items to resolve at the start of this milestone:** verify CoinGecko free-tier
> terms/endpoint (ADR-003); select the football competition the free tier serves (ADR-004);
> source the USD→Toman rate, or fall back to a configurable approximate rate (ADR-005).

---

## Milestone M5 — Service Layer
**Epic:** Orchestration

- [ ] **#19 — Crypto service** (`services/crypto_service.py`) — 🟡 · 35 min
  Cache-then-fetch with TTL staleness (ADR-006); client + repository injected via constructor;
  offline fallback to cache. *Deps:* #15, #17.
- [ ] **#20 — Football service** (`services/football_service.py`) — 🟡 · 35 min
  Same orchestration pattern for football. *Deps:* #15, #18.

---

## Milestone M6 — Presentation (CLI)
**Epic:** User Interface

- [ ] **#21 — Renderers** (`presentation/renderers.py`) — 🟡 · 40 min
  `rich` tables/panels for coins and matches. Pure formatting, no logic. *Deps:* #12, #13.
- [ ] **#22 — Interactive menu** (`presentation/menu.py`) — 🟡 · 40 min
  Input loop dispatching to services. Thin UI — no business logic. *Deps:* #19, #20, #21.
- [ ] **#23 — Wire dependencies in `main.py`** — 🟡 · 30 min
  Construct and inject all dependencies, launch the menu. Grows the composition root (TD-03). *Deps:* #22, #11, #10.

---

## Milestone M7 — Tests & Documentation
**Epic:** Quality & Documentation

- [ ] **#24 — Model tests** — 🟢 · 30 min
  Field defaults, construction, equality for crypto + football models. *Deps:* #12, #13.
- [ ] **#25 — Storage tests** — 🟡 · 40 min
  Roundtrip save/load using a temp-directory fixture; corrupted-file and missing-file edge cases. *Deps:* #15.
- [ ] **#26 — Service tests** — 🔴 · 45 min
  Inject fake client + fake repository to test caching logic in isolation (fresh / stale / offline). *Deps:* #19, #20.
- [ ] **#27 — Finalize README and architecture docs** — 🟢 · 30 min
  Update README to full V1 usage; reconcile any ADRs changed during implementation; release CHANGELOG. *Deps:* all.

---

## Definition of Done (V1 summary)

Full criteria in [`architecture.md`](architecture.md) §7. In brief: every menu path works;
crypto shows USD/Toman/24h/timestamp for BTC/ETH/SOL; cache serves-fresh / refetches-stale /
falls-back-offline without crashing; fresh-clone editable install runs; no secret in history;
Ruff + mypy strict + pytest all green; docs committed; every issue closed via PR into protected `main`.