Status: Current

# Continuous integration

GitHub Actions runs lint, type check, and tests on every pull request and on every push to `main`.

## What CI runs

The workflow is [`.github/workflows/ci.yml`](https://github.com/mkarots/benedict/blob/main/.github/workflows/ci.yml).

| Job | What it runs | Python |
| --- | --- | --- |
| Lint | `ruff check src tests` and `black --check src tests` | 3.12 |
| Type check | `mypy src/benedict` | 3.12 |
| Tests | `pytest` with coverage | 3.10, 3.11, 3.12 |

Local equivalents: `make lint`, `make type-check`, `make test`. After `pre-commit install`, Git hooks in `.pre-commit-config.yaml` run Black, Ruff, trailing-whitespace, and end-of-file-fixer on commit. Those Black and Ruff versions match the `dev` extra. Setup: `CONTRIBUTING.md` at the repository root.

Ruff, Black, and mypy versions are pinned in `pyproject.toml` so CI matches a local `make sync-dev`.

## Non-goals

CI does not publish packages, talk to Slack, or enforce the 80% coverage target.

## Type check scope

`mypy` uses `[tool.mypy]` in `pyproject.toml`. It checks `src/benedict` with reasonable strictness: untyped and incomplete function signatures are errors (`disallow_untyped_defs`, `disallow_incomplete_defs`), untyped bodies are checked, and unused ignores are warned. Third-party imports without stubs are allowed (`ignore_missing_imports`). Site-packages are not checked (`no_site_packages`) because NumPy 2 stubs use 3.12-only syntax.

## How to run the same checks

```bash
make lint
make type-check
make test
```

`make lint` fails if Ruff reports a problem or Black would reformat a file.
