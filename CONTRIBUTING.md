# Contributing

## Development setup

```bash
uv venv
VIRTUAL_ENV=.venv uv pip install --python .venv/bin/python maturin pytest json_repair
uv run maturin develop
```

## Verification

Run the full local check before opening a pull request:

```bash
cargo test
uv run pytest -q
uv build
```

## Pull requests

- Keep changes scoped to one problem.
- Add or update tests for behavioral changes.
- Update `README.md` when user-facing behavior or commands change.
