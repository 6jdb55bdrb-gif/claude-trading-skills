#!/usr/bin/env python3
"""Invite codes and subscribers — how friends get access to the tracker bot.

Access is a property of a *chat*, not of a person: whoever controls a chat id
sees whatever the bot sends there. Three roles exist.

``admin``   the configured owner chat, plus ``telegram.admin_chat_ids`` and any
            member promoted with ``/promote``. Admins mint and revoke invites,
            remove members and (when enabled) run a cycle.
``member``  a chat that redeemed a valid invite code, plus the legacy
            ``telegram.extra_chat_ids``. Members read; they never write.
``none``    everybody else. Refused, and told to ask for an invite link.

``telegram.access_mode`` decides who may join: ``invite`` (default — a valid
code is required), ``open`` (anyone who starts the bot) or ``closed`` (nobody
new, even with a code; existing members keep their access).

An invite is a short code carried by a Telegram deep link,
``https://t.me/<bot>?start=<CODE>``. Tapping it sends ``/start <CODE>`` to the
bot, so a friend joins with one tap and never retypes anything.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

# No O/0/I/1/l: a code is read off a screen often enough to matter.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8

ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"
ROLE_NONE = "none"

STATUS_ACTIVE = "active"
STATUS_REMOVED = "removed"
STATUS_BANNED = "banned"
STATUS_BLOCKED = "blocked"  # the chat blocked the bot; kept for the record

ACCESS_MODES = ("invite", "open", "closed")

DEFAULT_USES = 1
DEFAULT_EXPIRY_DAYS = 14
MAX_USES_LIMIT = 50


def _now(now: datetime | None = None) -> datetime:
    return now or datetime.now(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def _parse(stamp: str | None) -> datetime | None:
    if not stamp:
        return None
    try:
        moment = datetime.fromisoformat(str(stamp))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _telegram(config: dict[str, Any] | None) -> dict[str, Any]:
    return (config or {}).get("telegram") or {}


def access_mode(config: dict[str, Any] | None) -> str:
    mode = str(_telegram(config).get("access_mode", "invite")).lower()
    return mode if mode in ACCESS_MODES else "invite"


# ---------------------------------------------------------------- invites


def generate_code(length: int = CODE_LENGTH) -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))


def normalize_code(code: str) -> str:
    return (code or "").strip().upper()


def invite_link(bot_username: str, code: str) -> str:
    return f"https://t.me/{(bot_username or '').lstrip('@')}?start={normalize_code(code)}"


def create_invite(
    db: Any,
    *,
    created_by: str,
    max_uses: int = DEFAULT_USES,
    expires_days: int | None = DEFAULT_EXPIRY_DAYS,
    note: str | None = None,
    now: datetime | None = None,
    code: str | None = None,
) -> dict[str, Any]:
    """Mint an invite code. Returns the stored row."""
    moment = _now(now)
    uses = max(1, min(int(max_uses or 1), MAX_USES_LIMIT))
    expires_at = _iso(moment + timedelta(days=int(expires_days))) if expires_days else None
    code = normalize_code(code) if code else generate_code()
    db.conn.execute(
        "INSERT INTO invites (code, created_at, created_by, max_uses, uses, expires_at, note) "
        "VALUES (?, ?, ?, ?, 0, ?, ?)",
        (code, _iso(moment), str(created_by), uses, expires_at, note),
    )
    db.conn.commit()
    return invite(db, code)


def invite(db: Any, code: str) -> dict[str, Any] | None:
    row = db.conn.execute(
        "SELECT * FROM invites WHERE code = ?", (normalize_code(code),)
    ).fetchone()
    return dict(row) if row else None


def list_invites(db: Any, *, include_spent: bool = True) -> list[dict[str, Any]]:
    rows = [
        dict(row) for row in db.conn.execute("SELECT * FROM invites ORDER BY created_at DESC, code")
    ]
    if include_spent:
        return rows
    return [row for row in rows if row["uses"] < row["max_uses"] and not row["revoked_at"]]


def revoke_invite(db: Any, code: str, *, now: datetime | None = None) -> bool:
    cursor = db.conn.execute(
        "UPDATE invites SET revoked_at = ? WHERE code = ? AND revoked_at IS NULL",
        (_iso(_now(now)), normalize_code(code)),
    )
    db.conn.commit()
    return cursor.rowcount > 0


def invite_state(row: dict[str, Any], *, now: datetime | None = None) -> str:
    """``usable``, ``revoked``, ``expired`` or ``spent``."""
    if row.get("revoked_at"):
        return "revoked"
    expires = _parse(row.get("expires_at"))
    if expires and _now(now) > expires:
        return "expired"
    if int(row.get("uses") or 0) >= int(row.get("max_uses") or 1):
        return "spent"
    return "usable"


# ------------------------------------------------------------- subscribers


def subscriber(db: Any, chat_id: str) -> dict[str, Any] | None:
    row = db.conn.execute("SELECT * FROM subscribers WHERE chat_id = ?", (str(chat_id),)).fetchone()
    return dict(row) if row else None


def list_subscribers(db: Any, *, active_only: bool = True) -> list[dict[str, Any]]:
    sql = "SELECT * FROM subscribers"
    params: tuple[Any, ...] = ()
    if active_only:
        sql += " WHERE status = ?"
        params = (STATUS_ACTIVE,)
    sql += " ORDER BY joined_at, chat_id"
    return [dict(row) for row in db.conn.execute(sql, params)]


def add_subscriber(
    db: Any,
    chat_id: str,
    *,
    display_name: str | None = None,
    role: str = ROLE_MEMBER,
    invited_by: str | None = None,
    invite_code: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Insert or reactivate a subscriber. Existing names are not overwritten."""
    moment = _iso(_now(now))
    db.conn.execute(
        "INSERT INTO subscribers "
        "(chat_id, display_name, role, status, joined_at, left_at, invited_by, invite_code) "
        "VALUES (?, ?, ?, ?, ?, NULL, ?, ?) "
        "ON CONFLICT (chat_id) DO UPDATE SET "
        "  status = excluded.status, left_at = NULL, "
        "  display_name = COALESCE(excluded.display_name, subscribers.display_name), "
        "  invite_code = COALESCE(excluded.invite_code, subscribers.invite_code), "
        "  invited_by = COALESCE(excluded.invited_by, subscribers.invited_by)",
        (str(chat_id), display_name, role, STATUS_ACTIVE, moment, invited_by, invite_code),
    )
    db.conn.commit()
    return subscriber(db, chat_id)


