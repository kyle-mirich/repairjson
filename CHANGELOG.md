# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases use [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-09-21

### Fixed

- Missing object values no longer consume the next field (`{a:,b:2}` now preserves both keys).
- Mismatched closing delimiters end the appropriate container instead of absorbing sibling data.
- Raw and escaped control characters are preserved through JSON escapes, including NUL and CRLF.
- Adjacent quoted values are separated from bare tokens when commas are missing.
- Unquoted keys and values beginning with non-ASCII characters are preserved.
- Initial UTF-8 BOMs are ignored before locating the payload.

### Added

- A 128-container nesting bound with a Python `ValueError`, preventing unbounded native recursion.
- Public `MAX_DEPTH` metadata, explicit exports, type stubs, and a `py.typed` marker.
- Missing-colon recovery for inputs such as `{count 2}`.
- Property tests for valid-value preservation, arbitrary Unicode, malformed syntax, truncation, and idempotence.
- Regression coverage for concurrent callers, API errors, installed typing files, and resource boundaries.
- Tested minimum Rust version (1.88), Python 3.8/3.10/3.12/3.14 checks, installed-wheel tests, and source-distribution tests.
- Tag/version checks, strict distribution validation, pinned GitHub Actions, and changelog-based release notes.
- Behavior and release references, contributor conduct guidelines, and a feature-request template.

### Changed

- Rust repair releases the GIL; each call retains independent parser state.
- Number normalization writes directly into the output buffer instead of allocating temporary vectors.
- Simplified parser control flow and removed unused lexer lookahead.
- Updated PyO3 to 0.29.2 and modernized license metadata.
- Benchmarks now record environment metadata, verify spread-out samples before timing, warm both implementations, alternate timing order, and report repeated samples with medians.

### Migration notes

- Inputs deeper than 128 containers now raise `ValueError` instead of risking a process abort. Handle this error at the input boundary.
- Control characters are now retained, so decoded strings may differ from 0.1.x output that deleted them or normalized CRLF.
- Missing-value, missing-colon, and mismatched-delimiter repairs intentionally change some ambiguous results. Review the [behavior reference](docs/behavior.md) if your application depended on the previous heuristics.
- Supported binary releases target standard CPython. PyPy and free-threaded Python are not included in the tested release matrix.

## [0.1.3] - 2026-07-22

### Fixed

- Escaped tabs and control characters can no longer produce invalid JSON strings.
- Malformed decimals with exponents are normalized in valid JSON number order.

### Added

- Regression tests for control characters, exponent repair, Unicode preservation, and version metadata.
- Standard development and benchmark dependency groups.
- A Python-version marker that keeps the benchmark extra compatible with the library's Python 3.8 support.
- Formatting and Clippy enforcement in CI.

### Changed

- Removed unused parser context state and its dependency.
- Reworked documentation to describe heuristic behavior and safety limitations precisely.
- Limited release tags to the `v*` convention.
- Updated PyO3 to a version without the advisories affecting the previous dependency line.

## [0.1.2] - 2026-04-03

### Fixed

- Improved repair behavior for conversational preambles and malformed numbers.

[Unreleased]: https://github.com/kyle-mirich/repairjson/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/kyle-mirich/repairjson/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/kyle-mirich/repairjson/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/kyle-mirich/repairjson/releases/tag/v0.1.2
