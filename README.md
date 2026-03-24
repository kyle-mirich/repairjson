# repairjson

`repairjson` is a Rust-backed Python package for repairing malformed JSON, especially the kind of output commonly produced by LLMs.

It is designed as a fast replacement for Python-first JSON repair workflows:

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
