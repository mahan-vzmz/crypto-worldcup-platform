# Release Note: V8 — MarketPulse Transformation

## Overview
V8 pivots the project from the "crypto + football" learning application into **MarketPulse**, a
focused, multi-market price platform inspired by swapwallet.app. It is a cleanup-and-refocus
release: the football/World-Cup domain and an unreliable data source are removed, and the brand,
docs, and models are aligned with the new direction.

## Changes

### Phase 1 — Codebase cleanup
- Fixed a broken import in `bot/main.py` (missing parenthesis after `InlineQueryHandler`).
- Added the `image_url` field to `CryptoPrice` to match template usage.
- Renamed the FastAPI app title to "MarketPulse API".
- Purged stale football/World-Cup references from settings and docs.

### Phase 2 — Iran Bourse dropped
- Removed `IranBourseClient`, `IranBourseClientProtocol`, and the `IRAN_BOURSE` asset type — the
  TSETMC API returned empty data in testing.
- Cleaned all references from `CryptoService`, the DI container, templates, and tests.

## Testing
- Test suite updated and de-footballed. **Result: 35 tests, 35 passed.**

## Result
A clean, crypto/fiat/metals/stocks platform with web, bot, and CLI channels — the foundation the
V9 swapwallet-style coin list builds on.
