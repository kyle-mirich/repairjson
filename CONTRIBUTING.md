# Contributing to repairjson

Thank you for improving `repairjson`. Small, well-tested changes are easiest to review, especially when parser behavior is involved.

## Development setup

Install Python 3.8 or newer, Rust stable, and `uv`, then run:

```bash
git clone https://github.com/kyle-mirich/repairjson.git
cd repairjson
uv venv
uv pip install -e ".[dev]"
```

No environment variables or external services are required.

## Verification

Run the full local check before opening a pull request:

```bash
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test
.venv/bin/python -m pytest -q
```

Build release artifacts when changing packaging or release configuration:

```bash
.venv/bin/maturin build --release --sdist -i .venv/bin/python -o dist
.venv/bin/twine check dist/*
```

## Parser changes

- Add a minimal regression test for the malformed input.
- Assert that `repair()` returns valid JSON, not only the expected text shape.
- Preserve valid JSON values whenever the input is unambiguous.
- Document intentionally heuristic or lossy behavior.
- Remove private or sensitive content from real model payloads before adding fixtures.

## Pull requests

- Keep each pull request focused on one problem.
- Explain the ambiguity and chosen repair behavior when several interpretations are possible.
- Update the README and changelog for user-visible changes.
- Do not include generated benchmark corpora, wheels, virtual environments, or credentials.
