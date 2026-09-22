# Releasing repairjson

The supported distribution is the Python package on PyPI. The Rust crate is an implementation detail; there is no website deployment or separate crates.io release.

## Platforms

Release CI builds a CPython 3.8+ stable-ABI wheel for each target below, plus a source distribution:

| OS / libc | Architectures |
| --- | --- |
| Linux, glibc 2.17+ | x86_64, i686, aarch64, armv7l, ppc64le, s390x |
| Linux, musl 1.2+ | x86_64, i686, aarch64, armv7l |
| Windows | x86_64, x86, ARM64 |
| macOS | x86_64, ARM64 |

Cross-compiled Linux wheels are build-checked. Native Windows/macOS wheels, Linux x86_64, and Alpine x86_64 run the Python test suite after installation. The Python matrix also tests 3.8, 3.10, 3.12, and 3.14. A source-distribution job installs the tarball and tests the resulting extension.

The `abi3` wheels target standard CPython, not free-threaded builds or PyPy. Unsupported platforms may build from source with Rust 1.88+, Python development headers, and a C linker.

## Before tagging

1. Update `package.version` in `Cargo.toml`. Run `cargo check` to synchronize `Cargo.lock`; Python metadata derives its version from Cargo.
2. Add the dated version entry and migration notes to `CHANGELOG.md`.
3. Run the checks in [CONTRIBUTING.md](../CONTRIBUTING.md), build the wheel and source distribution, and validate with `twine check --strict`.
4. Run `python scripts/check_release.py` using Python 3.11+. It checks Cargo/lockfile/changelog consistency and, in CI, tag consistency.
5. Commit and push `main`. Wait for the complete CI run to pass before creating a release tag.
6. Inspect release notes with `python scripts/release_notes.py`.

Use a tag matching the package version exactly, such as `v0.2.0`:

```bash
git tag -a v0.2.0 -m "Release 0.2.0"
git push origin v0.2.0
```

Replace the version above for subsequent releases. Never retarget a published version tag or overwrite published distributions.

## Publication

The existing `.github/workflows/CI.yml` is the PyPI trusted-publisher entry point. Retain its filename and the `pypi` environment unless updating the publisher configuration in PyPI too.

A version tag triggers all checks and platform builds. Only after all required jobs succeed does the release job:

1. Download the `wheels-*` artifacts from that run.
2. Validate tag/version metadata and every distribution with Twine.
3. Generate build-provenance attestations.
4. Publish to PyPI using GitHub OIDC, without a stored upload token.
5. Create a GitHub Release containing the changelog notes and built distributions.

A manually dispatched branch build runs validation only. It does not publish. Actions are pinned to commit SHAs, with Dependabot maintaining update proposals. The build uses `Cargo.lock`, an explicit Maturin version, and explicit Linux compatibility targets.

## Verification and recovery

After publication, check the PyPI version and GitHub Release, then install the exact version from PyPI into a fresh environment and run the tests. Confirm the release artifacts correspond to the tag's commit.

For build failures, fix the issue and verify CI before tagging a new version. If PyPI publication succeeded but GitHub Release creation failed, recover only the GitHub Release from the original run's artifacts; do not repeat an upload blindly. If the PyPI environment requests approval or rejects its OIDC identity, a maintainer must fix that account configuration. Never work around it by committing a token.
