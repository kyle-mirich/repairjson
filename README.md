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
- skipping chatty preambles to recover the first JSON object or array payload

## Install

```bash
uv add repairjson
```

For a plain virtual environment:

```bash
uv venv
VIRTUAL_ENV=.venv uv pip install --python .venv/bin/python repairjson
```

## Fast Example

```bash
uv run --with repairjson python -c "import repairjson; print(repairjson.repair(\"{user: 'alice', active: True, tags: ['x', 'y',],}\"))"
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

## Performance

Current benchmark suite: six synthetic 20 MB malformed-JSON datasets modeled after LLM-style output patterns.

- `dense_object`: `206.2x`
- `fenced_payload`: `202.81x`
- `chatty_nested`: `242.24x`
- `long_text`: `198.91x`
- `array_heavy`: `209.86x`
- `truncated_nested`: `229.48x`

Average across the current suite: about `214.9x`.

The conservative claim is still `100x+`, because real-world speedups depend on payload shape, string density, and how broken the JSON is.

The benchmark harness lives in [`benchmark.py`](./benchmark.py).

## Development

Create the local environment and install the package in editable mode:

```bash
uv venv
VIRTUAL_ENV=.venv uv pip install --python .venv/bin/python maturin pytest json_repair
uv run maturin develop
```

Run tests:

```bash
cargo test
uv run pytest -q
```

Run benchmarks:

```bash
uv run python benchmark.py --dataset all
```

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the development workflow and pull request expectations.

## License

MIT. See [`LICENSE`](./LICENSE).
