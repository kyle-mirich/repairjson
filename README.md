# repairjson

[![CI](https://github.com/kyle-mirich/repairjson/actions/workflows/CI.yml/badge.svg)](https://github.com/kyle-mirich/repairjson/actions/workflows/CI.yml)
[![PyPI](https://img.shields.io/pypi/v/repairjson)](https://pypi.org/project/repairjson/)
[![Python](https://img.shields.io/pypi/pyversions/repairjson)](https://pypi.org/project/repairjson/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/kyle-mirich/repairjson/blob/main/LICENSE)

A small Rust-backed Python library for repairing malformed JSON from language models and other text sources. Recover a value from single quotes, Python literals, missing punctuation, Markdown fences, and truncated containers.

```bash
python -m pip install repairjson
```

```python
import repairjson

source = "{user: 'alice', active: True, tags: ['x', 'y',],}"

print(repairjson.repair(source))
# {"user":"alice","active":true,"tags":["x","y"]}

print(repairjson.loads(source))
# {'user': 'alice', 'active': True, 'tags': ['x', 'y']}
```

CPython 3.8+ is supported. Binary wheels cover Windows, macOS, glibc Linux, and musl Linux on the [release platforms](https://github.com/kyle-mirich/repairjson/blob/main/docs/releases.md#platforms). Installation from a wheel requires no Rust toolchain and adds no Python runtime dependencies. Source builds require Rust 1.88+ and a C linker. PyPy and free-threaded Python wheels are not part of the supported release matrix.

## Repair examples

| Input | Repaired JSON |
| --- | --- |
| `{name: 'Ada', ready: True}` | `{"name":"Ada","ready":true}` |
| `{items: [1 2 3,]}` | `{"items":[1,2,3]}` |
| `{count 2}` | `{"count":2}` |
| `{missing:, next: 2}` | `{"missing":null,"next":2}` |
| `{items: [1, 2` | `{"items":[1,2]}` |
| `{value: +.5, other: 01, exp: 1e+}` | `{"value":0.5,"other":1,"exp":1e+0}` |
| `Here is the result: {ok: True}` | `{"ok":true}` |

Quoted Unicode and JSON escapes are preserved. Raw control characters inside strings are escaped, including carriage returns and NUL bytes. Unquoted Unicode keys and values are accepted. See [repair rules and boundaries](https://github.com/kyle-mirich/repairjson/blob/main/docs/behavior.md) for exact examples and ambiguous cases.

## API

| Name | Result |
| --- | --- |
| `repair(input: str) -> str` | One compact JSON value as text |
| `loads(input: str) -> Any` | The repaired value decoded by Python's `json.loads()` |
| `repair_to_string(input: str) -> str` | Compatibility alias for `repair()` |
| `repair_json(input: str) -> str` | Compatibility alias for `repair()` |
| `__version__` | Installed package version |
| `MAX_DEPTH` | Maximum nesting: 128 simultaneously open containers |

All functions accept a Python `str`. Empty input becomes `null` (`None` with `loads`). More than 128 nested objects/arrays raises `ValueError`. Ambiguous unescaped quotes in an object value also raise `ValueError` (for example, `{"command": "say "hello" now"}`). Escape the inner quotes before retrying. Non-string inputs raise `TypeError`. Raw unpaired surrogates cannot cross the UTF-8 extension boundary and raise `UnicodeError`; escaped forms such as `r'"\ud800"'` are accepted. `loads` also inherits Python's numeric conversion limits and errors.

The Rust repair step releases the GIL. Each call owns its parser state, so independent inputs can be repaired from multiple Python threads. Type stubs and a `py.typed` marker are included.

## Choosing a repair policy

Repair is heuristic: it produces a plausible value, not proof of the source's intended meaning. Validate the result against your application's expected schema. This is useful for recovering a model's response; it is not a substitute for strict parsing when accepting configuration, authorizations, or signed data.

- The first object or array outside quotes takes precedence over a prose preamble. Otherwise the first scalar is parsed.
- Text after the recovered value is ignored. This is not a JSON Lines or streaming parser.
- A missing closing delimiter is inserted; an encountered parent delimiter ends the nested container. Later text may therefore be excluded.
- Duplicate keys remain in repaired text; `loads` keeps the last value, like Python's JSON decoder.
- Line (`//`) and block (`/* ... */`) comments are skipped outside strings. JavaScript expressions and arbitrary multiword bare strings are not supported syntax.
- Callers should bound input size. Repair uses memory proportional to input/output size; the nesting limit does not limit large strings or arrays.

The project is alpha software. Version 0.2 improves several repair choices and adds a nesting error; see the [migration notes](https://github.com/kyle-mirich/repairjson/blob/main/CHANGELOG.md#020---2026-09-21).

## Benchmarks

The [benchmark harness](https://github.com/kyle-mirich/repairjson/blob/main/benchmark.py) compares repair-to-string throughput with Python's `json-repair`. It generates six synthetic corpora of many small records, checks sampled output equivalence, warms both implementations, alternates execution order, and reports repeated timings with environment metadata.

```bash
uv venv --python 3.12
uv pip install -e ".[dev,benchmark]"
.venv/bin/python benchmark.py --megabytes 1 --repeat 3 --output benchmarks/local.json
```

See [methodology and a reproducible sample run](https://github.com/kyle-mirich/repairjson/blob/main/benchmarks/README.md). These corpora do not measure repair accuracy, large-document latency, or performance on your own model output. No universal speedup is promised.

## Development and community

Start with [CONTRIBUTING.md](https://github.com/kyle-mirich/repairjson/blob/main/CONTRIBUTING.md) for setup, checks, and parser changes. The [architecture notes](https://github.com/kyle-mirich/repairjson/blob/main/docs/flows.md) explain the parser and [release guide](https://github.com/kyle-mirich/repairjson/blob/main/docs/releases.md) covers publication.

- [Report a bug](https://github.com/kyle-mirich/repairjson/issues/new?template=bug_report.yml) with a minimal, non-sensitive example.
- [Request a feature](https://github.com/kyle-mirich/repairjson/issues/new?template=feature_request.yml) with the input and intended behavior.
- Report security issues privately using the [security policy](https://github.com/kyle-mirich/repairjson/blob/main/SECURITY.md).
- Read the [changelog](https://github.com/kyle-mirich/repairjson/blob/main/CHANGELOG.md) and [contributor conduct guidelines](https://github.com/kyle-mirich/repairjson/blob/main/CODE_OF_CONDUCT.md).

MIT licensed. See [LICENSE](https://github.com/kyle-mirich/repairjson/blob/main/LICENSE).
