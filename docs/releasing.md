# Releasing retrievalgate

This document is intentionally boring. Releases should be reproducible and should not depend on a maintainer copying long-lived PyPI tokens into GitHub.

## One-time PyPI setup

Before the first tag, configure a **pending Trusted Publisher** on PyPI:

- PyPI project name: `retrievalgate`
- GitHub owner: `oalangomes`
- GitHub repository: `retrievalgate`
- workflow filename: `release.yml`
- environment: `pypi`

The repository release workflow requests OIDC only in the dedicated publish job. No PyPI API token is stored in GitHub.

A GitHub environment named `pypi` is recommended. Add a required reviewer if you want a manual approval between build verification and publication.

## Release gate

Do not create a release tag unless all of these are true:

- [ ] version in `pyproject.toml` is the intended release version;
- [ ] `CHANGELOG.md` contains the release;
- [ ] CI is green on Python 3.11, 3.12, and 3.13;
- [ ] Ruff is green;
- [ ] mypy strict is green;
- [ ] wheel and sdist build successfully;
- [ ] `twine check dist/*` succeeds;
- [ ] clean-wheel quickstart succeeds;
- [ ] PyPI Trusted Publisher is configured for this repository/workflow/environment;
- [ ] README installation instructions match the release.

## Publishing

For version `0.1.0`, create and push exactly this tag from the release commit:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The tag-triggered workflow then:

1. verifies that `v0.1.0` matches the package version;
2. builds wheel and source distribution;
3. validates package metadata;
4. installs the wheel into a clean virtual environment and runs the example;
5. uploads the already-built distributions as a workflow artifact;
6. publishes those same distributions to PyPI through Trusted Publishing;
7. creates the GitHub Release only after PyPI publication succeeds.

## Post-release smoke

Verify installation from the public index, not from the repository:

```bash
pipx install retrievalgate
retrievalgate --help
```

And, separately:

```bash
uv tool install retrievalgate
retrievalgate --help
```

Then run the documented minimal example from a clean checkout.

If public installation fails, the release is not considered complete.
