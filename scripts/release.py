#!/usr/bin/env python3
"""
One-command release: bump version, optional changelog, commit, tag, push.
Usage: python scripts/release.py [patch | minor | major] [--no-changelog] [--dry-run]
Example: python scripts/release.py patch
         python scripts/release.py minor --dry-run
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    cwd = cwd or REPO_ROOT
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(r.stderr or r.stdout, file=sys.stderr)
        sys.exit(r.returncode)
    return r


def main() -> int:
    parser = argparse.ArgumentParser(description="Release: bump, changelog, commit, tag, push")
    parser.add_argument(
        "bump",
        choices=["patch", "minor", "major"],
        help="Bump type: patch (2.4.0->2.4.1), minor (2.4.0->2.5.0), major (2.4.0->3.0.0)",
    )
    parser.add_argument("--no-changelog", action="store_true", help="Skip conventional-changelog update")
    parser.add_argument("--dry-run", action="store_true", help="Only print what would be done, do not commit/push")
    args = parser.parse_args()

    # Require main branch
    r = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], check=False)
    if r.returncode != 0 or r.stdout.strip() != "main":
        print("Error: release must be run from branch 'main'.", file=sys.stderr)
        sys.exit(1)

    # 1) Bump version
    print(f"Bumping version ({args.bump})...")
    run([sys.executable, str(REPO_ROOT / "scripts" / "bump_version.py"), args.bump])
    version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    tag = f"v{version}"
    print(f"Version set to {version} -> tag {tag}")

    # 2) Optional changelog
    if not args.no_changelog:
        print("Updating CHANGELOG (conventional-changelog)...")
        r = run(["npm", "run", "release:changelog"], check=False)
        if r.returncode != 0:
            print("(Changelog update skipped – run 'npm install' in repo root if needed)", file=sys.stderr)
    else:
        print("Skipping changelog (--no-changelog).")

    if args.dry_run:
        print("\n[DRY RUN] Would run:")
        print(f"  git add -A")
        print(f"  git commit -m \"chore: release {version}\"")
        print(f"  git tag {tag}")
        print(f"  git push origin main")
        print(f"  git push origin {tag}")
        return 0

    # 3) Commit
    run(["git", "add", "-A"])
    run(["git", "status", "--short"])
    run(["git", "commit", "-m", f"chore: release {version}"])

    # 4) Tag
    run(["git", "tag", tag])

    # 5) Push
    print(f"Pushing main and {tag}...")
    run(["git", "push", "origin", "main"])
    run(["git", "push", "origin", tag])

    print(f"Done. Release {tag} triggered – GitHub Actions will create the release and attach APK/installer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
