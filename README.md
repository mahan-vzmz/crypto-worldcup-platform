# Crypto & World Cup Information Platform
[![CI](https://github.com/mahan-vzmz/crypto-worldcup-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/mahan-vzmz/crypto-worldcup-platform/actions/workflows/ci.yml)

A Python 3.12 terminal application that displays live cryptocurrency prices
(BTC, ETH, SOL) and football tournament data, built as a portfolio-grade
demonstration of clean, layered architecture.

It is **offline-first and anti-fragile**: every external call is cached with a
time-to-live, and when an API is unreachable the app serves the last good data
rather than crashing. The user never sees a raw traceback.

## Why this project exists

This is a learning and portfolio piece, not a product. Its goal is to show
professional Python engineering in practice: Clean Architecture, SOLID (the
Dependency Inversion Principle in particular), strict typing, and tests that
isolate business logic from the outside world. Each design decision is recorded
as an Architecture Decision Record in [`docs/architecture.md`](docs/architecture.md).

## Features

- **Cryptocurrency prices** — USD price, computed Toman price, 24-hour change,
  and last-updated timestamp for BTC, ETH, and SOL. View all coins or a single
  coin on demand.
- **World Cup data** — fixtures, results, scores, kickoff times, team names, and
  current tournament stage for one competition.
- **TTL caching** — each fetch is cached with a `fetched_at` timestamp; fresh
  cache is served without a network call, stale cache triggers a refetch.
- **Offline fallback** — if a live API fails, the app serves the most recent
  cached data with a warning instead of erroring out. Only a total failure
  (API down *and* no cache at all) surfaces a clear message.

## Architecture in one diagram

```
[ User ] -> [ Presentation ] -> [ Service ] -> [ Clients (external APIs) ]
                                     |
                               [ Storage (JSON) ]
        ( Utilities & Configuration available to every layer )
```

Dependencies flow one direction only. Services depend on *interfaces*, not
concrete implementations, which is what makes the JSON-to-database migration (a
future version) a swap rather than a rewrite — and what lets the test suite
replace the network and filesystem with lightweight fakes. External API shapes
are translated into typed domain models inside the client layer (an
anti-corruption layer), so nothing above the clients ever sees raw API JSON.

## Tech stack

| Concern | Choice |
| --- | --- |
| Language | Python 3.12+ |
| HTTP | `requests` (session reuse, explicit timeouts, backoff retries) |
| CLI rendering | `rich` |
| Config | `python-dotenv` + environment variables |
| Typing | `mypy --strict` |
| Lint & format | `ruff` |
| Tests | `pytest` |

No dependency is included that the V1 scope does not need.

## Setup

Requires Python 3.12 or newer.

```bash
# 1. Clone and enter the project
git clone <your-repo-url>
cd crypto-worldcup-platform

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install the package (editable) with dev tooling
pip install -e ".[dev]"

# 4. Create your .env from the template
cp .env.example .env
```

### Environment variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `DATA_DIR` | no | `data` | Root for cache, logs, settings, history |
| `CACHE_TTL_SECONDS` | no | `300` | Freshness window before a refetch |
| `USD_TO_TOMAN_RATE` | no | configurable fallback | USD→Toman conversion (see ADR-005 / TD-04) |
| `CRYPTO_API_KEY` | no | — | CoinGecko key (lifts rate limits; not required) |
| `FOOTBALL_API_KEY` | no | — | Football-Data.org key; without it, football features degrade gracefully |

Crypto works with no keys at all. The football feature requires
`FOOTBALL_API_KEY`; if it is absent the app still runs and simply reports the
football section as unavailable.

> The `.env` file is gitignored. No secret is ever committed or logged.

## Running

The `src/` layout means the package must be installed (step 3 above) before it
can run. Use the console entry point or the module form — **not**
`python src/main.py`, which bypasses the installed package and breaks imports:

```bash
crypto-wc            # console entry point (defined in pyproject.toml)
# or
python -m app.main   # equivalent module invocation
```

You will see an interactive menu: all coin prices, a single coin, World Cup
matches, or quit.

## Development

```bash
ruff check .         # lint
ruff format .        # format
mypy src             # strict type check
pytest               # run the suite
```

The test suite covers the domain models, the JSON repository (with a real
temporary-directory fixture), and the service orchestration (with in-memory
fakes for the client and repository). No test touches a live API or the real
filesystem outside its fixture.

## Project layout

```
src/app/
  main.py            # composition root: wires every layer, starts the CLI
  config/            # settings loader (frozen dataclass, env-driven)
  models/            # typed domain dataclasses (crypto, football)
  services/          # orchestration: cache-then-fetch with offline fallback
  clients/           # API adapters (anti-corruption layer) + base HTTP client
  storage/           # repository interface + atomic JSON implementation
  presentation/      # rich renderers + interactive menu (no business logic)
  utils/             # logging, exception hierarchy
tests/               # mirrors the source tree
docs/                # architecture, taskbook, release notes
data/                # runtime cache/logs/settings/history (gitignored)
```

## License

MIT — see [`LICENSE`](LICENSE).