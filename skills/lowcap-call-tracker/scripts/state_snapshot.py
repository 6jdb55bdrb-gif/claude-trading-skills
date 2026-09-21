#!/usr/bin/env python3
"""Export / import the whole tracker database as one JSON document.

The tracker's value is continuity: dedupe, PnL since entry, hit rate over time.
That lives in a SQLite file, which is fine on a server with a disk but useless
wherever the working copy is recreated each run (a scheduled cloud session, a
container, a new machine).

A snapshot is plain JSON, so it survives in git, diffs readably, and carries the
history to another host — including the eventual move to a VPS, where importing
it once brings every open call and its price history along.

CLI:
    python3 state_snapshot.py --export tracker-output/state_snapshot.json
    python3 state_snapshot.py --import tracker-output/state_snapshot.json
    python3 state_snapshot.py --show   tracker-output/state_snapshot.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from call_db import CallDatabase

from config import load_config, resolve_path

SNAPSHOT_VERSION = 1
# Fixed allowlist: table names are interpolated into SQL, never user input.
# The public snapshot is committed to git, so it carries no personal data.
TABLES: tuple[str, ...] = ("calls", "role_verdicts", "price_history", "runs", "llm_usage")

# Who can read the tracker. An invite code is a shared secret and a chat id
# identifies a person, so these NEVER go in the committed snapshot — they are
# exported separately, to a gitignored file.
MEMBER_TABLES: tuple[str, ...] = ("subscribers", "invites")


class SnapshotError(RuntimeError):
    """Raised when a snapshot cannot be read or does not match the schema."""


def export_snapshot(
    db: CallDatabase,
    path: str | Path | None = None,
    *,
    tables_to_export: tuple[str, ...] = TABLES,
) -> dict[str, Any]:
    """Serialize the public tables. Writes to *path* when given; returns the document."""
    tables: dict[str, list[dict[str, Any]]] = {}
    for table in tables_to_export:
        rows = db.conn.execute(f"SELECT * FROM {table}")  # nosec B608 — fixed allowlist
        tables[table] = [dict(row) for row in rows]
    snapshot = {
        "snapshot_version": SNAPSHOT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "counts": {table: len(rows) for table, rows in tables.items()},
        "tables": tables,
    }
    if path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(snapshot, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8"
        )
    return snapshot


def load_snapshot(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.is_file():
        raise SnapshotError(f"snapshot not found: {target}")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SnapshotError(f"snapshot is not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or "tables" not in data:
        raise SnapshotError("snapshot has no 'tables' section")
    version = data.get("snapshot_version")
    if version != SNAPSHOT_VERSION:
        raise SnapshotError(
            f"snapshot version {version!r} is not supported (expected {SNAPSHOT_VERSION})"
        )
    return data


def import_snapshot(
    db: CallDatabase,
    path: str | Path,
    *,
    replace: bool = False,
    tables_to_import: tuple[str, ...] = TABLES,
) -> dict[str, Any]:
    """Load a snapshot into *db*.

    Refuses a database that already holds calls unless *replace* is set, so a
    scheduled run can import unconditionally without ever clobbering live state.
    """
    guard_table = tables_to_import[0]
    existing = db.conn.execute(
        f"SELECT COUNT(*) AS n FROM {guard_table}"  # nosec B608 — fixed allowlist
    ).fetchone()["n"]
    if existing and not replace:
        return {
            "imported": False,
            "reason": f"database already holds {existing} {guard_table} row(s)",
        }

    snapshot = load_snapshot(path)
    tables = snapshot["tables"]
    counts: dict[str, int] = {}
    with db.conn:  # one transaction: a half-imported history is worse than none
        if replace:
            for table in reversed(tables_to_import):
                db.conn.execute(f"DELETE FROM {table}")  # nosec B608 — fixed allowlist
        for table in tables_to_import:
            rows = tables.get(table) or []
            counts[table] = len(rows)
            for row in rows:
                if not isinstance(row, dict) or not row:
                    continue
                columns = ", ".join(row)
                placeholders = ", ".join("?" for _ in row)
                db.conn.execute(
                    f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})",  # nosec B608
                    tuple(row.values()),
                )
    return {
        "imported": True,
        "counts": counts,
        "exported_at": snapshot.get("exported_at"),
    }


def export_members(db: CallDatabase, path: str | Path) -> dict[str, Any]:
    """Write subscribers and invites to *path*.

    Kept out of the committed snapshot on purpose: an invite code is a shared
    secret and a chat id identifies a person. The destination belongs under
    ``state/``, which this repository does not track.
    """
    return export_snapshot(db, path, tables_to_export=MEMBER_TABLES)


def import_members(db: CallDatabase, path: str | Path, *, replace: bool = False) -> dict[str, Any]:
    """Load a member file written by :func:`export_members`."""
    return import_snapshot(db, path, replace=replace, tables_to_import=MEMBER_TABLES)


def snapshot_path(config: dict[str, Any], override: str | None = None) -> Path | None:
    """Resolve the configured snapshot path, or None when snapshots are off."""
    if override:
        return Path(override)
    if not (config.get("tracker") or {}).get("snapshot_file"):
        return None
    return resolve_path(config, "snapshot_file")


def members_path(config: dict[str, Any], override: str | None = None) -> Path | None:
    """Resolve the member file, defaulting beside the tracker's other state.

    Never inside ``tracker-output/``: that directory is committed.
    """
    if override:
        return Path(override)
    configured = (config.get("tracker") or {}).get("members_file")
    if not configured:
        return None
    return resolve_path(config, "members_file")


def describe(snapshot: dict[str, Any]) -> str:
    counts = snapshot.get("counts", {})
    calls = snapshot.get("tables", {}).get("calls", [])
    open_calls = [row for row in calls if row.get("status") == "OPEN"]
    lines = [
        f"snapshot v{snapshot.get('snapshot_version')} exported {snapshot.get('exported_at')}",
        "  " + "  ".join(f"{table}={count}" for table, count in counts.items()),
        f"  open calls: {', '.join(row['ticker'] for row in open_calls) or '(none)'}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export or import tracker state as JSON")
    parser.add_argument("--config")
    parser.add_argument("--db")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--export", metavar="PATH")
    group.add_argument("--import", dest="import_path", metavar="PATH")
    group.add_argument("--show", metavar="PATH")
    parser.add_argument(
        "--replace", action="store_true", help="Overwrite a non-empty database on import"
    )
    args = parser.parse_args(argv)

    if args.show:
        print(describe(load_snapshot(args.show)))
        return 0

    config = load_config(args.config)
    db_path = args.db or resolve_path(config, "db_path")
    with CallDatabase(db_path) as db:
        if args.export:
            snapshot = export_snapshot(db, args.export)
            print(f"exported {sum(snapshot['counts'].values())} row(s) to {args.export}")
            print(describe(snapshot))
            return 0
        try:
            result = import_snapshot(db, args.import_path, replace=args.replace)
        except SnapshotError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        if not result["imported"]:
            print(f"skipped: {result['reason']} (use --replace to overwrite)")
            return 0
        print(f"imported {sum(result['counts'].values())} row(s) from {args.import_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
