# Security policy

## Supported versions

Security fixes are applied to the latest published release. Users should upgrade before reporting an issue that only affects an older version.

## Reporting a vulnerability

Please use [GitHub's private vulnerability reporting](https://github.com/kyle-mirich/repairjson/security/advisories/new) instead of opening a public issue. Include a minimal reproduction, affected versions, and the expected impact. Do not include real model payloads, credentials, or other sensitive information.

Because repair is heuristic, semantic disagreement about ambiguous input is usually a correctness issue rather than a vulnerability. Security reports should describe a concrete confidentiality, integrity, availability, or memory-safety impact.

## Processing untrusted input

Repair does not establish that data is safe or matches your schema. Set an application-level input-size limit, validate decoded types and numeric ranges, and apply normal authorization checks after parsing. The library rejects nesting beyond 128 containers with `ValueError`, but wide arrays and long strings can still consume substantial memory. Report process crashes or ways to bypass the nesting bound privately.
