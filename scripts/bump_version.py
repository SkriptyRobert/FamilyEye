#!/usr/bin/env python3
"""
Bump project version in one place (VERSION) and propagate to all files.
Usage: python scripts/bump_version.py [VERSION | patch | minor | major]
Example: python scripts/bump_version.py 2.5.0
         python scripts/bump_version.py patch
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def read_version() -> str:
    vf = REPO_ROOT / "VERSION"
    if not vf.exists():
        return "2.4.0"
    return vf.read_text(encoding="utf-8").strip() or "2.4.0"


def parse_semver(s: str) -> tuple[int, int, int]:
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", s.strip())
    if not m:
        raise ValueError(f"Invalid semver: {s}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def format_semver(major: int, minor: int, patch: int) -> str:
    return f"{major}.{minor}.{patch}"


def bump(current: str, kind: str) -> str:
    major, minor, patch = parse_semver(current)
    if kind == "patch":
        patch += 1
    elif kind == "minor":
        minor += 1
        patch = 0
    elif kind == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        raise ValueError(f"Unknown bump kind: {kind}")
    return format_semver(major, minor, patch)


def set_version_file(version: str) -> None:
    (REPO_ROOT / "VERSION").write_text(version.strip() + "\n", encoding="utf-8")
    print(f"VERSION -> {version}")


def set_gradle_version_code(version: str) -> None:
    path = REPO_ROOT / "clients" / "android" / "app" / "build.gradle.kts"
    text = path.read_text(encoding="utf-8")
    match = re.search(r"versionCode\s*=\s*(\d+)", text)
    if not match:
        print("WARN: versionCode not found in build.gradle.kts", file=sys.stderr)
        return
    old_code = int(match.group(1))
    new_code = old_code + 1
    text = re.sub(r"versionCode\s*=\s*\d+(\s*//.*)?", f"versionCode = {new_code}  // bumped by scripts/bump_version.py", text, count=1)
    path.write_text(text, encoding="utf-8")
    print(f"clients/android/app/build.gradle.kts -> versionCode {old_code} -> {new_code}")


def set_app_config_version(version: str) -> None:
    path = REPO_ROOT / "backend" / "app" / "config" / "app-config.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = version
    path.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"backend/app/config/app-config.json -> {version}")


def set_package_json_version(path: Path, version: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = version
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"{path.relative_to(REPO_ROOT)} -> {version}")


def set_iss_version(path: Path, version: str, pattern: str = r'#define MyAppVersion "[^"]*"') -> None:
    text = path.read_text(encoding="utf-8")
    new_line = f'#define MyAppVersion "{version}"'
    if not re.search(pattern, text):
        print(f"WARN: MyAppVersion not found in {path}", file=sys.stderr)
        return
    text = re.sub(pattern, new_line, text, count=1)
    path.write_text(text, encoding="utf-8")
    print(f"{path.relative_to(REPO_ROOT)} -> {version}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bump version across the repo")
    parser.add_argument(
        "version",
        nargs=1,
        help="New version (e.g. 2.5.0) or patch | minor | major",
    )
    args = parser.parse_args()
    raw = args.version[0].strip().lower()
    if raw in ("patch", "minor", "major"):
        current = read_version()
        new_version = bump(current, raw)
        print(f"Bump {raw}: {current} -> {new_version}")
    else:
        parse_semver(raw)
        new_version = raw

    set_version_file(new_version)
    set_gradle_version_code(new_version)
    set_app_config_version(new_version)
    set_package_json_version(REPO_ROOT / "frontend" / "package.json", new_version)
    set_package_json_version(REPO_ROOT / "website" / "package.json", new_version)
    set_iss_version(REPO_ROOT / "installer" / "agent" / "setup_agent.iss", new_version)
    set_iss_version(REPO_ROOT / "installer" / "server" / "setup_server.iss", new_version)

    print(f"Done. Version set to {new_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
