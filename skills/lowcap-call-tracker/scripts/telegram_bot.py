#!/usr/bin/env python3
"""Telegram notifications and command bot for the lowcap call tracker.

Two halves, both optional and both off without credentials:

1. **Push** — ``run_cycle.py`` sends a summary after every run: new calls with
   the Judge's decision, price updates, anything closed, and the statistics
   block. ``telegram.notify_when: changes`` keeps quiet runs silent.
2. **Commands** — a long-polling loop answers ``/stats``, ``/open``, ``/calls``
   and friends, so the tracker is readable from a phone without opening GitHub.

Credentials are read from the environment only and never from configuration:

    TELEGRAM_BOT_TOKEN   from @BotFather
    TELEGRAM_CHAT_ID     the chat that may command the bot (the bot answers /id)

``TELEGRAM_CHAT_ID`` may be a private chat (a positive id) or a group/supergroup
(a negative id such as ``-1001234567890``). A bot cannot join a group from an
invite link — no Bot API method exists for that — so a member has to add it to
the group; ``--list-chats`` then prints the numeric id to configure. In a group,
**every member can command the bot**, because authorization is per chat.

Only the configured chat (plus ``telegram.extra_chat_ids``) may issue commands;
every other chat gets a refusal and nothing else. ``/run`` stays disabled unless
``telegram.allow_run_command`` is set, because a cycle spends LLM budget.

CLI:
    python3 telegram_bot.py --list-chats          # print the chat ids that messaged the bot
    python3 telegram_bot.py --test                # send a "tracker is wired up" message
    python3 telegram_bot.py --send-stats          # push the statistics block now
    python3 telegram_bot.py --poll                # answer commands until stopped
    python3 telegram_bot.py --once                # drain pending commands and exit
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from call_db import KIND_ACTIVE, STATUS_OPEN, CallDatabase

from config import ConfigError, load_config, resolve_path

try:
    import requests

    HAS_REQUESTS = True
except ImportError:  # pragma: no cover - degraded path covered by tests
    HAS_REQUESTS = False

API_BASE = "https://api.telegram.org"
TELEGRAM_HARD_LIMIT = 4096


class TelegramError(RuntimeError):
    """Raised when the Telegram API rejects a request or is unreachable."""


class TelegramDisabled(RuntimeError):
    """Raised when Telegram is switched off or has no credentials."""


def escape_html(text: Any) -> str:
    """Escape the three characters Telegram's HTML parse mode reserves."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_INVITE_LINK_RE = re.compile(r"(?:https?://)?t\.me/(?:\+|joinchat/)", re.IGNORECASE)
_PUBLIC_LINK_RE = re.compile(r"(?:https?://)?t\.me/([A-Za-z][A-Za-z0-9_]{3,31})/?$", re.IGNORECASE)
_USERNAME_RE = re.compile(r"^@[A-Za-z][A-Za-z0-9_]{3,31}$")
_NUMERIC_ID_RE = re.compile(r"^-?\d{1,20}$")  # any numeric id; Telegram validates the value


def normalize_chat_id(raw: str) -> str:
    """Validate ``TELEGRAM_CHAT_ID`` and normalize what is accepted.

    Accepted: a numeric id (``4242``), a group/supergroup id (``-1001234567890``),
    an ``@username`` for a public channel or group, or a ``t.me/username`` link,
    which is reduced to ``@username``.

    Rejected with guidance: a **private invite link** (``t.me/+hash`` or the older
    ``t.me/joinchat/hash``). The hash is a server-side token, not an encoded chat
    id — there is no offline conversion, and the Bot API has no method to resolve
    one, so the id has to be discovered after the bot is in the chat.
    """
    value = (raw or "").strip()
    if not value:
        raise TelegramDisabled("TELEGRAM_CHAT_ID is not set")
    if _INVITE_LINK_RE.match(value):
        raise TelegramDisabled(
            "TELEGRAM_CHAT_ID looks like a private invite link. A bot cannot join "
            "from an invite link and the link does not encode a chat id. Add the "
            "bot to the chat (Add members -> @yourbot), post /id@yourbot there, "
            "run 'telegram_bot.py --list-chats', and use the numeric id it prints "
            "(group ids are negative)."
        )
    public = _PUBLIC_LINK_RE.match(value)
    if public:
        return f"@{public.group(1)}"
    if _USERNAME_RE.match(value) or _NUMERIC_ID_RE.match(value):
        return value
    raise TelegramDisabled(
        f"TELEGRAM_CHAT_ID {value!r} is not a chat id. Expected a number such as "
        "4242, a group id such as -1001234567890, or @username for a public chat. "
        "Run 'telegram_bot.py --list-chats' to see the ids the bot can reach."
    )


