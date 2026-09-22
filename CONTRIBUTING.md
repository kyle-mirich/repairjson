# Contributing to repairjson

Parser fixes, small reproductions, documentation improvements, and packaging reports are welcome. Please use non-sensitive input examples and keep proposed repair behavior explicit.

## Setup

Use Python 3.10+ for development (3.12 recommended), Rust 1.88+ with `rustfmt` and `clippy`, a C linker, and [uv](https://docs.astral.sh/uv/). The installed library supports CPython 3.8+; the complete development toolset has a higher floor.

```bash
git clone https://github.com/kyle-mirich/repairjson.git
cd repairjson
uv venv --python 3.12
uv pip install -e ".[dev]"
```

Editable installation builds the native extension. **After every Rust change, rebuild it** before running Python tests:

```bash
uv pip install --reinstall -e ".[dev]"
```

On Windows, replace `.venv/bin/` in commands below with `.venv\Scripts\`. No credentials or external services are needed for development.

## Checks

```bash
cargo fmt --check
cargo clippy --locked --all-targets -- -D warnings
cargo test --locked
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest -q
```

Rust tests cover parser internals and depth boundaries. Python regression tests cover the installed API. Hypothesis checks valid-value preservation, arbitrary Unicode, syntax noise, truncation, and repair idempotence with deterministic generated examples.

To exercise older Python versions, create a separate environment and install `.[test]`. CI checks Python 3.8, 3.10, 3.12, and 3.14, Rust stable and 1.88, and installed wheels on the native release runners.

For packaging changes, build and validate both distribution formats:

```bash
.venv/bin/maturin build --release --locked --sdist -i .venv/bin/python -o dist
.venv/bin/twine check --strict dist/*
```

Test the wheel in a new environment so the editable build cannot mask missing files:

```bash
uv venv .venv-wheel --python 3.12
uv pip install --python .venv-wheel/bin/python --no-index --find-links dist repairjson
uv pip install --python .venv-wheel/bin/python "pytest>=7.4" "hypothesis>=6"
.venv-wheel/bin/python -m pytest -q
```

## Parser changes

1. Add the smallest reproduction to `python/tests/test_regressions.py` or the Rust unit tests.
2. Assert the decoded value, not just the formatting of the output.
3. Check that valid JSON retains its value and repaired output is idempotent.
4. Explain ambiguous interpretations in `docs/behavior.md` and the changelog.
5. Run the checks above. Use the [benchmark](benchmarks/README.md) for performance changes.

Avoid adding broad format support under a narrow fix. Comments, streaming, and JavaScript parsing require their own design decisions. Do not add private model payloads or generated corpora to the repository.

## Pull requests and releases

Describe the triggering input, the resulting behavior, and validation. Follow the [conduct guidelines](CODE_OF_CONDUCT.md), use [private reporting](SECURITY.md) for security issues, and leave publication to maintainers following the [release guide](docs/releases.md).
