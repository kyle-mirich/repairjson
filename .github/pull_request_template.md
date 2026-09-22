## Summary

Describe the malformed-input case or project issue and the focused change that addresses it.

## Validation

- [ ] `cargo fmt --check`
- [ ] `cargo clippy --locked --all-targets -- -D warnings`
- [ ] `cargo test --locked`
- [ ] `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .`
- [ ] Rebuilt the extension after Rust changes
- [ ] `.venv/bin/python -m pytest -q`
- [ ] New repair behavior has a minimal regression test
- [ ] User-facing behavior and documentation agree
