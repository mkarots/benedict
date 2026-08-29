# Contributing to Benedict

This guide is how you set up a development environment, run checks, report issues, use Discussions, and open a pull request.

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md). Report unacceptable behavior privately as that document describes. Do not open a public issue for a conduct report.

## Development environment

You need:

- Python 3.10 or newer
- [uv](https://docs.astral.sh/uv/)
- Make (optional; the `uv` commands below are equivalent)

Install uv if you do not have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or: brew install uv
```

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/mkarots/benedict.git
cd benedict
make setup
source .venv/bin/activate
make sync-dev
```

`make setup` creates `.venv`. `make sync-dev` installs the package and the `dev` extra (pytest, Ruff, Black, mypy, Pylint, and the docs tools).

Without Make:

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

You do not need Slack tokens or an Anthropic key to run lint, type check, or tests. You need them only to run the bot (`make run`). See [docs/install.md](docs/install.md) and [docs/SLACK_SETUP.md](docs/SLACK_SETUP.md).

## Tests

```bash
make test        # all tests
make test-cov    # tests plus a terminal and HTML coverage report
make test-unit
make test-integration
```

Without Make: `uv run pytest`, `uv run pytest --cov=src/benedict --cov-report=term-missing --cov-report=html`.

New logic needs a unit test. New routes or workflows need an integration test when one applies. Details and fixtures: [tests/README.md](tests/README.md).

## Code style and type checking

CI on every pull request and on `main` runs the same checks as these targets. See [docs/ci.md](docs/ci.md).

| Check | Command | Tools |
| --- | --- | --- |
| Format and lint | `make lint` | [Ruff](https://docs.astral.sh/ruff/) (`ruff check src tests`) and [Black](https://black.readthedocs.io/) (`black --check src tests`) |
| Type check | `make type-check` | [mypy](https://mypy.readthedocs.io/) on `src/benedict` |
| Format files | `make format` | Black rewrite, then Ruff `--fix` |
| All of the above plus coverage | `make check` | format-check, lint, type-check, test-cov |

Line length is 100 (`[tool.black]` and `[tool.pylint]` in `pyproject.toml`).

Pylint is in the `dev` extra (`pylint src/benedict`). It is not part of `make lint` or CI. Use it locally if you want a second pass.

Ruff, Black, and mypy versions are pinned in `pyproject.toml` so a local `make sync-dev` matches CI.

## Commit messages

Use a short subject that states why the change exists, not a file list.

```
docs: add CONTRIBUTING.md with setup and PR guidelines
```

Common prefixes: `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`. Keep the subject to one line. Add a body when the why is not obvious from the subject.

This repository uses [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and [SemVer](https://semver.org/). If the change is user-visible, bump the version in `pyproject.toml` and `src/benedict/__init__.py`, and add a dated section in `CHANGELOG.md` that links the issue.

## Issue reporting

Search [existing issues](https://github.com/mkarots/benedict/issues) before you open a new one.

Questions, ideas, and show-and-tell posts belong in [GitHub Discussions](https://github.com/mkarots/benedict/discussions), not in issues.

| Kind | Where |
| --- | --- |
| Question, idea, or show and tell | [Discussions](https://github.com/mkarots/benedict/discussions) (Q&A, Ideas, Show and tell) |
| Bug | [Bug report](https://github.com/mkarots/benedict/issues/new?template=bug_report.md) template |
| Feature | [Feature request](https://github.com/mkarots/benedict/issues/new?template=feature_request.md) template |
| Security vulnerability | [SECURITY.md](SECURITY.md) — private disclosure only |
| Code of Conduct | [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — private report only |

A useful issue states the expected behavior, the actual behavior, and how to reproduce it. Redact tokens, API keys, and other secrets.

Maintainers apply labels such as `bug`, `enhancement`, `architecture`, `testing`, `documentation`, `question`, `good first issue`, and `help wanted`.

## Pull requests

1. Branch from `main`. Use a name that matches the work (`docs/…`, `fix/…`, `feat/…`).
2. Keep the change small and focused. Do not mix unrelated refactors.
3. Add or update tests for the behavior you change.
4. If behavior, commands, paths, env vars, or architecture changed, update `README.md` and the matching pages under `docs/` in the same change. Do not leave current docs describing the old system.
5. Run `make lint`, `make type-check`, and `make test` (or `make check`) before you push.
6. Open a pull request against `main`. Link the issue (`Fixes #52` or `Closes #52`).
7. In the PR body, write a short Summary (what and why) and a Test plan with checkboxes.

CI must pass. Reviewers look for correctness, a readable diff, and docs that match the code.

If the change is something a human sees (operator UI, landing page, docs chrome, Slack Block Kit), include a screenshot in the PR body or under `docs/` and link it.

A pull request template is not in the repository yet. Use the Summary and Test plan sections above until one exists.
