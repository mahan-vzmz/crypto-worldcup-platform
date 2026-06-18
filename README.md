# Crypto & World Cup Information Platform
[![CI](https://github.com/mahan-vzmz/crypto-worldcup-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/mahan-vzmz/crypto-worldcup-platform/actions/workflows/ci.yml)

A Python 3.12+ fully asynchronous platform (API, Bot & CLI) that displays live financial markets
(Cryptocurrency, Fiat, Precious Metals) and multi-league football tournament data, 
built as a portfolio-grade demonstration of clean, layered architecture.

It is **offline-first and anti-fragile**: every external call is cached with a
time-to-live, and when an API is unreachable the app serves the last good data
rather than crashing. The user never sees a raw traceback.

## Why this project exists

This is a learning and portfolio piece, not a product. Its goal is to show
professional Python engineering in practice: Clean Architecture, SOLID (the
Dependency Inversion Principle in particular), strict typing, asynchronous programming,
and tests that isolate business logic from the outside world.

## Features

- **Fully Asynchronous (V7)** — Built with `asyncio`, `httpx`, `asyncpg`, and `FastAPI` for high concurrency and performance.
- **Robust Storage** — Uses **SQLAlchemy ORM** mapped to **PostgreSQL** in production, with fallback to **SQLite** for seamless local development.
- **Dockerized Deployments** — Ships with a complete `docker-compose` setup spinning up the Database, REST API Dashboard, and Telegram Bot securely in isolated containers.
- **Financial Markets** — USD price, computed Toman price, 24-hour change,
  and timestamps dynamically fetched for Crypto, Fiat (EUR, GBP), and Metals.
- **Football Tournaments** — fixtures, results, scores, kickoff times, team names, and
  current tournament stages for major global competitions.
- **TTL caching** — each fetch is cached in the DB with a `fetched_at` timestamp; fresh
  cache is served without a network call, stale cache triggers a refetch.
- **Offline fallback** — if a live API fails, the app serves the most recent
  cached data with a warning instead of erroring out.

## Architecture in one diagram

```
[ Web Dashboard ]  [ Telegram Bot ]  [ CLI ]
         \                |            /
        [ REST API & Async Wrappers ]
                          |
           [ Core Service Layer ]  ----> [ Clients (httpx) ]
                          |
    [ Storage (SQLAlchemy + PostgreSQL/SQLite) ]

   ( Utilities & Configuration available to every layer )
```

Dependencies flow one direction only. Services depend on *interfaces*, not
concrete implementations. The test suite replaces the network and DB with lightweight fakes. External API shapes
are translated into typed domain models inside the client layer (an
anti-corruption layer), so nothing above the clients ever sees raw API JSON.

## Tech stack

| Concern | Choice |
| --- | --- |
| Language | Python 3.12+ |
| Concurrency | `asyncio` |
| HTTP Client | `httpx` (async, session reuse, explicit timeouts) |
| Storage & ORM| `SQLAlchemy 2.0` (async) + `asyncpg` + `aiosqlite` |
| Web API | `fastapi` + `uvicorn` |
| UI/Templates | `jinja2` + `HTMX` + TradingView Widgets |
| Telegram Bot | `python-telegram-bot` (async, job-queue) |
| CLI rendering | `rich` |
| Config | `python-dotenv` + environment variables |
| Container | `Docker` + `Docker Compose` |
| Tests | `pytest` + `pytest-asyncio` |

## Setup (Docker - Recommended for Production)

The easiest way to run the full stack (Database + API + Bot) is using Docker Compose.

```bash
# 1. Clone the project
git clone <your-repo-url>
cd crypto-worldcup-platform

# 2. Create your .env from the template
cp .env.example .env

# 3. Fill in your environment variables (especially TELEGRAM_BOT_TOKEN)
nano .env

# 4. Start the stack in detached mode
docker-compose up -d --build
```
The Web Dashboard will be available at `http://localhost:8000`.

## Setup (Local Development)

Requires Python 3.12 or newer.

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install the package (editable) with dev tooling
pip install -e ".[dev]"

# 3. Create your .env from the template
cp .env.example .env
```

### Environment variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `DATABASE_URL` | no | SQLite | Connection string (e.g., `postgresql+asyncpg://...`) |
| `DATA_DIR` | no | `data` | Root for logs, settings, history |
| `CACHE_TTL_SECONDS` | no | `300` | Freshness window before a refetch |
| `TELEGRAM_BOT_TOKEN` | yes* | — | Required for `crypto-wc-bot` to run |
| `FOOTBALL_API_KEY` | no | — | Football-Data.org key |

> The `.env` file is gitignored. No secret is ever committed or logged.

## Running Locally

Once installed via step 2 above, you can run the following console commands:

```bash
crypto-wc            # Console CLI menu
crypto-wc-api        # FastAPI Web Dashboard (runs on http://127.0.0.1:8000)
crypto-wc-bot        # Telegram Bot Polling (requires TELEGRAM_BOT_TOKEN)
```

## Development & Testing

```bash
ruff check .         # lint
ruff format .        # format
mypy src             # strict type check
pytest               # run the test suite (100% async coverage)
```

The test suite covers the domain models, the SQLAlchemy repository (with a real
temporary-directory SQLite database), and the service orchestration (with fakes). No test touches a live API.

## Project layout

```
src/app/
  main.py            # composition root: wires every layer, starts the CLI
  api/               # FastAPI endpoints & dependencies
  bot/               # Telegram bot handlers & commands
  config/            # settings loader (frozen dataclass, env-driven)
  models/            # typed domain dataclasses (crypto, football)
  services/          # orchestration: cache-then-fetch with offline fallback
  clients/           # async API adapters + base HTTP client
  storage/           # SQLAlchemy repository + SQLite/Postgres support
  presentation/      # rich CLI renderers
tests/               # Pytest suite
data/                # local SQLite DB / logs (gitignored)
```

## License

MIT — see [`LICENSE`](LICENSE).