def credentials(config: dict[str, Any]) -> tuple[str, str]:
    """Return ``(token, chat_id)`` from the environment.

    Raises ``TelegramDisabled`` when Telegram is off or either value is absent —
    callers treat that as "skip notifications", never as a run failure.
    """
    if not (config.get("telegram") or {}).get("enabled", False):
        raise TelegramDisabled("telegram.enabled is false")
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token:
        raise TelegramDisabled("TELEGRAM_BOT_TOKEN is not set")
    return token, normalize_chat_id(chat_id)


def split_message(text: str, limit: int = 3900) -> list[str]:
    """Split *text* into Telegram-sized chunks, preferring line boundaries."""
    limit = max(1, min(int(limit), TELEGRAM_HARD_LIMIT))
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for line in text.split("\n"):
        while len(line) > limit:  # a single very long line still has to fit
            if current:
                chunks.append("\n".join(current))
                current, length = [], 0
            chunks.append(line[:limit])
            line = line[limit:]
        if length + len(line) + (1 if current else 0) > limit:
            chunks.append("\n".join(current))
            current, length = [], 0
        current.append(line)
        length += len(line) + (1 if len(current) > 1 else 0)
    if current:
        chunks.append("\n".join(current))
    return [chunk for chunk in chunks if chunk]


