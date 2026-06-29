# Engineering Handoff

> **Purpose.** This document is the bridge between development sessions. A fresh
> session (with no prior conversation context) should be able to read this and
> resume work immediately and correctly. Read it together with
> [`architecture.md`](architecture.md) (design rationale, ADRs, technical-debt
> register), [`decisions.md`](decisions.md) (the full ADR log), and
> [`roadmap.md`](roadmap.md) (the strategic version history and what's next).

**Last updated:** v9 — swapwallet-style coin list, group-ready Telegram bot,
Persian names, and a coin detail page.
**Active branch:** `feature/swapwallet-coin-list`.

---

## 1. Project in one paragraph

**MarketPulse** is a Python 3.12+, fully-async platform that serves live market
prices — crypto, fiat, precious metals, and global stocks — through three
channels that share one core: a **web dashboard** (FastAPI + Jinja2 + HTMX), a
**Telegram bot** (python-telegram-bot), and an interactive **CLI** (`rich`).
Dependencies flow one direction only: presentation → service → data, with utils
and config available to all layers. External APIs sit behind adapter clients
(an anti-corruption layer); persistence is SQLAlchemy 2.0 (async) behind a
repository interface. Everything is offline-first: every external call is cached
with a TTL, and a downed API serves the last good cache instead of crashing.

---

## 2. Current status — what is built and verified

| Area | State |
| --- | --- |
| Web dashboard | ✅ swapwallet-style coin list: logos, market cap, volume, rank, sortable columns, 7-day sparklines, search/tabs, 30s HTMX polling |
| Coin detail page | ✅ `/coin/{symbol}` — stats, TradingView chart (crypto) / sparkline fallback, stored history |
| Telegram bot | ✅ `/market`, `/price` (+ `/p`), `/watchlist`, inline query, daily brief; **group-ready**: mention/reply/free-text answers, join-greeting, command menu |
| Data sources | ✅ CoinGecko (global crypto), Wallex (Toman + metals + Persian names), ExchangeRate (EUR/GBP), Yahoo (stocks/indices) |
| Storage | ✅ SQLAlchemy async (SQLite dev / PostgreSQL prod), TTL cache + offline fallback, price history |
| Quality gates | ✅ `ruff check` + `ruff format --check` + `mypy --strict src` + `pytest` — **62 tests green** |

### Data-source merge (the heart of the service)
`CryptoService.get_prices()` builds the crypto list from **CoinGecko** (rich
data) and enriches each coin with a **Toman price from Wallex** (direct TMN pair,
else converted via the USDT/Toman rate) and the **Persian name** from Wallex when
available. Metals/fiat/bourse are appended separately. If CoinGecko is down it
falls back to Wallex's own crypto entries; if every source fails it serves stale
cache, and only errors when there is no cache at all.

---

## 3. How to run and test

A Python **3.12** interpreter is required (the package refuses to install on
3.11). See the README "اجرا و تست" section for the full walkthrough. Quick form:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Quality gates (must all pass before a PR)
ruff check . && ruff format --check . && mypy --strict src && pytest

# Run a channel
crypto-wc-api    # web dashboard at http://127.0.0.1:8000
crypto-wc-bot    # Telegram bot (needs TELEGRAM_BOT_TOKEN)
crypto-wc        # interactive CLI
```

**Live data needs network egress** to `api.coingecko.com`, `api.wallex.ir`,
`api.exchangerate-api.com`, and `query1.finance.yahoo.com`. Without it the app
does not crash — it serves cache, or shows an empty state on a cold cache. In a
Claude Code web session, set the environment's Network access to **Custom** and
add those domains (see README).

---

## 4. Conventions to preserve

- **Layering:** presentation → service → data; never import upward. Clients raise
  `APIError`, storage raises `StorageError`, config raises `ConfigError` — foreign
  exceptions are translated at the boundary with `from exc`.
- **Money is `Decimal`**; `last_updated` is timezone-aware UTC.
- **Domain purity:** `CryptoPrice` is a frozen, slotted dataclass with
  construction-time validation; bot search logic lives in pure, tested helpers
  (`app/bot/search.py`).
- **Config:** only `settings.py` reads the environment; inject `Settings`.
- **Quality gates green** before every PR (ruff, ruff format, mypy --strict,
  pytest), on Python 3.12.
- **Git:** feature branch + Conventional Commits + PR.

---

## 5. Where to pick up next

- **Item 4 (deferred):** wire the dashboard "خرید/فروش" buttons to a real action
  (currently a placeholder `alert`).
- **Persian names on the web** currently rely on the coin existing on Wallex;
  consider a small static alias map for popular coins not listed there.
- **Price alerts / portfolio** (roadmap v10): per-user threshold subscriptions
  pushed via the bot; a user model already exists for the watchlist.

---

## 6. Quick-start checklist for a new session

1. Read `architecture.md`, then this file, then `roadmap.md`.
2. Create a **Python 3.12** venv and `pip install -e ".[dev]"`.
3. Run the gates — expect **62 tests** green.
4. Launch a channel (`crypto-wc-api` / `crypto-wc-bot` / `crypto-wc`).
5. Work on `feature/swapwallet-coin-list`; Conventional Commits; PR.
