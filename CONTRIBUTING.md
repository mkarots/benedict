# Contributing to Benedict

Thank you for your interest in contributing.

Please read the [Code of Conduct](CODE_OF_CONDUCT.md) before participating.
Report security issues using the [security policy](SECURITY.md), not public issues.

## Development setup

You need Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/mkarots/benedict.git
cd benedict
make setup
source .venv/bin/activate
make sync-dev
cp .env.example .env
```

Fill in Slack and Anthropic credentials in `.env`. See [docs/SLACK_SETUP.md](docs/SLACK_SETUP.md).

Install git hooks:

```bash
make pre-commit-install
```

## Running checks

```bash
make test          # pytest
make test-cov      # pytest with coverage
make format        # black + ruff
make lint          # ruff check
make typecheck     # mypy
make check         # format + tests
```

Or:

```bash
uv run pytest tests/ -v
uv run pytest --cov=src/benedict --cov-report=term-missing
```

## Code style

- Match existing patterns in the module you are editing.
- Prefer composition and protocols over large god objects.
- Instantiate concrete classes at the composition root (`src/benedict/main.py`).
- Keep diffs focused. Avoid drive-by refactors.
- Line length is 100. Black and Ruff are the source of truth.

## Tests

- Add or update unit tests for behavior changes.
- Put unit tests under `tests/unit/`.
- Put workflow tests that cross module boundaries under `tests/integration/`.
- Mock Slack, Anthropic, and the filesystem. Do not call live APIs in tests.

## Pull requests

1. Open an issue or comment on an existing one before large changes.
2. Create a branch from `main`.
3. Keep the change small enough to review.
4. Add or update tests.
5. Update `CHANGELOG.md` under `[Unreleased]`.
6. Fill in the pull request template.

### Commit messages

Use a short prefix and a sentence that explains why:

- `feat: ...` new behavior
- `fix: ...` bug fix
- `docs: ...` documentation
- `test: ...` tests only
- `chore: ...` tooling, CI, packaging

## Reporting bugs

Use the bug report template. Include:

- What you expected
- What happened
- Steps to reproduce
- Environment (OS, Python version)
- Relevant logs with tokens and channel IDs redacted

## Feature requests

Use the feature request template. Describe the use case first, then a proposed solution.

## Release process

See [docs/RELEASING.md](docs/RELEASING.md).