@dataclass
class TelegramClient:
    """Minimal Bot API client: ``sendMessage`` and ``getUpdates``.

    ``transport`` exists so tests (and dry runs) can drive the client without a
    network: it takes ``(method, payload)`` and returns the decoded API result.
    """

    token: str
    chat_id: str
    parse_mode: str = "HTML"
    timeout: int = 30
    max_message_chars: int = 3900
    transport: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None
    sent: list[dict[str, Any]] = field(default_factory=list)

    def _post(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self.transport is not None:
            return self.transport(method, payload)
        if not HAS_REQUESTS:
            raise TelegramError("the 'requests' package is required to reach Telegram")
        url = f"{API_BASE}/bot{self.token}/{method}"
        for attempt in range(3):
            try:
                response = requests.post(url, json=payload, timeout=self.timeout)
            except Exception as exc:  # pragma: no cover - network failure
                if attempt == 2:
                    raise TelegramError(f"{method} failed: {type(exc).__name__}: {exc}") from exc
                time.sleep(2**attempt)
                continue
            if response.status_code == 429:
                retry_after = 1
                try:
                    retry_after = int(response.json().get("parameters", {}).get("retry_after", 1))
                except Exception:  # pragma: no cover - malformed 429 body
                    pass
                time.sleep(min(retry_after, 30))
                continue
            try:
                body = response.json()
            except ValueError as exc:
                raise TelegramError(f"{method}: non-JSON response") from exc
            if not body.get("ok"):
                raise TelegramError(f"{method}: {body.get('description', 'unknown error')}")
            return body.get("result", {})
        raise TelegramError(f"{method}: rate limited after 3 attempts")

    def send_message(
        self,
        text: str,
        *,
        chat_id: str | None = None,
        silent: bool = False,
    ) -> list[dict[str, Any]]:
        """Send *text*, split across as many messages as Telegram requires."""
        results = []
        for chunk in split_message(text, self.max_message_chars):
            payload = {
                "chat_id": chat_id or self.chat_id,
                "text": chunk,
                "parse_mode": self.parse_mode,
                "disable_web_page_preview": True,
                "disable_notification": silent,
            }
            self.sent.append(payload)
            results.append(self._post("sendMessage", payload))
        return results

    def get_updates(self, offset: int | None = None, timeout: int = 50) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": timeout, "allowed_updates": ["message"]}
        if offset is not None:
            payload["offset"] = offset
        result = self._post("getUpdates", payload)
        return result if isinstance(result, list) else []


def build_client(
    config: dict[str, Any],
    *,
    transport: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
) -> TelegramClient:
    """Build a client from configuration and environment credentials."""
    token, chat_id = credentials(config)
    telegram = config["telegram"]
    return TelegramClient(
        token=token,
        chat_id=chat_id,
        max_message_chars=int(telegram.get("max_message_chars", 3900)),
        transport=transport,
    )


# ---------------------------------------------------------------- formatting


def _pnl_tag(pnl: float | None) -> str:
    if pnl is None:
        return "?"
    return f"{pnl:+.1f}%"


def format_run_notification(report: dict[str, Any], config: dict[str, Any]) -> str:
    """Render the per-run push message."""
    telegram = config.get("telegram") or {}
    session = report.get("session", {})
    price_update = report.get("price_update", {})
    new_calls = report.get("new_calls", [])
    closed = [update for update in price_update.get("updates", []) if update.get("closed")]

    takes = [call for call in new_calls if call["decision"] == "TAKE"]
    shadows = [call for call in new_calls if call["decision"] != "TAKE"]

    header = "📈 <b>Lowcap tracker</b>"
    if report.get("dry_run"):
        header += " (dry run)"
    lines = [
        header,
        f"<i>{escape_html(session.get('as_of', ''))} — {escape_html(session.get('reason', ''))}</i>",
    ]
    if not report.get("screening_ran"):
        lines.append("Screening skipped; prices updated.")

    if takes or shadows:
        lines.append("")
        lines.append(f"<b>New calls</b> — {len(takes)} TAKE / {len(shadows)} shadow")
        for call in new_calls:
            marker = "✅" if call["decision"] == "TAKE" else "⏭"
            lines.append(
                f"{marker} <b>{escape_html(call['ticker'])}</b> "
                f"{escape_html(call.get('direction') or '-')} "
                f"({escape_html(call['asset_type'])}, {escape_html(call['variant'])}) "
                f"conf {call['confidence']} · entry {call.get('entry')} · stop {call.get('stop')}"
            )
            lines.append(f"    <i>{escape_html(call.get('reason') or '')}</i>")
            if telegram.get("include_role_detail"):
                lines.extend(_role_detail_lines(report, call["ticker"]))

    open_updates = sorted(
        [update for update in price_update.get("updates", []) if not update.get("closed")],
        key=lambda item: item.get("pnl_pct") or 0,
        reverse=True,
    )
    if open_updates:
        lines.append("")
        lines.append(f"<b>Open calls</b> ({len(open_updates)})")
        for update in open_updates[:10]:
            kind = "" if update.get("kind") == KIND_ACTIVE else " · shadow"
            lines.append(
                f"• <b>{escape_html(update['ticker'])}</b> {escape_html(update['direction'])} "
                f"{update['entry_price']:.2f} → {update['price']:.2f} "
                f"<b>{_pnl_tag(update.get('pnl_pct'))}</b>{kind}"
            )
        if len(open_updates) > 10:
            lines.append(f"  …and {len(open_updates) - 10} more")
    if price_update.get("missing_prices"):
        lines.append(
            f"<i>no price for: {escape_html(', '.join(price_update['missing_prices']))}</i>"
        )

    if closed:
        lines.append("")
        lines.append("<b>Closed</b>")
        for update in closed:
            lines.append(
                f"❌ <b>{escape_html(update['ticker'])}</b> {_pnl_tag(update.get('pnl_pct'))} "
                f"— stopped out at the {price_update.get('threshold_pct')}% threshold"
            )

    if telegram.get("include_stats", True) and report.get("stats"):
        lines.append("")
        lines.append(format_stats_message(report["stats"], compact=True))

    cost = report.get("llm_cost") or {}
    if cost.get("cost_usd"):
        lines.append(
            f"<i>LLM ${cost['cost_usd']:.4f} this run · "
            f"${report.get('llm_month_to_date_usd', 0.0):.2f} of "
            f"${report.get('llm_cap_usd', 0.0):.2f} this month</i>"
        )
    for error in report.get("errors", []):
        lines.append(f"⚠️ {escape_html(error)}")
    return "\n".join(lines)


def _role_detail_lines(report: dict[str, Any], ticker: str) -> list[str]:
    for review in report.get("reviews", []):
        if review.get("ticker") != ticker:
            continue
        verdicts = review.get("verdicts", {})
        skeptic = verdicts.get("skeptic", {})
        return [
            "    <i>R {r} · T {t} · S {s} (severity) · RM {rm}</i>".format(
                r=verdicts.get("researcher", {}).get("score"),
                t=verdicts.get("technician", {}).get("score"),
                s=skeptic.get("score"),
                rm=verdicts.get("risk_manager", {}).get("score"),
            ),
            f"    <i>objection: {escape_html(skeptic.get('strongest_objection', '—'))}</i>",
        ]
    return []


def format_stats_message(stats: dict[str, Any], *, compact: bool = False) -> str:
    """Render the statistics block (compact for run pushes, full for /stats)."""
    overall = stats.get("overall", {})
    portfolio = stats.get("portfolio", {})
    take_vs_skip = stats.get("take_vs_skip", {})
    lines = [
        "<b>Stats</b>",
        f"calls {overall.get('total')} · open {overall.get('open')} · "
        f"right {overall.get('right')} · wrong {overall.get('wrong')} · "
        f"neutral {overall.get('neutral')} · hit rate {overall.get('hit_rate_pct')}%",
        f"avg PnL {overall.get('avg_pnl_pct')}% · portfolio (equal weight, TAKE) "
        f"{portfolio.get('equal_weight_pnl_pct_take_only')}%",
    ]
    best, worst = overall.get("best_call"), overall.get("worst_call")
    if best:
        lines.append(
            f"best {escape_html(best['ticker'])} {best['pnl_pct']:+.1f}% · "
            f"worst {escape_html(worst['ticker'])} {worst['pnl_pct']:+.1f}%"
            if worst
            else f"best {escape_html(best['ticker'])} {best['pnl_pct']:+.1f}%"
        )
    lines.append(
        f"TAKE {take_vs_skip.get('take', {}).get('avg_pnl_pct')}% vs shadow "
        f"{take_vs_skip.get('skip_shadow', {}).get('avg_pnl_pct')}% → "
        f"{escape_html(take_vs_skip.get('verdict', '—'))}"
    )
    if compact:
        return "\n".join(lines)

    for title, key in (
        ("By direction", "by_direction"),
        ("By asset type", "by_asset_type"),
        ("By variant", "by_variant"),
        ("By confidence", "confidence_buckets"),
    ):
        block = stats.get(key) or {}
        if not block:
            continue
        lines.append("")
        lines.append(f"<b>{title}</b>")
        for name, values in block.items():
            lines.append(
                f"• {escape_html(name)}: n={values.get('total')} "
                f"hit {values.get('hit_rate_pct')}% avg {values.get('avg_pnl_pct')}%"
            )
    roles = stats.get("role_accuracy") or {}
    if roles:
        lines.append("")
        lines.append("<b>Role accuracy</b> (skeptic: lower is better)")
        for role, values in roles.items():
            lines.append(
                f"• {escape_html(role)}: winners {values.get('avg_score_winners')} vs "
                f"{values.get('avg_score_others')} · corr {values.get('corr_score_vs_pnl')} "
                f"(n={values.get('samples')})"
            )
    return "\n".join(lines)


def format_calls_message(rows: list[Any], *, title: str, limit: int = 20) -> str:
    """Render a list of call rows (sqlite3.Row or mapping)."""
    if not rows:
        return f"<b>{escape_html(title)}</b>\n(none)"
    lines = [f"<b>{escape_html(title)}</b> ({len(rows)})"]
    for row in rows[:limit]:
        pnl = row["pnl_pct"]
        status = "open" if row["status"] == STATUS_OPEN else "closed"
        marker = "🟢" if (pnl or 0) > 0 else ("🔴" if status == "closed" else "⚪️")
        lines.append(
            f"{marker} <b>{escape_html(row['ticker'])}</b> {escape_html(row['direction'])} "
            f"{escape_html(row['kind'])} · {row['entry_price']:.2f} → "
            f"{(row['current_price'] or 0):.2f} <b>{_pnl_tag(pnl)}</b> · "
            f"{escape_html(row['screen_variant'] or '—')} · conf {row['confidence']} · {status}"
        )
    if len(rows) > limit:
        lines.append(f"…and {len(rows) - limit} more")
    return "\n".join(lines)


def format_help(config: dict[str, Any]) -> str:
    telegram = config.get("telegram") or {}
    lines = [
        "<b>Lowcap tracker bot</b>",
        "/stats — full statistics",
        "/open — open calls with live PnL",
        "/calls [n] — the most recent calls (default 10)",
        "/shadow — open shadow calls (the ones the Judge skipped)",
        "/last — what the most recent run did",
        "/id — this chat's id (for setup)",
        "/help — this message",
    ]
    if telegram.get("allow_run_command"):
        lines.insert(-2, "/run — run a full tracker cycle now")
    else:
        lines.append("<i>/run is disabled (telegram.allow_run_command)</i>")
    return "\n".join(lines)


# ------------------------------------------------------------------ commands


def authorized_chats(config: dict[str, Any], chat_id: str) -> set[str]:
    extra = (config.get("telegram") or {}).get("extra_chat_ids") or []
    return {str(chat_id), *(str(item) for item in extra)}


def parse_command(text: str) -> tuple[str, list[str]]:
    """Split ``/calls@mybot 25`` into ``("/calls", ["25"])``."""
    parts = (text or "").strip().split()
    if not parts or not parts[0].startswith("/"):
        return "", []
    command = parts[0].split("@", 1)[0].lower()
    return command, parts[1:]


def handle_command(
    command: str,
    args: list[str],
    *,
    config: dict[str, Any],
    db_path: str | Path,
    chat_id: str,
    allowed: set[str],
    run_cycle_fn: Callable[[], dict[str, Any]] | None = None,
) -> str:
    """Return the reply for one command. Unauthorized chats get a refusal."""
    telegram = config.get("telegram") or {}
    if command in {"/id", "/start"}:
        note = "" if str(chat_id) in allowed else "\n<i>This chat is not authorized.</i>"
        return f"Chat id: <code>{escape_html(chat_id)}</code>{note}"
    if str(chat_id) not in allowed:
        return "Not authorized."
    if command in {"/help", "/commands"}:
        return format_help(config)

    from stats import compute_stats  # local import: keeps --test cheap

    if command == "/run":
        if not telegram.get("allow_run_command") or run_cycle_fn is None:
            return "/run is disabled. Enable telegram.allow_run_command to use it."
        report = run_cycle_fn()
        return format_run_notification(report, config)

    with CallDatabase(db_path) as db:
        if command == "/stats":
            return format_stats_message(compute_stats(db, config))
        if command == "/open":
            rows = [row for row in db.open_calls()]
            return format_calls_message(rows, title="Open calls")
        if command == "/shadow":
            rows = [row for row in db.open_calls() if row["kind"] != KIND_ACTIVE]
            return format_calls_message(rows, title="Open shadow calls")
        if command == "/calls":
            limit = 10
            if args and args[0].isdigit():
                limit = max(1, min(int(args[0]), 50))
            rows = list(reversed(db.all_calls()))[:limit]
            return format_calls_message(rows, title="Recent calls", limit=limit)
        if command == "/last":
            runs = db.runs(limit=1)
            if not runs:
                return "No runs recorded yet."
            run = runs[0]
            return (
                f"<b>Last run</b> {escape_html(run['run_id'])}\n"
                f"started {escape_html(run['started_at'])} · "
                f"screening {'yes' if run['screening_ran'] else 'no'} "
                f"({escape_html(run['session_reason'] or '')})\n"
                f"hits {run['hits']} · reviewed {run['reviewed']} · new {run['new_calls']} "
                f"({run['new_takes']} TAKE / {run['new_shadows']} shadow) · "
                f"closed {run['closed']} · priced {run['priced']}\n"
                f"LLM ${run['llm_cost_usd'] or 0:.4f}"
            )
    return "Unknown command. Try /help."


# ------------------------------------------------------------------- polling


def load_offset(config: dict[str, Any]) -> int | None:
    try:
        path = resolve_path(config, "offset_file", section="telegram")
    except ConfigError:
        return None
    if not path.is_file():
        return None
    try:
        return int(json.loads(path.read_text(encoding="utf-8")).get("offset"))
    except (ValueError, TypeError, OSError):
        return None


def save_offset(config: dict[str, Any], offset: int) -> None:
    try:
        path = resolve_path(config, "offset_file", section="telegram")
    except ConfigError:  # pragma: no cover - offset_file always configured
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"offset": offset, "updated_at": datetime.now(timezone.utc).isoformat()}),
        encoding="utf-8",
    )


