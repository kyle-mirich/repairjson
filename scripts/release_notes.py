"""Extract the current version's notes from the maintained changelog."""

import re
import tomllib
from pathlib import Path

version = tomllib.loads(Path("Cargo.toml").read_text())["package"]["version"]
changelog = Path("CHANGELOG.md").read_text()
heading = f"## [{version}]"
if heading not in changelog:
    raise SystemExit(f"Missing changelog entry for {version}")
section = changelog.split(heading, 1)[1].split("\n", 1)[1].split("\n## ", 1)[0]
section = re.sub(
    r"\]\((?!https?://|#)([^)]+)\)",
    rf"](https://github.com/kyle-mirich/repairjson/blob/v{version}/\1)",
    section,
)
print(section.strip())
print(f"\nInstall: `python -m pip install --upgrade repairjson=={version}`")
