# Version 1 — Release & Closeout

**Release:** V1.0.0
**Status:** Complete. All milestones M0–M7 merged into a protected `main`.
**Scope:** the frozen V1 scope in [`architecture.md`](architecture.md) §6, delivered in full.

> This document records *what shipped* and *why it works*. For instructions on resuming or
> extending the project, read it alongside [`architecture.md`](architecture.md) (design rationale
> and ADRs) and [`taskbook.md`](taskbook.md) (the completed roadmap). The engineering handoff is
> retained for historical context; this closeout supersedes it as the current state of record.

---

## 1. What was built

A Python 3.12 terminal application delivering live cryptocurrency prices (BTC, ETH, SOL) and
football tournament data through a clean, layered architecture. The user interacts with a `rich`
CLI menu; everything beneath it is separated into presentation, service, and data layers with
strictly one-directional dependencies.

The application is **offline-first**: external calls are cached with a time-to-live, and an
unreachable API degrades to the last good data rather than failing. End-to-end operation —
including the offline-fallback path against a downed network — was verified at release.

---

## 2. The architecture, layer by layer

- **Presentation** (`presentation/`, `main.py`) — `rich` renderers (pure formatting) and an
  interactive menu that dispatches to services and catches `AppError` at the boundary so the user
  never sees a traceback. `main.py` is the composition root: the one place that imports across
  layers, wiring settings → repository → clients → services → menu in dependency order.
- **Service** (`services/`) — orchestration only. Each service implements cache-then-fetch with
  TTL staleness and offline fallback, depending on injected abstractions rather than concrete
  collaborators.
- **Data** (`clients/`, `storage/`) — external access (API adapters) and internal persistence
  (atomic JSON repository), each hidden behind its own abstraction.
- **Utilities & Config** (`utils/`, `config/`) — logging, the custom exception hierarchy, and the
  frozen settings loader, available to every layer.

---

## 3. Two ideas that carried the design

### The Anti-Corruption Layer (the client mapping step)
External APIs speak their own dialect — CoinGecko's `usd_24h_change`, Football-Data.org's
`IN_PLAY` status and nested `score.fullTime.home`. None of that vocabulary is allowed past the
client layer. Each client translates raw JSON into typed domain models (`CryptoPrice`,
`Tournament`) before returning, so every layer above sees clean, validated objects and is immune
to a provider renaming a field. When a provider changes, exactly one file changes. This is what
makes the planned provider swaps a contained edit rather than a ripple through the codebase.

### Cache-then-Fetch orchestration (the service decision tree)
Every service request follows one policy: serve fresh cache without a network call; on stale or
absent cache, fetch and persist; if the fetch fails, serve stale cache with a warning; only when
the API is down *and* no cache exists at all does an `APIError` reach the user as a clear message.
The single principle is **stale data beats no data, but a crash is reserved for genuine
nothing-to-serve**. Deserialization from cache re-runs the models' validation, so a corrupted
cache entry cannot silently re-enter the domain. This policy was proven live: with the network
disabled, the app served cached prices and logged the fallback exactly as designed.

---

## 4. Quality at release

- **Tests:** 52 passing in V1 (currently 49 in V2 after retiring fiat client). Domain-model invariants; the JSON repository against a real temporary
  directory (round-trip, corruption, future-schema, idempotent delete, unsafe-key rejection); and
  all four service orchestration branches via in-memory fakes. No test touches a live API or the
  real filesystem outside its fixture — the repository ABC is what makes those fakes trivial.
- **Typing:** `mypy --strict` passing.
- **Lint/format:** `ruff` clean.
- **Definition of Done:** every clause in `architecture.md` §7 met and verified.

---

## 5. Carried debt — the V2 starting line

V1 ships with ten recorded debts (full register in `architecture.md` §8). The ones most relevant
to a V2 effort, roughly in the order a V2 would address them:

1. **TD-01 — JSON has no concurrency safety.** The single largest V1→V2 driver. Resolution is the
   headline V2 move: a `SQLiteRepository` implementing the *same* `BaseRepository` contract, with
   zero changes to services. This is the migration the whole architecture was built to make cheap.
2. **TD-09 / TD-10 — the client-side DIP seam is incomplete.** Services depend on concrete client
   classes, and `main.py` carries an ad-hoc unavailable-client stand-in. Extracting
   `CryptoClientProtocol` / `FootballClientProtocol` removes a test `type: ignore` and lets the
   stand-in implement a real interface. A small, high-value early-V2 refactor. 
3. **TD-02 — money as `float`.** Migrate to `Decimal` alongside the database work, where values
   may start driving arithmetic.
4. **TD-04 — approximate Toman rate.** Adopt a proper rate source.
5. **TD-07 — coarse TTL caching.** Extract a cache-strategy object if richer invalidation is
   warranted (V3).
6. **TD-08 — synchronous HTTP.** Move to async at the `base_client` seam when concurrency matters
   (V6).
7. **TD-03 — manual wiring** and **TD-05 — no CI** remain low-priority, deferred to V3 and V6
   respectively per the roadmap.

The through-line holds: because V1 separated presentation, service, and data behind interfaces,
each future version replaces or adds **one** layer without rewriting the others. V2 is a storage
swap, not a rebuild — and that was the entire point.

---

## 6. Acknowledgements

Built issue-by-issue with a deliberate concept → plan → code → review loop, every compromise
recorded rather than hidden. The result is a small system whose design decisions are all
traceable — which is the actual deliverable of a portfolio project.