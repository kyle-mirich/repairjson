# JSON Repair project overview

JSON Repair (`repairjson`) is a published Python library that recovers common malformed model output using a Rust parser exposed through PyO3. It combines an ergonomic Python API with compact text output, bounded native recursion, explicit error behavior, and tests at the Python/Rust boundary. Repair is heuristic: applications still need input limits and validation of the recovered value.

## Evidence-backed achievement wording

- Published a Rust-backed Python JSON repair library with PyO3 bindings and stable-ABI wheels for 15 platform targets.
- Expanded public API verification to 168 tests, including isolated process-survival checks for hostile nesting, Unicode boundaries, truncation, and 10,000 deterministic malformed inputs.
- Strengthened a reproducible benchmark across eight synthetic corpora, verifying all 62,276 records against independent expected values before comparing native repair with explicit Python baselines.

These are independent-project achievements. They do not establish customer adoption, download counts, production scale, or a universal speedup.

## Supporting evidence (2026-10-01)

| Claim | Evidence and scope |
| --- | --- |
| Published Python package | [PyPI 0.2.0](https://pypi.org/project/repairjson/0.2.0/), [GitHub release](https://github.com/kyle-mirich/repairjson/releases/tag/v0.2.0), 15 wheels plus an sdist in live PyPI metadata |
| Native parser and Python boundary | [Architecture](flows.md), [Rust parser](../src/parser.rs), [PyO3 API](../src/lib.rs) |
| Regression and property coverage | [Python tests](../python/tests/), 168 passing tests in clean local release-wheel environments on CPython 3.8.20, 3.12.12, and 3.14.0, macOS arm64 |
| Fresh source installation | Final sdist installs in a separate CPython 3.12 environment and passes all 168 packaged tests; wheel and sdist metadata pass `twine check --strict` |
| Rust verification | Six Rust tests passing on Rust 1.94 and the minimum 1.88 toolchain; stable formatting and Clippy checks passing |
| Larger malformed-input check | [Input checker](../scripts/check_inputs.py), `--cases 100000 --seed 76381`: 88,426 valid idempotent repairs, 11,574 documented errors, seven large-input scenarios, and all public aliases still usable |
| Reproducible comparison | [Methodology](../benchmarks/README.md), [raw annotated report](../benchmarks/results/0.2.0-calibrated-macos-arm64-loaded.json), full verification on three repair paths and a fourth valid-input-only baseline |
| Practical application boundary | [Runnable example](../examples/repair_response.py): strict parse first, 16 KiB input cap, exact fields, type checks, finite numeric range |

## Limitations

The latest benchmark ran under substantial shared-machine load and is unsuitable for résumé speedup claims. It measures many small synthetic records, not production repair accuracy, one large document, `loads()` latency, peak memory, or thread scalability. The broader `json-repair` package has different heuristics and is not behaviorally interchangeable.

The nesting bound reduces stack risk but does not bound input bytes or wide arrays. Truncation, unknown escapes, duplicate keys, and trailing data can lose information; see [behavior rules](behavior.md). The hostile-input checks are regression evidence, not proof that all crashes or resource-exhaustion cases are impossible. No parser semantics, package version, or publication was changed in this maintenance pass.
