# Release Note: V9 — Swapwallet-style Coin List & Group-Ready Bot

## Overview
V9 turns MarketPulse into a genuine CoinMarketCap/swapwallet-style experience and makes the
Telegram bot useful in groups. It adds a global market-data source, a richer coin list, a per-coin
detail page, Persian asset names, and group-aware bot behavior — all while preserving the
offline-first guarantees.

## Features Added & Architectural Changes

### 1. Global coin list (CoinGecko)
- Added `CoinGeckoClient` behind a new `MarketDataClientProtocol`: logos, market cap, 24h volume,
  market-cap rank, and a 7-day sparkline in a single request (ADR-015 / ADR-018).
- `CryptoService` now sources the crypto list from CoinGecko and enriches each coin with a Toman
  price from Wallex (direct TMN pair, else USDT-rate conversion) and the Wallex Persian name.
- `CryptoPrice` and the storage layer gained `market_cap`, `volume_24h`, `rank`, `image_url`, and
  `sparkline`, persisted for offline rendering.
- Graceful degradation: CoinGecko down → Wallex crypto entries; all sources down → stale cache.

### 2. Web: redesigned list + coin detail page
- Coin list: rank column, sortable headers, compact market cap/volume, inline-SVG 7-day sparklines,
  search/tabs, responsive column hiding.
- New `/coin/{symbol}` page: header card, market-cap/volume/rank stats, an interactive TradingView
  chart for crypto (sparkline fallback otherwise), and recent observations from stored history.
- Asset names link to their detail page.

### 3. Telegram bot optimized for groups
- Free-text price answers via @mention, reply-to-bot, or any private message; silent on unrelated
  group chatter (ADR-016 / ADR-019).
- Auto-greeting on join (`ChatMemberHandler`), context-aware `/help`, `/p` alias, and a registered
  command menu (`set_my_commands`).
- Pure, unit-tested `bot/search.py` with Persian aliases and filler-word stripping, shared by the
  inline and in-chat handlers; inline results now show coin-logo thumbnails.
- New `docs/telegram-bot.md` covering BotFather setup, privacy mode, and group usage.

## Testing
- Added tests for the CoinGecko client, the source-merge logic (incl. Persian-name override), the
  new model fields, the bot search helpers, and the web dashboard/detail routes.
- **Result: 62 tests, 62 passed.** `ruff`, `ruff format --check`, and `mypy --strict` clean.

## Notes
- Live data requires network egress to `api.coingecko.com`, `api.wallex.ir`,
  `api.exchangerate-api.com`, and `query1.finance.yahoo.com` (see README).
