# Version 2 — Release & Closeout

**Release:** V2.0.0
**Status:** Complete.

> This document records what was shipped in Version 2. For instructions on resuming or extending the project, see [`architecture.md`](architecture.md) and [`roadmap.md`](roadmap.md).

---

## 1. What was built

Version 2 focused heavily on addressing technical debt from V1 to make the platform more durable, precise, and native to the Iranian market, while maintaining the application's clean architecture.

### Storage Migration: JSON to SQLite
The primary goal of V2 was to replace the simple JSON storage (TD-01) with a robust, relational SQLite database without touching the business logic.
- We evolved the `BaseRepository` interface to support normalized domain querying (`get_price_history`).
- The `SQLiteRepository` now maintains normalized tables (`price_history`, `tournament`, `match`).
- This allows tracking of price history and displaying it via a new "Coin price history" menu option.

### Precision Currency: Decimal Migration
To address TD-02, all monetary values across the application were converted from standard `float`s to Python's `decimal.Decimal`. This ensures no rounding errors or floating-point inaccuracies ever creep into the platform's presentation.

### Native Market Rates: Wallex Integration
We completely eliminated the complex fallback fiat conversion logic (TD-04). By switching the cryptocurrency data provider from CoinGecko to the Iranian **Wallex** exchange, the system now natively fetches both the Tether (USDT) price and the precise Toman (TMN) local market price directly from the live order book in a single request. 

---

## 2. Technical Debt Resolved

- **TD-01 (JSON storage, no concurrency safety):** Resolved. Migrated to SQLite.
- **TD-02 (Money as `float`):** Resolved. Migrated to `Decimal`.
- **TD-04 (Approximate Toman rate):** Resolved. Integrated Wallex API for native Toman pairs.
- **TD-09 / TD-10 (Incomplete Client Interfaces):** Resolved. Extracted proper protocols (`CryptoClientProtocol`, `FootballClientProtocol`) and refactored the composition root to rely on pure interfaces.

---

## 3. The Power of Clean Architecture

The transition to V2 proved the success of the architecture established in V1. 

By defining clear interfaces (`BaseRepository`, `CryptoClientProtocol`), we completely swapped the entire database backend (JSON to SQLite) and the external API provider (CoinGecko to Wallex) **without touching a single line of code in the core business services or the presentation layer**. The dependencies point inward, allowing the infrastructure to evolve safely and independently.
