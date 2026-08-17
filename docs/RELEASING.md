# Releasing Benedict

Benedict follows [Semantic Versioning](https://semver.org/). Document every user-visible change in [CHANGELOG.md](../CHANGELOG.md) using [Keep a Changelog](https://keepachangelog.com/).

## Versioning

- **MAJOR**: incompatible API or bot command changes
- **MINOR**: backward-compatible features
- **PATCH**: backward-compatible fixes

The open-source line starts at `0.4.0`. Breaking changes are allowed in 0.x with a clear changelog note.

## Release checklist

1. Move `[Unreleased]` notes into a dated version section in `CHANGELOG.md`.
2. Set the same version in `pyproject.toml` and `src/benedict/__init__.py`.
3. Run `make check` and `make typecheck`.
4. Commit the version bump.
5. Tag the commit: `git tag v0.4.0`.
6. Push the tag: `git push origin v0.4.0`.

Pushing a `v*` tag runs [`.github/workflows/release.yml`](../.github/workflows/release.yml), which builds the package and creates a GitHub Release.

## PyPI

Publishing to PyPI is optional until the package name is reserved.

1. Build locally: `make build`
2. Upload to TestPyPI: `make publish-test`
3. Install from TestPyPI and smoke-test `benedict --help` or `python -m benedict.main`
4. Upload to PyPI: `make publish`

The release workflow publishes to PyPI when the `PYPI_API_TOKEN` repository secret is set.