def process_updates(
    client: TelegramClient,
    updates: list[dict[str, Any]],
    *,
    config: dict[str, Any],
    db_path: str | Path,
    run_cycle_fn: Callable[[], dict[str, Any]] | None = None,
) -> int | None:
    """Answer every message update; return the next getUpdates offset."""
    allowed = authorized_chats(config, client.chat_id)
    next_offset = None
    for update in updates:
        next_offset = int(update.get("update_id", 0)) + 1
        message = update.get("message") or {}
        chat_id = str((message.get("chat") or {}).get("id", ""))
        command, args = parse_command(message.get("text", ""))
        if not command or not chat_id:
            continue
        try:
            reply = handle_command(
                command,
                args,
                config=config,
                db_path=db_path,
                chat_id=chat_id,
                allowed=allowed,
                run_cycle_fn=run_cycle_fn,
            )
        except Exception as exc:  # a bad command must not kill the poller
            reply = f"Command failed: {escape_html(f'{type(exc).__name__}: {exc}')}"
        client.send_message(reply, chat_id=chat_id)
    return next_offset


def poll_once(
    client: TelegramClient,
    *,
    config: dict[str, Any],
    db_path: str | Path,
    timeout: int = 0,
    run_cycle_fn: Callable[[], dict[str, Any]] | None = None,
) -> int:
    """One getUpdates round trip. Returns the number of updates handled."""
    offset = load_offset(config)
    updates = client.get_updates(offset=offset, timeout=timeout)
    next_offset = process_updates(
        client, updates, config=config, db_path=db_path, run_cycle_fn=run_cycle_fn
    )
    if next_offset is not None:
        save_offset(config, next_offset)
    return len(updates)


