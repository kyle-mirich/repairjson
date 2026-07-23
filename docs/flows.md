# Project flows

## Repair flow

1. Python passes a Unicode string through the PyO3 extension.
2. The lexer trims surrounding Markdown fences and searches conversational text for the first object or array.
3. The parser walks the input bytes, normalizing strings, literals, numbers, separators, and container endings.
4. `repair()` returns compact JSON. `loads()` additionally delegates to Python's `json.loads()`.

The parser is intentionally heuristic. It produces one repaired value rather than preserving every byte or reporting a list of edits.

## Validation flow

Rust tests exercise parser internals and malformed-input regressions. Python tests verify the installed extension, aliases, deserialization, Unicode preservation, and public metadata.

## Release flow

Pushes and pull requests run formatting, Clippy, Rust tests, and Python tests. A `v*` tag builds ABI3 wheels for the configured platforms and a source distribution, generates build provenance, and publishes to PyPI through GitHub trusted publishing.
