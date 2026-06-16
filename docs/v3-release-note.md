# Version 3 — Release & Closeout

**Release:** V3.0.0
**Status:** Complete.

> This document records what was shipped in Version 3. For instructions on resuming or extending the project, see [`architecture.md`](architecture.md) and [`roadmap.md`](roadmap.md).

---

## 1. What was built

Version 3 focused entirely on **OOP Refactoring and cleaner internals**. There are no major user-facing changes; rather, the focus was on improving the application's design patterns, error handling, and component decoupling.

### Richer Result Types (`Ok` / `Err`)
We replaced the pattern of raising bare `APIError` exceptions inside the services when offline with a more robust, functional `Result` type.
- Created a generic `Result[T, E]` type consisting of `Ok` and `Err` using Python 3.12 syntax.
- `CryptoService` and `FootballService` now return explicitly typed `Result` objects, forcing the caller (`Menu`) to explicitly handle the `Ok` and `Err` paths.
- **ADR-012** details this decision to shift from typical Exception raising to explicit type-level error handling.

### Dependency Injection Container
To resolve TD-03, we introduced a centralized IoC Container (`src/app/config/container.py`).
- Extracted all the manual wiring, repository initialization, and fallback logic from `main.py`.
- `main.py` is now solely responsible for fetching settings, creating the `Container`, and passing the resolved services to the `Menu`.

### Cache Strategy Object
To resolve TD-07, the simple standalone `is_fresh` helper was replaced with a `CacheStrategyProtocol`.
- Implemented `TTLCacheStrategy` which conforms to the protocol.
- The cache strategy is now injected into the services by the `Container`, decoupling the caching rules from the orchestration logic.

---

## 2. Technical Debt Resolved

- **TD-03 (Manual dependency wiring):** Resolved. Moved wiring to `Container`.
- **TD-07 (TTL cache as a simple function):** Resolved. Promoted to `CacheStrategyProtocol`.

---

## 3. The Power of Clean Architecture

Version 3 reinforces the core value of our layered architecture. By keeping the Presentation layer independent from the Service logic, we were able to overhaul the way errors are returned (Result types) and services are instantiated (DI Container) without having to rewrite any underlying API clients or repository implementations.
