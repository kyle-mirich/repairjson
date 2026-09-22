"""Fail before publishing when a release tag and the package version disagree."""

import os
import tomllib
from pathlib import Path

manifest = tomllib.loads(Path("Cargo.toml").read_text())
version = manifest["package"]["version"]
lock = tomllib.loads(Path("Cargo.lock").read_text())
locked = next(package["version"] for package in lock["package"] if package["name"] == "repairjson")
if version != locked:
    raise SystemExit(f"Cargo.toml version {version} differs from Cargo.lock version {locked}")
ref = os.environ.get("GITHUB_REF", "")
if ref.startswith("refs/tags/") and ref != f"refs/tags/v{version}":
    raise SystemExit(f"Tag {ref} does not match package version {version}")
if f"## [{version}]" not in Path("CHANGELOG.md").read_text():
    raise SystemExit(f"CHANGELOG.md is missing a release entry for {version}")
print(f"Release metadata is consistent: {version}")
