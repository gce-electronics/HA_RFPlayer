#!/usr/bin/env python3
"""Sync dependencies from pyproject.toml to manifest.json.

Excludes homeassistant from the requirements.
"""

import json
from pathlib import Path
import re
import sys


def extract_dependencies(pyproject_path: Path) -> list[str]:
    """Extract dependencies from pyproject.toml, excluding homeassistant.

    Args:
        pyproject_path: Path to pyproject.toml

    Returns:
        List of dependency strings

    """
    with open(pyproject_path) as f:
        content = f.read()

    # Extract dependencies section
    deps_match = re.search(r"dependencies\s*=\s*\[(.*?)\]", content, re.DOTALL)
    if not deps_match:
        raise ValueError("Could not find dependencies section in pyproject.toml")

    deps_section = deps_match.group(1)
    deps = []

    for line in deps_section.split(","):
        dep = line.strip().strip('"').strip("'")
        if not dep or dep.startswith("#"):
            continue
        # Skip homeassistant dependency
        if dep.startswith("homeassistant"):
            continue
        deps.append(dep)

    return deps


def create_manifest(manifest_path: Path, requirements: list[str], version: str) -> None:
    """Create manifest.json with given requirements and version."""

    manifest = {
        "domain": "rfplayer",
        "name": "GCE RF Player",
        "codeowners": ["@racletteparty", "@Aohzan"],
        "config_flow": True,
        "documentation": "https://github.com/gce-electronics/HA_RFPlayer",
        "integration_type": "hub",
        "iot_class": "local_push",
        "issue_tracker": "https://github.com/gce-electronics/HA_RFPlayer/issues",
        "loggers": ["rfplayer"],
        "requirements": requirements,
        "version": version,
    }

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")  # Add trailing newline


def main():
    """Sync dependencies from pyproject.toml to manifest.json."""

    if len(sys.argv) != 4:
        print("Usage: sync_manifest_deps.py <pyproject.toml> <manifest.json> <version>")  # noqa: T201
        sys.exit(1)

    pyproject_path = Path(sys.argv[1])
    manifest_path = Path(sys.argv[2])
    version = sys.argv[3]

    if not pyproject_path.exists():
        print(f"Error: {pyproject_path} not found")  # noqa: T201
        sys.exit(1)

    try:
        requirements = extract_dependencies(pyproject_path)
        create_manifest(manifest_path, requirements, version)
        print(f"✓ Updated {manifest_path.name}")  # noqa: T201
        print(f"  Version: {version}")  # noqa: T201
        print(f"  Requirements: {', '.join(requirements)}")  # noqa: T201
    except Exception as e:  # noqa: BLE001
        print(f"Error: {e}", file=sys.stderr)  # noqa: T201
        sys.exit(1)


if __name__ == "__main__":
    main()