def remove_subscriber(
    db: Any, chat_id: str, *, now: datetime | None = None, banned: bool = False
) -> bool:
    status = STATUS_BANNED if banned else STATUS_REMOVED
    cursor = db.conn.execute(
        "UPDATE subscribers SET status = ?, left_at = ? WHERE chat_id = ?",
        (status, _iso(_now(now)), str(chat_id)),
    )
    db.conn.commit()
    return cursor.rowcount > 0


def mark_blocked(db: Any, chat_id: str, *, now: datetime | None = None) -> bool:
    """Record that a chat can no longer be reached (blocked or deleted)."""
    cursor = db.conn.execute(
        "UPDATE subscribers SET status = ?, left_at = ? WHERE chat_id = ?",
        (STATUS_BLOCKED, _iso(_now(now)), str(chat_id)),
    )
    db.conn.commit()
    return cursor.rowcount > 0


def set_role(db: Any, chat_id: str, role: str) -> bool:
    if role not in (ROLE_ADMIN, ROLE_MEMBER):
        raise ValueError(f"unknown role: {role}")
    cursor = db.conn.execute(
        "UPDATE subscribers SET role = ? WHERE chat_id = ?", (role, str(chat_id))
    )
    db.conn.commit()
    return cursor.rowcount > 0


def redeem_invite(
    db: Any,
    code: str,
    *,
    chat_id: str,
    display_name: str | None = None,
    config: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Redeem *code* for *chat_id*.

    Returns ``{"ok": bool, "reason": str, ...}``. Refusal reasons are
    ``closed``, ``banned``, ``unknown``, ``revoked``, ``expired`` and ``spent``.
    Redeeming twice from the same chat succeeds without burning a second use.
    """
    chat_id = str(chat_id)
    if access_mode(config) == "closed":
        return {"ok": False, "reason": "closed"}

    existing = subscriber(db, chat_id)
    if existing and existing["status"] == STATUS_BANNED:
        return {"ok": False, "reason": "banned"}
    if existing and existing["status"] == STATUS_ACTIVE:
        return {
            "ok": True,
            "reason": "already_member",
            "already_member": True,
            "subscriber": existing,
        }

    row = invite(db, code)
    if not row:
        return {"ok": False, "reason": "unknown"}
    state = invite_state(row, now=now)
    if state != "usable":
        return {"ok": False, "reason": state}

    db.conn.execute("UPDATE invites SET uses = uses + 1 WHERE code = ?", (row["code"],))
    member = add_subscriber(
        db,
        chat_id,
        display_name=display_name,
        invited_by=row["created_by"],
        invite_code=row["code"],
        now=now,
    )
    return {
        "ok": True,
        "reason": "joined",
        "already_member": False,
        "subscriber": member,
        "invite": invite(db, row["code"]),
    }


# ----------------------------------------------------------------- access


def _configured(config: dict[str, Any] | None, key: str) -> set[str]:
    return {str(item) for item in (_telegram(config).get(key) or [])}


def access_for(
    db: Any, config: dict[str, Any] | None, *, owner_chat_id: str | None, chat_id: str
) -> str:
    """Resolve a chat's role: ``admin``, ``member`` or ``none``."""
    chat_id = str(chat_id)
    if owner_chat_id is not None and chat_id == str(owner_chat_id):
        return ROLE_ADMIN
    if chat_id in _configured(config, "admin_chat_ids"):
        return ROLE_ADMIN

    row = subscriber(db, chat_id)
    if row and row["status"] == STATUS_ACTIVE:
        return ROLE_ADMIN if row["role"] == ROLE_ADMIN else ROLE_MEMBER
    if row and row["status"] in (STATUS_BANNED, STATUS_REMOVED, STATUS_BLOCKED):
        return ROLE_NONE
    if chat_id in _configured(config, "extra_chat_ids"):
        return ROLE_MEMBER
    if access_mode(config) == "open":
        return ROLE_MEMBER
    return ROLE_NONE


def broadcast_targets(
    db: Any, config: dict[str, Any] | None, *, owner_chat_id: str | None
) -> list[str]:
    """Every chat a run notification goes to, owner first, no repeats."""
    targets: list[str] = []
    seen: set[str] = set()

    def add(candidate: Any) -> None:
        value = str(candidate)
        if value and value not in seen:
            seen.add(value)
            targets.append(value)

    if owner_chat_id is not None:
        add(owner_chat_id)
    for chat_id in _configured(config, "admin_chat_ids"):
        add(chat_id)
    for chat_id in _configured(config, "extra_chat_ids"):
        add(chat_id)
    for row in list_subscribers(db):
        add(row["chat_id"])
    return targets


# ---------------------------------------------------------------- rendering


def _label(row: dict[str, Any]) -> str:
    return row.get("display_name") or f"chat {row['chat_id']}"


def format_members(rows: list[dict[str, Any]], *, owner_chat_id: str | None = None) -> str:
    """Render ``/members`` — never prints ``None``."""
    if not rows:
        return "No members yet. Mint a link with /invite and send it to a friend."
    lines = [f"<b>Members</b> — {len(rows)}"]
    for row in rows:
        marker = " · you" if owner_chat_id and row["chat_id"] == str(owner_chat_id) else ""
        role = " · admin" if row.get("role") == ROLE_ADMIN else ""
        joined = (row.get("joined_at") or "")[:10]
        since = f" · since {joined}" if joined else ""
        lines.append(f"<code>{row['chat_id']}</code> {_label(row)}{role}{since}{marker}")
    return "\n".join(lines)


def format_invites(
    rows: list[dict[str, Any]], bot_username: str, *, now: datetime | None = None
) -> str:
    """Render ``/invites`` — usable codes first, with their links."""
    usable = [row for row in rows if invite_state(row, now=now) == "usable"]
    if not usable:
        return "No usable invite links. Mint one with /invite."
    lines = [f"<b>Invite links</b> — {len(usable)} usable"]
    for row in usable:
        left = int(row["max_uses"]) - int(row["uses"])
        expires = (row.get("expires_at") or "")[:10]
        window = f" · until {expires}" if expires else " · no expiry"
        note = f" · {row['note']}" if row.get("note") else ""
        lines.append(f"{invite_link(bot_username, row['code'])}\n  {left} left{window}{note}")
    return "\n".join(lines)
