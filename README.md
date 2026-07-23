# repairjson

[![CI](https://github.com/kyle-mirich/repairjson/actions/workflows/CI.yml/badge.svg)](https://github.com/kyle-mirich/repairjson/actions/workflows/CI.yml)
[![PyPI](https://img.shields.io/pypi/v/repairjson)](https://pypi.org/project/repairjson/)
[![Python](https://img.shields.io/pypi/pyversions/repairjson)](https://pypi.org/project/repairjson/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

`repairjson` is a Rust-backed Python library that turns common forms of malformed, LLM-style JSON into valid JSON. It is useful at system boundaries where model output is close to JSON but may contain Python literals, missing punctuation, Markdown fences, or a truncated container.

## What it repairs

- Single-quoted strings and unquoted object keys
- Python literals such as `True`, `False`, and `None`
- Missing or trailing commas
- Truncated objects and arrays
- Common malformed number forms
- Raw newlines, tabs, and control characters inside strings
- Leading Markdown fences and conversational preambles before an object or array

The repair engine is byte-oriented and returns compact JSON. `loads()` performs repair and then delegates deserialization to Python's standard `json` module.

## Installation

```bash
python -m pip install repairjson
```

## Quick start

```python
import repairjson

source = "{user: 'alice', active: True, tags: ['x', 'y',],}"

fixed = repairjson.repair(source)
print(fixed)
# {"user":"alice","active":true,"tags":["x","y"]}

value = repairjson.loads(source)
print(value["user"])
# alice
```

## API

### `repairjson.repair(input: str) -> str`

Returns a repaired JSON string. For example:

```python
repairjson.repair("Here is the JSON:\n```json\n{answer: 42}\n```")
# '{"answer":42}'
```

### `repairjson.loads(input: str) -> object`

Repairs the input and returns the Python value produced by `json.loads()`.

`repair_to_string()` and `repair_json()` remain available as compatibility aliases for `repair()`.

## Limitations and safety

Repair is heuristic and can be lossy. Ambiguous input may have more than one reasonable interpretation; callers should validate the returned value against an expected schema before using it. The library extracts the first object or array found after a conversational preamble and ignores trailing prose after the parsed value.

This package does not perform schema validation, stream parsing, or security policy enforcement. Apply normal input-size and nesting limits when processing untrusted data. If exact preservation is required, reject malformed input instead of repairing it.

The package is currently an alpha release. See [CHANGELOG.md](CHANGELOG.md) for release history.

## Benchmarking

The benchmark harness compares `repairjson` with the Python `json-repair` package across generated malformed-input profiles:

```bash
uv run --extra benchmark python benchmark.py --dataset all
```

The benchmark requires Python 3.10 or newer because of its comparison dependency. It checks a sample for semantic equivalence before reporting timings. Results vary with hardware, package versions, and input shape, so the project does not claim a fixed speedup.

## Development

Prerequisites: Python 3.8 or newer, Rust stable, and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/kyle-mirich/repairjson.git
cd repairjson
uv venv
uv pip install -e ".[dev]"
```

Run the same checks used by CI:

```bash
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test
.venv/bin/python -m pytest -q
```

Build and inspect release artifacts:

```bash
.venv/bin/maturin build --release --sdist -i .venv/bin/python -o dist
.venv/bin/twine check dist/*
```

## Project structure

- `src/lexer.rs`: byte-level input traversal and fence handling
- `src/parser.rs`: repair state machine and normalization logic
- `src/lib.rs`: PyO3 Python API
- `python/tests/`: end-to-end Python API tests
- `benchmark.py`: generated-corpus benchmark harness
- `.github/workflows/CI.yml`: checks, wheels, attestations, and trusted publishing
- [`docs/flows.md`](docs/flows.md): repair and release flows

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and pull request expectations.

Report security issues privately as described in [SECURITY.md](SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).
