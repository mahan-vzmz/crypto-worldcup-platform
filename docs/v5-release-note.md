# Release Note: V5.0.0 (Dynamic Markets & Web Dashboard)

Version 5 represents a massive leap in capability and user experience. The project has evolved from a CLI-only application with hardcoded assets into a full-fledged web platform tracking global financial markets.

## What Changed?

### 1. Dynamic Asset Domain Refactoring
Previously, the crypto market feature was tightly coupled to a static `Coin` Enum (BTC, ETH, SOL).
- **The Seam:** We removed `Coin` entirely and replaced it with generic `symbol` strings.
- **The Enabler:** Because of the Clean Architecture, this sweeping change was safely implemented. The `SQLiteRepository`, API clients, and the CLI renderers were refactored to support *any* symbol string dynamically.
- **Result:** The system now fetches the entire market of cryptocurrencies automatically.

### 2. Multi-Market Expansion (Fiat & Metals)
- Added `AssetType` (Crypto, Fiat, Metal) to the domain model to classify data.
- Created `FiatClient` to scrape/fetch real-time USD, EUR, and GBP to Toman exchange rates.
- Upgraded the `CryptoService` to orchestrate parallel fetching of Crypto and Fiat markets, calculating Toman prices dynamically based on the live USD rate.

### 3. Multi-League Football
- Extended `FootballClient` and `FootballService` to support arbitrary `competition_code` parameters (e.g., 'WC' for World Cup, 'PL' for Premier League).

### 4. Modern Web Dashboard
We successfully consumed the V4 FastAPI backend using a server-rendered frontend.
- **Jinja2 + HTMX:** The dashboard uses Jinja2 for server-side template rendering and HTMX for seamless background auto-polling. This provides a Single-Page Application (SPA) feel without the complexity of a JavaScript framework.
- **Aesthetic UI:** A custom, dark-themed, glassmorphic CSS stylesheet was written to make the presentation layer look highly premium.

## Why it Matters
This release solidifies the architectural hypothesis: because the Service Layer and Domain Models were perfectly decoupled, we successfully swapped the UI (from CLI to Web) and swapped the scope of the domain (from 3 hardcoded coins to 100+ dynamic assets) without rewriting the core orchestration logic.
