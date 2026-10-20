# Contributing

## Releases

Releases are automated. Merging to `main` publishes a new version of both
`llama-index-tools-decodo` and `llama-index-readers-decodo` based on the PR
title, which must follow [Conventional Commits](https://www.conventionalcommits.org):
`fix:` → patch, `feat:` → minor, `feat!:` or a `BREAKING CHANGE:` footer → major.
`chore:`, `docs:`, `ci:`, `refactor:`, `test:` don't release. Don't edit the
version in either package's `pyproject.toml`.
