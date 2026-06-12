# Contributing and Workflow Guidelines

## Branching Strategy
- `main` must always be stable and deployable.
- Features are developed in short-lived feature branches (`feat/` or `phase-N/`).
- Merge into `main` only via Pull Requests.

## Commit Message Convention
We follow the Conventional Commits specification:
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code (white-space, formatting)
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `chore`: Updating build tasks, package manager configs, etc.