def run_poller(
    client: TelegramClient,
    *,
    config: dict[str, Any],
    db_path: str | Path,
    run_cycle_fn: Callable[[], dict[str, Any]] | None = None,
    max_rounds: int | None = None,
) -> None:  # pragma: no cover - exercised via poll_once in tests
    """Long-poll for commands until interrupted (or *max_rounds* elapse)."""
    timeout = int((config.get("telegram") or {}).get("poll_timeout_seconds", 50))
    rounds = 0
    while max_rounds is None or rounds < max_rounds:
        rounds += 1
        try:
            poll_once(
                client,
                config=config,
                db_path=db_path,
                timeout=timeout,
                run_cycle_fn=run_cycle_fn,
            )
        except TelegramError as exc:
            print(f"WARNING: {exc}", file=sys.stderr)
            time.sleep(5)


def discover_chats(client: TelegramClient) -> list[dict[str, Any]]:
    """Summarize the chats visible in pending updates, newest last.

    Non-destructive: the getUpdates offset is neither read nor written, so a
    running poller still answers the same commands. Use it to find a group's
    numeric id after adding the bot to the group.
    """
    seen: dict[str, dict[str, Any]] = {}
    for update in client.get_updates(offset=None, timeout=0):
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None:
            continue
        sender = message.get("from") or {}
        seen[str(chat_id)] = {
            "chat_id": str(chat_id),
            "type": chat.get("type", "?"),
            "title": chat.get("title") or chat.get("username") or chat.get("first_name") or "",
            "from": sender.get("username") or sender.get("first_name") or "",
            "text": (message.get("text") or "")[:60],
        }
    return list(seen.values())


