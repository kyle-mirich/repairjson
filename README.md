# repairjson

Blazing-fast JSON repair for messy LLM output.

`repairjson` is a Rust-powered drop-in repair layer for malformed JSON in Python. It is built for the reality of modern LLM pipelines: broken commas, single quotes, unquoted keys, truncated payloads, Markdown fences, and half-finished responses that still need to get through production systems.

If `json.loads()` is too strict and Python-side repair is too slow, this is the fast path.

## Why repairjson

- Rust core with a single-pass repair engine
- designed for malformed LLM-style JSON, not just clean parser input
- published PyPI wheels
- benchmarked at roughly `~200x` average speedup versus Python `json_repair` on the current 20 MB malformed corpus suite

## What It Repairs

- single-pass byte-oriented repair
- support for single-quoted strings
- support for Python literals like `True`, `False`, and `None`
- repair of unquoted object keys
- repair of missing commas and trailing commas
- auto-closing of truncated objects and arrays
- stripping of leading and trailing Markdown code fences

## Install

```bash
pip install repairjson
```

## Fast Example

```bash
python -c "import repairjson; print(repairjson.repair(\"{user: 'alice', active: True, tags: ['x', 'y',],}\"))"
```

Output:

```json
{"user":"alice","active":true,"tags":["x","y"]}
```

## Usage

```python
import repairjson

fixed = repairjson.repair("{user: 'alice', active: True, tags: ['x', 'y',],}")
print(fixed)
# {"user":"alice","active":true,"tags":["x","y"]}

obj = repairjson.loads("{user: 'alice', active: True, tags: ['x', 'y',],}")
print(obj)
# {'user': 'alice', 'active': True, 'tags': ['x', 'y']}
```

## Benchmarks

Current benchmark suite: six synthetic 20 MB malformed-JSON datasets modeled after LLM-style output patterns.

- `dense_object`: `206.2x`
- `fenced_payload`: `202.81x`
- `chatty_nested`: `242.24x`
- `long_text`: `198.91x`
- `array_heavy`: `209.86x`
- `truncated_nested`: `229.48x`

Average across the current suite: about `214.9x`.

The conservative claim is still `100x+`, because real-world speedups depend on payload shape, string density, and how broken the JSON is.

## Development

Create the local environment and install the package in editable mode:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip maturin pytest json_repair
.venv/bin/maturin develop
```

Run tests:

```bash
cargo test
.venv/bin/pytest -q
```

Run benchmarks:

```bash
.venv/bin/python benchmark.py --dataset all
```
