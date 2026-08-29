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

Local equivalents: `make lint`, `make type-check`, `make test`.

## Non-goals

CI does not publish packages, talk to Slack, or enforce the 80% coverage target.

## Type check scope

`mypy` uses `[tool.mypy]` in `pyproject.toml`. A listed set of older modules is ignored so the job can stay green while type hints catch up.

## How to run the same checks

```bash
make lint
make type-check
make test
```

`make lint` fails if Ruff reports a problem or Black would reformat a file.