def format_chat_list(chats: list[dict[str, Any]], configured: str | None = None) -> str:
    """Render ``--list-chats`` output for a terminal."""
    if not chats:
        return (
            "No pending updates.\n"
            "Send the bot a message (in a group: add the bot first, then post "
            "/id@yourbot), and run this again. If the command bot service is "
            "already running it has consumed the updates — read its reply in "
            "Telegram instead, or stop it: systemctl stop lowcap-telegram.service"
        )
    lines = [f"{'CHAT ID':>16}  {'TYPE':<10}  TITLE / FROM"]
    for chat in chats:
        marker = "  <- configured" if configured and chat["chat_id"] == str(configured) else ""
        title = chat["title"] or chat["from"]
        lines.append(f"{chat['chat_id']:>16}  {chat['type']:<10}  {title}{marker}")
    lines.append("")
    lines.append("Put the id you want into TELEGRAM_CHAT_ID in .env (group ids are negative).")
    return "\n".join(lines)


# ------------------------------------------------------------- notify helper


def notify(
    config: dict[str, Any],
    text: str,
    *,
    silent: bool = False,
    transport: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Best-effort send. Never raises: a broken bot must not fail a run."""
    try:
        client = build_client(config, transport=transport)
    except TelegramDisabled as exc:
        return {"sent": False, "reason": str(exc)}
    try:
        client.send_message(text, silent=silent)
    except TelegramError as exc:
        return {"sent": False, "reason": str(exc)}
    return {"sent": True, "messages": len(client.sent)}


def should_notify(report: dict[str, Any], config: dict[str, Any]) -> bool:
    """Apply ``telegram.notify_when``."""
    when = str((config.get("telegram") or {}).get("notify_when", "changes")).lower()
    if when == "always":
        return True
    closed = any(
        update.get("closed") for update in report.get("price_update", {}).get("updates", [])
    )
    return bool(report.get("new_calls") or closed or report.get("errors"))


def notify_run(
    report: dict[str, Any],
    config: dict[str, Any],
    *,
    transport: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Send the run summary, honouring notify_when and the quiet-run setting."""
    telegram = config.get("telegram") or {}
    if not should_notify(report, config):
        return {"sent": False, "reason": "no changes this run (telegram.notify_when=changes)"}
    quiet = not report.get("new_calls") and not any(
        update.get("closed") for update in report.get("price_update", {}).get("updates", [])
    )
    return notify(
        config,
        format_run_notification(report, config),
        silent=bool(quiet and telegram.get("silent_when_quiet", True)),
        transport=transport,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Telegram bot for the lowcap call tracker")
    parser.add_argument("--config")
    parser.add_argument("--db")
    parser.add_argument("--test", action="store_true", help="Send a connectivity test message")
    parser.add_argument(
        "--list-chats",
        action="store_true",
        help="Print the chat ids that messaged the bot (find a group's numeric id)",
    )
    parser.add_argument("--send-stats", action="store_true", help="Push the statistics block")
    parser.add_argument("--poll", action="store_true", help="Answer commands until stopped")
    parser.add_argument("--once", action="store_true", help="Drain pending commands and exit")
    parser.add_argument("--max-rounds", type=int, default=None, help="Stop after N poll rounds")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    db_path = args.db or resolve_path(config, "db_path")

    try:
        client = build_client(config)
    except TelegramDisabled as exc:
        print(f"Telegram is not configured: {exc}", file=sys.stderr)
        print(
            "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (see deploy/VPS_SETUP.md).",
            file=sys.stderr,
        )
        return 2

    if args.list_chats:
        print(format_chat_list(discover_chats(client), os.environ.get("TELEGRAM_CHAT_ID")))
        return 0

    if args.test:
        client.send_message("✅ <b>Lowcap tracker</b> is wired up.\n" + format_help(config))
        print("test message sent")
        return 0

    if args.send_stats:
        from stats import compute_stats

        with CallDatabase(db_path) as db:
            client.send_message(format_stats_message(compute_stats(db, config)))
        print("stats sent")
        return 0

    if args.once or args.poll:
        if not (config.get("telegram") or {}).get("allow_commands", True):
            print("telegram.allow_commands is false; nothing to do", file=sys.stderr)
            return 2
        run_cycle_fn = None
        if (config.get("telegram") or {}).get("allow_run_command"):

            def run_cycle_fn() -> dict[str, Any]:  # noqa: F811 - conditional definition
                from run_cycle import run_cycle

                return run_cycle(config, db_path=str(db_path))

        if args.once:
            handled = poll_once(client, config=config, db_path=db_path, run_cycle_fn=run_cycle_fn)
            print(f"handled {handled} update(s)")
            return 0
        print("polling for commands (Ctrl-C to stop)", file=sys.stderr)
        run_poller(
            client,
            config=config,
            db_path=db_path,
            run_cycle_fn=run_cycle_fn,
            max_rounds=args.max_rounds,
        )
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
