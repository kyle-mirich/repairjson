# Architecture and project flows

## Source map

| Path | Responsibility |
| --- | --- |
| `src/lexer.rs` | Byte cursor, token boundaries, BOM/fence trimming, preamble scanning |
| `src/parser.rs` | Container repair, string escaping, literal/number normalization, nesting bound |
| `src/lib.rs` | PyO3 bindings, Python errors, GIL release, version and depth metadata |
| `python/repairjson/` | Explicit Python exports and packaged typing information |
| `python/tests/` | Installed API regressions and generated invariants |
| `benchmark.py` | Reproducible synthetic throughput comparison |
| `.github/workflows/CI.yml` | Validation, platform builds, trusted publication |

## Repair flow

1. PyO3 accepts a Python Unicode string and borrows its UTF-8 representation.
2. The wrapper detaches from the Python interpreter while Rust performs repair, allowing other Python threads to run.
3. The lexer trims a BOM and surrounding fences, then searches outside quotes for an object or array payload.
4. A bounded recursive-descent parser writes compact JSON into one output buffer. Each container consumes its own closing delimiter; an encountered parent delimiter is left for the parent.
5. Strings share one escaping routine. Numbers are validated before being normalized directly into the output buffer, without a per-number allocation or floating-point conversion.
6. A successful result becomes a Python string. `loads()` additionally calls Python's `json.loads()` after reattaching. A depth-limit error becomes `ValueError`.

The lexer and parser advance through input without backtracking. The preamble scan can visit bytes once before parsing them; this is not a strict one-pass parser. Time is linear in input length, with memory proportional to input/output size and bounded native recursion. Parser state is local to each call; no unsafe Rust or global mutable state is used in this crate.

## Design boundaries

The engine repairs syntax without understanding a schema. It produces one plausible value rather than an edit log. The [behavior reference](behavior.md) documents lossy choices. A stable-ABI extension keeps wheel count small while supporting CPython 3.8 and newer. The native Rust API is not published as a separate supported crate.

## Validation and publication

Rust unit tests exercise low-level behavior. Python tests run through the installed extension, including generated checks for valid-JSON preservation, idempotence, malformed text, and truncation. Additional regressions cover concurrency, Unicode, escaping, API errors, metadata, and type files.

CI checks formatting, lints, the minimum Rust version, multiple Python versions, native wheels, and source-distribution installation. Tagged releases publish only after those checks and all platform builds pass. See the [release guide](releases.md).
