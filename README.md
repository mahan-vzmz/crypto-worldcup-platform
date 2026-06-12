# Crypto & World Cup Information Platform

A Python terminal application delivering real-time cryptocurrency prices (BTC, ETH, SOL) and
football tournament data through a clean, layered architecture.

## Purpose

This project is a portfolio-grade showcase of professional software engineering principles in
Python — Clean Architecture, SOLID (especially Dependency Inversion), separation of concerns,
and test-driven growth. It is built incrementally, milestone by milestone, with every
architectural decision documented in [`docs/architecture.md`](docs/architecture.md).

## Architecture Overview

- **Presentation Layer** — thin CLI interface using `rich`.
- **Service Layer** — business logic, orchestration, and cache-TTL management.
- **Data Layer** — isolated API clients (adapters) and an atomic JSON repository backend.

Dependencies flow in one direction only: Presentation → Service → Data. See the
[architecture document](docs/architecture.md) for the full design, ADRs, scope, and roadmap.

## Project Status

**Phase 0 (scaffolding) is complete.** The package structure, tooling, and entry point are in
place and the application installs and runs. Feature implementation begins at Milestone M1.
The application currently prints a startup banner and exits; data features are not yet built.

## Requirements

- Python 3.12 or newer
- `git`

## Setup

Clone the repository and enter it:

```bash
git clone https://github.com/mahan-vzmz/crypto-worldcup-platform.git
cd crypto-worldcup-platform
```

Create and activate a virtual environment:

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

Install the package in editable mode with development tooling:

```bash
pip install --upgrade pip
pip install -e ".[dev]"
```

Copy the environment template and fill in values as they become required (API keys are
introduced at Milestone M4):

```bash
cp .env.example .env
```

## Usage

Run the application via its console entry point:

```bash
crypto-wc
```

At this stage the command prints a startup banner confirming the environment is set up
correctly. Interactive crypto and football features arrive in later milestones.

## Development

Run the quality gates before opening a pull request:

```bash
ruff check .      # lint
ruff format .     # format
mypy src          # static type checking (strict)
pytest            # tests
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the branch strategy, commit conventions, and the
pre-merge code review checklist. In short: one feature branch per issue, merged into a protected
`main` via pull request, using Conventional Commits.

## License

Released under the MIT License. See [`LICENSE`](LICENSE).