#!/usr/bin/env python3
"""Commit and push stats.md / improvements.md so results are readable from a phone.

Only the two report files are ever staged: a tracker run must never push code,
the SQLite database or anything else the working tree happens to contain.
"""

from __future__ import annotations

import subprocess  # nosec B404 — fixed git argv, no shell
from pathlib import Path
from typing import Any

from config import repo_root, resolve_path


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 B607 — git with a fixed argv list
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=False
    )


def publish_reports(
    config: dict[str, Any],
    *,
    message: str | None = None,
    branch: str | None = None,
    dry_run: bool = False,
    root: Path | None = None,
) -> dict[str, Any]:
    """Stage, commit and push the report files. Returns a result summary."""
    root = root or repo_root()
    paths = []
    for key in ("stats_file", "improvements_file"):
        try:
            path = resolve_path(config, key)
        except Exception:  # pragma: no cover - key not configured
            continue
        if path.is_file():
            paths.append(path)
    if not paths:
        return {"pushed": False, "reason": "no report files to publish"}

    relative = []
    for path in paths:
        try:
            relative.append(str(path.resolve().relative_to(root.resolve())))
        except ValueError:
            continue  # a report configured outside the checkout is never pushed
    if not relative:
        return {"pushed": False, "reason": "report files are outside the repository"}
    add = _git(["add", "--", *relative], root)
    if add.returncode != 0:
        return {"pushed": False, "reason": f"git add failed: {add.stderr.strip()}"}

    staged = _git(["diff", "--cached", "--name-only", "--", *relative], root)
    if not staged.stdout.strip():
        return {"pushed": False, "reason": "no changes in report files", "files": relative}
    if dry_run:
        return {"pushed": False, "reason": "dry run", "files": relative}

    commit = _git(["commit", "-m", message or "chore(lowcap-tracker): refresh stats"], root)
    if commit.returncode != 0:
        return {"pushed": False, "reason": f"git commit failed: {commit.stderr.strip()}"}

    target = branch or _git(["rev-parse", "--abbrev-ref", "HEAD"], root).stdout.strip()
    push = _git(["push", "-u", "origin", target], root)
    if push.returncode != 0:
        return {
            "pushed": False,
            "reason": f"git push failed: {push.stderr.strip()}",
            "files": relative,
        }
    return {"pushed": True, "branch": target, "files": relative}
