# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases use [Semantic Versioning](https://semver.org/).

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

[0.1.3]: https://github.com/kyle-mirich/repairjson/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/kyle-mirich/repairjson/releases/tag/v0.1.2
