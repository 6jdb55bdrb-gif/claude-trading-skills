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

import membership as ms
from allocation import money
from call_db import KIND_ACTIVE, STATUS_EXPIRED, STATUS_OPEN, CallDatabase
from option_contract import days_to_expiry

from config import ConfigError, load_config, load_dotenv, resolve_path

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
    # The HTTP read timeout must outlast the long poll itself: getUpdates holds
    # the connection open for poll_timeout_seconds, so a shorter client timeout
    # would abort every quiet round and re-open the connection for nothing.
    poll_timeout = int(telegram.get("poll_timeout_seconds", 50))
    return TelegramClient(
        token=token,
        chat_id=chat_id,
        timeout=max(30, poll_timeout + 10),
        max_message_chars=int(telegram.get("max_message_chars", 3900)),
        transport=transport,
    )


# ---------------------------------------------------------------- formatting


def _pnl_tag(pnl: float | None) -> str:
    """Signed PnL, or an em dash when the call has never been priced."""
    if pnl is None:
        return "—"
    return f"{pnl:+.1f}%"


def _num(value: Any, spec: str = ".2f", suffix: str = "") -> str:
    """Render a number for a message; an absent value reads '—', never 'None'."""
    if value is None or value == "":
        return "—"
    try:
        return format(float(value), spec) + suffix
    except (TypeError, ValueError):
        return escape_html(value)


def _contract(row: Any, *, with_expiry: bool = True) -> str:
    """CALL/PUT with its strike and how long the contract still has to run."""
    try:
        # Never fall back to the direction: an unjudged call's direction is a
        # PnL convention, not a contract someone chose.
        instrument = row["instrument"]
        strike = row["strike"]
        expiry = row["expiry_date"]
    except (KeyError, IndexError, TypeError):
        instrument, strike, expiry = (
            row.get("instrument"),
            row.get("strike"),
            row.get("expiry_date"),
        )
    label = str(instrument or "—").upper()
    if strike:
        label += f" {_num(strike)}"
    if with_expiry and expiry:
        remaining = days_to_expiry(expiry)
        label += f" exp {escape_html(str(expiry)[:10])}"
        if remaining is not None:
            label += f" ({remaining}d)" if remaining >= 0 else " (expired)"
    return label


def _stale_note(update: dict[str, Any]) -> str:
    """Flag an open call whose price could not be refreshed this run."""
    if update.get("priced", True):
        return ""
    if update.get("stale_source"):
        return " ⏸ <i>held: source behind</i>"
    days = update.get("stale_days")
    if days:
        return f" ⏸ <i>no price for {days}d</i>"
    return " ⏸ <i>no price</i>"


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
                f"{_contract(call)} "
                f"({escape_html(call['asset_type'])}, {escape_html(call['variant'])}) "
                f"conf {call['confidence']} · entry {_num(call.get('entry'))} "
                f"· stop {_num(call.get('stop'))}"
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
            age = update.get("age_days")
            age_note = f" · {age}d" if age else ""
            remaining = update.get("days_to_expiry")
            expiry_note = ""
            if remaining is not None:
                expiry_note = f" · {remaining}d to expiry" + (" ⏳" if remaining <= 7 else "")
            lines.append(
                f"• <b>{escape_html(update['ticker'])}</b> "
                f"{str(update.get('instrument') or update['direction']).upper()} "
                f"{_num(update['entry_price'])} → {_num(update['price'])} "
                f"<b>{_pnl_tag(update.get('pnl_pct'))}</b>{kind}{expiry_note}{age_note}"
                f"{_stale_note(update)}"
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
            if update.get("expired"):
                verdict = "RIGHT" if (update.get("pnl_pct") or 0) > 0 else "WRONG"
                lines.append(
                    f"⌛ <b>{escape_html(update['ticker'])}</b> "
                    f"{str(update.get('instrument') or '').upper()} "
                    f"{_pnl_tag(update.get('pnl_pct'))} — contract expired "
                    f"{escape_html(str(update.get('expiry_date') or '')[:10])} ({verdict})"
                )
            else:
                lines.append(
                    f"❌ <b>{escape_html(update['ticker'])}</b> {_pnl_tag(update.get('pnl_pct'))} "
                    f"— stopped out at the "
                    f"{_num(price_update.get('threshold_pct'), '.0f')}% threshold"
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


def _signed(value: Any) -> str:
    """A percentage with an explicit sign; an em dash when there is none."""
    if value is None:
        return "—"
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "—"


def format_stats_message(stats: dict[str, Any], *, compact: bool = False) -> str:
    """Render the statistics block (compact for run pushes, full for /stats)."""
    overall = stats.get("overall", {})
    portfolio = stats.get("portfolio", {})
    account = stats.get("account", {})
    take_vs_skip = stats.get("take_vs_skip", {})
    if not overall.get("total"):
        return (
            "<b>Stats</b>\nNo calls yet — the tracker has not opened one. "
            "Every screened candidate becomes a call or a shadow call, so this "
            "fills up on the first run that finds something."
        )

    lines = [
        "<b>Stats</b>",
        f"calls {overall.get('total')} · open {overall.get('open')} · "
        f"right {overall.get('right')} · wrong {overall.get('wrong')} · "
        f"neutral {overall.get('neutral')} · hit rate "
        f"{_num(overall.get('hit_rate_pct'), '.1f', '%')}",
        f"<b>Portfolio {money(account.get('portfolio_value_usd'))}</b> "
        f"({_signed(account.get('total_return_pct'))} on "
        f"{money(account.get('account_usd'))})",
        f"{account.get('allocated_pct', 0)}% allocated · cash {money(account.get('cash_usd'))}",
        f"<b>Total PnL {_signed(portfolio.get('total_pnl_pct'))}</b> "
        f"<i>(equal weight, all {portfolio.get('calls_counted', 0)} calls)</i>",
        f"avg PnL {_num(overall.get('avg_pnl_pct'), '.2f', '%')} · portfolio "
        f"(equal weight, TAKE) "
        f"{_num(portfolio.get('equal_weight_pnl_pct_take_only'), '.2f', '%')}",
    ]
    best, worst = overall.get("best_call"), overall.get("worst_call")
    if best:
        line = f"best {escape_html(best['ticker'])} {_pnl_tag(best.get('pnl_pct'))}"
        if worst and worst.get("ticker") != best.get("ticker"):
            line += f" · worst {escape_html(worst['ticker'])} {_pnl_tag(worst.get('pnl_pct'))}"
        lines.append(line)
    take_block = take_vs_skip.get("take", {})
    shadow_block = take_vs_skip.get("skip_shadow", {})
    lines.append(
        f"TAKE {_num(take_block.get('avg_pnl_pct'), '.2f', '%')} "
        f"(n={take_block.get('total', 0)}) vs shadow "
        f"{_num(shadow_block.get('avg_pnl_pct'), '.2f', '%')} "
        f"(n={shadow_block.get('total', 0)}) → "
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
            if not values.get("total"):
                continue
            lines.append(
                f"• {escape_html(name)}: n={values.get('total')} "
                f"hit {_num(values.get('hit_rate_pct'), '.1f', '%')} "
                f"avg {_num(values.get('avg_pnl_pct'), '.2f', '%')}"
            )
    roles = stats.get("role_accuracy") or {}
    if roles:
        lines.append("")
        lines.append("<b>Role accuracy</b> (skeptic: lower is better)")
        for role, values in roles.items():
            lines.append(
                f"• {escape_html(role)}: winners {_num(values.get('avg_score_winners'), '.1f')} "
                f"vs {_num(values.get('avg_score_others'), '.1f')} · corr "
                f"{_num(values.get('corr_score_vs_pnl'), '.2f')} (n={values.get('samples', 0)})"
            )
    return "\n".join(lines)


def format_calls_message(rows: list[Any], *, title: str, limit: int = 20) -> str:
    """Render a list of call rows (sqlite3.Row or mapping)."""
    if not rows:
        return f"<b>{escape_html(title)}</b>\n(none)"
    lines = [f"<b>{escape_html(title)}</b> ({len(rows)})"]
    for row in rows[:limit]:
        pnl = row["pnl_pct"]
        status = (
            "open"
            if row["status"] == STATUS_OPEN
            else ("expired" if row["status"] == STATUS_EXPIRED else "closed")
        )
        marker = "🟢" if (pnl or 0) > 0 else ("🔴" if status != "open" else "⚪️")
        lines.append(
            f"{marker} <b>{escape_html(row['ticker'])}</b> {_contract(row, with_expiry=False)} "
            f"{escape_html(row['kind'])} · {_num(row['entry_price'])} → "
            f"{_num(row['current_price'])} <b>{_pnl_tag(pnl)}</b> · "
            f"{escape_html(row['screen_variant'] or '—')} · conf "
            f"{row['confidence'] if row['confidence'] is not None else '—'} · {status}"
        )
    if len(rows) > limit:
        lines.append(f"…and {len(rows) - limit} more")
    return "\n".join(lines)


# The command menu Telegram shows in the app. Kept in one place so the menu, the
# /help reply and the documentation cannot drift apart.
BOT_COMMANDS: tuple[tuple[str, str], ...] = (
    ("report", "The whole picture: open calls, statistics, last run"),
    ("stats", "Full statistics: hit rate, PnL, breakdowns, per-role accuracy"),
    ("open", "Open calls with live PnL"),
    ("calls", "Recent calls — /calls 20 for more"),
    ("shadow", "Open shadow calls (the ones the Judge skipped)"),
    ("call", "Every role's verdict for one ticker — /call SDEV"),
    ("last", "What the most recent run did"),
    ("id", "This chat's id (setup helper)"),
    ("stop", "Leave the tracker — no further updates"),
    ("help", "Show the command list"),
)
ADMIN_COMMANDS: tuple[tuple[str, str], ...] = (
    ("invite", "Mint an invite link — /invite [uses] [days]"),
    ("invites", "The invite links that still work"),
    ("revoke", "Kill an invite link — /revoke CODE"),
    ("members", "Who has access"),
    ("remove", "Take access away — /remove CHAT_ID"),
)
BOT_SHORT_DESCRIPTION = (
    "Screens US low-cap stocks and ETFs, argues each candidate through five "
    "roles, and tracks every call's PnL."
)
BOT_DESCRIPTION = (
    "I screen US low caps and ETFs for explosive moves every 4 hours, run each "
    "hit past a Researcher, Technician, Skeptic, Risk Manager and Judge, then "
    "track the calls I take AND the ones I skip so you can see whether the Judge "
    "adds value.\n\n"
    "Send /stats for hit rate and PnL, /open for live positions, /calls for "
    "recent calls, /help for everything."
)


def setup_profile(
    client: TelegramClient,
    *,
    config: dict[str, Any] | None = None,
    include_run: bool | None = None,
) -> dict[str, Any]:
    """Publish the command menu, description and about text to Telegram.

    Idempotent: re-running after editing ``BOT_COMMANDS`` republishes the menu.
    ``/run`` only appears in the menu when it is actually enabled.
    """
    if include_run is None:
        include_run = bool((config or {}).get("telegram", {}).get("allow_run_command"))
    commands = [{"command": name, "description": text} for name, text in BOT_COMMANDS]
    admin_commands = commands[:-1] + [
        {"command": name, "description": text} for name, text in ADMIN_COMMANDS
    ]
    if include_run:
        admin_commands.append({"command": "run", "description": "Run a tracker cycle now"})
    admin_commands.append(commands[-1])

    results = {
        "commands": client._post("setMyCommands", {"commands": commands}),
        "description": client._post("setMyDescription", {"description": BOT_DESCRIPTION}),
        "short_description": client._post(
            "setMyShortDescription", {"short_description": BOT_SHORT_DESCRIPTION}
        ),
    }
    # Admin chats see the invite commands; members never do, so nobody is
    # tempted by a button that would only refuse them.
    admin_chats = [str(client.chat_id)] + [
        str(item) for item in ((config or {}).get("telegram", {}).get("admin_chat_ids") or [])
    ]
    scoped = 0
    for admin_chat in dict.fromkeys(admin_chats):
        try:
            client._post(
                "setMyCommands",
                {
                    "commands": admin_commands,
                    "scope": {"type": "chat", "chat_id": admin_chat},
                },
            )
            scoped += 1
        except TelegramError:  # a group the bot has since left must not fail setup
            continue
    return {"published": len(commands), "admin_scopes": scoped, "results": results}


def format_report_message(db: CallDatabase, config: dict[str, Any]) -> str:
    """The whole picture in one message: open calls, statistics, last run."""
    from stats import compute_stats

    open_rows = list(db.open_calls())
    active = [row for row in open_rows if row["kind"] == KIND_ACTIVE]
    shadow = [row for row in open_rows if row["kind"] != KIND_ACTIVE]
    lines = ["📋 <b>Tracker report</b>", ""]

    if open_rows:
        lines.append(f"<b>Open</b> — {len(active)} active / {len(shadow)} shadow")
        for row in sorted(open_rows, key=lambda item: item["pnl_pct"] or 0, reverse=True):
            tag = "" if row["kind"] == KIND_ACTIVE else " · shadow"
            lines.append(
                f"• <b>{escape_html(row['ticker'])}</b> {_contract(row)} "
                f"{_num(row['entry_price'])} → {_num(row['current_price'])} "
                f"<b>{_pnl_tag(row['pnl_pct'])}</b>{tag} · "
                f"{escape_html(row['screen_variant'] or '—')}"
            )
    else:
        lines.append("<b>Open</b> — none")

    closed = [row for row in db.all_calls() if row["status"] != STATUS_OPEN]
    if closed:
        lines.append("")
        lines.append(f"<b>Closed</b> — {len(closed)} stopped out at the threshold")
        for row in closed[-5:]:
            lines.append(
                f"• <b>{escape_html(row['ticker'])}</b> {_pnl_tag(row['pnl_pct'])} "
                f"· {escape_html(row['screen_variant'] or '—')}"
            )

    lines.append("")
    lines.append(format_stats_message(compute_stats(db, config), compact=True))

    runs = db.runs(limit=1)
    if runs:
        run = runs[0]
        lines.append("")
        lines.append(
            f"<i>last run {escape_html(run['started_at'])} · "
            f"screening {'yes' if run['screening_ran'] else 'no'} · "
            f"{run['new_calls'] or 0} new · {run['closed'] or 0} closed</i>"
        )
    return "\n".join(lines)


def format_call_detail(db: CallDatabase, ticker: str) -> str:
    """Every role's verdict for one ticker — why the call was taken or skipped."""
    ticker = ticker.strip().upper()
    row = db.open_call_for(ticker)
    if row is None:
        matches = [item for item in db.all_calls() if item["ticker"] == ticker]
        if not matches:
            return f"No call for <b>{escape_html(ticker)}</b>. Try /calls to see recent ones."
        row = matches[-1]

    verdicts = db.verdicts_for(row["id"])
    researcher = verdicts.get("researcher", {})
    technician = verdicts.get("technician", {})
    skeptic = verdicts.get("skeptic", {})
    risk = verdicts.get("risk_manager", {})
    judge = verdicts.get("judge", {})
    status = "open" if row["status"] == STATUS_OPEN else "closed"

    lines = [
        f"🔍 <b>{escape_html(row['ticker'])}</b> — {escape_html(row['judge_decision'])} "
        f"({row['confidence']}) · {escape_html(row['kind'])} · {status}",
        f"<i>{escape_html(row['screen_variant'] or '—')} · called "
        f"{escape_html(str(row['call_date'])[:16])}</i>",
        "",
        f"<b>contract:</b> {_contract(row)}",
        f"entry {_num(row['entry_price'])} → {_num(row['current_price'])} "
        f"<b>{_pnl_tag(row['pnl_pct'])}</b> · stop {_num(row['stop_price'])} "
        f"· target {_num(row['target_price'])}",
        "",
        f"<b>Researcher {_num(researcher.get('score'), '.1f')}</b> — "
        f"{escape_html(researcher.get('catalyst_type') or '—')}: "
        f"{escape_html(researcher.get('catalyst_summary') or '—')}",
        f"<b>Technician {_num(technician.get('score'), '.1f')}</b> — "
        f"{escape_html(technician.get('trend') or '—')}, "
        f"{escape_html(technician.get('volume_pattern') or '—')}, "
        f"{_num(technician.get('extension_pct_sma20'), '.0f', '%')} above SMA20",
        f"<b>Skeptic {_num(skeptic.get('score'), '.1f')}</b> (severity) — "
        f"{escape_html(skeptic.get('strongest_objection') or '—')}",
        f"<b>Risk {_num(risk.get('score'), '.1f')}</b> — "
        f"{escape_html(risk.get('instrument') or risk.get('direction') or '—')}, "
        f"{escape_html(risk.get('expiry_setup') or '—')} horizon, "
        f"{escape_html(risk.get('stop_basis') or '—')} stop",
        "",
        f"<b>Judge:</b> {escape_html(judge.get('reason') or row['judge_reason'] or '—')}",
        *([f"<i>{escape_html(judge['reasoning'])}</i>"] if judge.get("reasoning") else []),
        *(
            [
                "<i>catalyst penalty −{points} ({before} → {after})</i>".format(
                    points=judge["catalyst_penalty"]["points"],
                    before=judge["catalyst_penalty"]["confidence_before"],
                    after=judge["catalyst_penalty"]["confidence_after"],
                )
            ]
            if judge.get("catalyst_penalty")
            else []
        ),
    ]
    answer = judge.get("skeptic_answer")
    if answer:
        label = (
            "objection answered"
            if judge.get("skeptic_objections_answered")
            else "objection NOT answered"
        )
        lines.append(f"<i>{label}: {escape_html(answer)}</i>")
    if judge.get("gate_overrides"):
        lines.append("<i>gate: " + escape_html("; ".join(judge["gate_overrides"])) + "</i>")
    return "\n".join(lines)


def format_help(config: dict[str, Any], *, role: str = ms.ROLE_ADMIN) -> str:
    telegram = config.get("telegram") or {}
    lines = [
        "<b>Lowcap tracker bot</b>",
        "/report — the whole picture: open calls, stats, last run",
        "/stats — full statistics",
        "/open — open calls with live PnL",
        "/calls [n] — the most recent calls (default 10)",
        "/shadow — open shadow calls (the ones the Judge skipped)",
        "/call TICKER — every role's verdict for one call",
        "/last — what the most recent run did",
        "/id — this chat's id (for setup)",
        "/stop — leave the tracker",
        "/help — this message",
    ]
    if role == ms.ROLE_ADMIN:
        lines += [
            "",
            "<b>Admin</b>",
            "/invite [uses] [days] [note] — mint an invite link for a friend",
            "/invites — the links that still work",
            "/revoke CODE — kill a link",
            "/members — who has access",
            "/remove CHAT_ID [ban] — take access away",
            "/promote CHAT_ID — make a member an admin",
        ]
        if telegram.get("allow_run_command"):
            lines.append("/run — run a full tracker cycle now")
        else:
            lines.append("<i>/run is disabled (telegram.allow_run_command)</i>")
    return "\n".join(lines)


# ------------------------------------------------------------------ commands


_BOT_USERNAME: str | None = None


def bot_username(config: dict[str, Any] | None = None) -> str:
    """The bot's @name, asked once and cached. Empty when it cannot be read."""
    global _BOT_USERNAME
    if _BOT_USERNAME is not None:
        return _BOT_USERNAME
    try:
        client = build_client(config or {})
        _BOT_USERNAME = str((client._post("getMe", {}) or {}).get("username") or "")
    except (TelegramDisabled, TelegramError):
        _BOT_USERNAME = ""
    return _BOT_USERNAME


def parse_command(text: str) -> tuple[str, list[str]]:
    """Split ``/calls@mybot 25`` into ``("/calls", ["25"])``."""
    parts = (text or "").strip().split()
    if not parts or not parts[0].startswith("/"):
        return "", []
    command = parts[0].split("@", 1)[0].lower()
    return command, parts[1:]


def _join_hint(config: dict[str, Any]) -> str:
    """What a chat without access is told. Never leaks tracker content."""
    if ms.access_mode(config) == "closed":
        return "This bot is closed to new members."
    return (
        "Not authorized. This bot is invite-only — ask its owner for an "
        "invite link, then tap it or send <code>/start YOURCODE</code>."
    )


REDEEM_REFUSALS = {
    "unknown": "That invite code is not one of mine. Ask for a fresh invite link.",
    "expired": "That invite link has expired. Ask for a fresh one.",
    "spent": "That invite link has already been used up. Ask for a fresh one.",
    "revoked": "That invite link was revoked. Ask for a fresh one.",
    "banned": "This chat was removed from the tracker.",
    "closed": "This bot is closed to new members.",
}


def format_welcome(config: dict[str, Any], *, role: str, returning: bool = False) -> str:
    opening = "<b>Welcome back.</b>" if returning else "<b>Welcome to the Lowcap tracker.</b>"
    body = (
        "Every 4 hours I screen US low caps and ETFs, argue each candidate through "
        "five roles, and track the calls — the ones taken AND the ones skipped.\n\n"
        "Nothing here is advice: these are small, thin, violent stocks, and the "
        "record is published so you can judge it for yourself."
    )
    return f"{opening}\n{body}\n\n{format_help(config, role=role)}"


def _invite_reply(db: Any, config: dict[str, Any], args: list[str], chat_id: str) -> str:
    telegram = config.get("telegram") or {}
    uses = int(telegram.get("invite_uses", ms.DEFAULT_USES))
    days: int | None = int(telegram.get("invite_expiry_days", ms.DEFAULT_EXPIRY_DAYS))
    if args and args[0].isdigit():
        uses = int(args[0])
    if len(args) > 1 and args[1].isdigit():
        days = int(args[1]) or None
    note = " ".join(args[2:]) if len(args) > 2 else None
    row = ms.create_invite(db, created_by=chat_id, max_uses=uses, expires_days=days, note=note)
    username = bot_username(config)
    window = f"expires in {days} day(s)" if days else "never expires"
    if not username:
        return (
            f"Invite code <code>{row['code']}</code> — {uses} use(s), {window}.\n"
            "Tell your friend to send the bot <code>/start "
            f"{row['code']}</code>."
        )
    link = ms.invite_link(username, row["code"])
    return (
        f"<b>Invite link</b> — {uses} use(s), {window}\n"
        f"{link}\n\n"
        "Send that to a friend. One tap adds them; they can read the calls and "
        "the stats, and nothing else."
    )


def handle_command(
    command: str,
    args: list[str],
    *,
    config: dict[str, Any],
    db_path: str | Path,
    chat_id: str,
    owner_chat_id: str | None = None,
    display_name: str | None = None,
    run_cycle_fn: Callable[[], dict[str, Any]] | None = None,
) -> str:
    """Return the reply for one command, enforcing the caller's role."""
    telegram = config.get("telegram") or {}
    chat_id = str(chat_id)

    from stats import compute_stats  # local import: keeps --test cheap

    with CallDatabase(db_path) as db:
        role = ms.access_for(db, config, owner_chat_id=owner_chat_id, chat_id=chat_id)
        is_owner = owner_chat_id is not None and chat_id == str(owner_chat_id)
        is_admin = role == ms.ROLE_ADMIN

        if command == "/id":
            note = "" if role != ms.ROLE_NONE else "\n<i>This chat has no access.</i>"
            return f"Chat id: <code>{escape_html(chat_id)}</code> · {role}{note}"

        if command == "/start":
            if role != ms.ROLE_NONE:
                if args:
                    ms.add_subscriber(db, chat_id, display_name=display_name, role=role)
                return format_welcome(config, role=role, returning=True)
            code = args[0] if args else ""
            if not code and ms.access_mode(config) == "open":
                ms.add_subscriber(db, chat_id, display_name=display_name)
                return format_welcome(config, role=ms.ROLE_MEMBER)
            if not code:
                return _join_hint(config)
            result = ms.redeem_invite(
                db, code, chat_id=chat_id, display_name=display_name, config=config
            )
            if not result["ok"]:
                return REDEEM_REFUSALS.get(result["reason"], _join_hint(config))
            return format_welcome(config, role=ms.ROLE_MEMBER)

        if role == ms.ROLE_NONE:
            return _join_hint(config)

        if command in {"/help", "/commands"}:
            return format_help(config, role=role)

        if command == "/stop":
            if is_owner:
                return "You are the owner — /stop would silence your own tracker."
            ms.remove_subscriber(db, chat_id)
            return (
                "Removed. You will get no further updates. Tap your invite link "
                "again (or ask for a new one) to come back."
            )

        # ------------------------------------------------------- admin only
        admin_commands = {"/invite", "/invites", "/revoke", "/members", "/remove", "/promote"}
        if command in admin_commands or command == "/run":
            if not is_admin:
                return "That command is for admins only."

        if command == "/invite":
            return _invite_reply(db, config, args, chat_id)
        if command == "/invites":
            return ms.format_invites(ms.list_invites(db), bot_username(config))
        if command == "/revoke":
            if not args:
                return "Usage: /revoke CODE — see /invites for the codes."
            done = ms.revoke_invite(db, args[0])
            return "Revoked." if done else "No usable invite with that code."
        if command == "/members":
            return ms.format_members(ms.list_subscribers(db), owner_chat_id=owner_chat_id)
        if command == "/remove":
            if not args:
                return "Usage: /remove CHAT_ID — see /members for the ids."
            target = str(args[0])
            if owner_chat_id is not None and target == str(owner_chat_id):
                return "The owner chat cannot be removed."
            done = ms.remove_subscriber(db, target, banned="ban" in args[1:])
            return f"Removed {escape_html(target)}." if done else "No member with that id."
        if command == "/promote":
            if not args:
                return "Usage: /promote CHAT_ID — see /members for the ids."
            done = ms.set_role(db, str(args[0]), ms.ROLE_ADMIN)
            return "Promoted to admin." if done else "No member with that id."

        if command == "/run":
            if not telegram.get("allow_run_command") or run_cycle_fn is None:
                return "/run is disabled. Enable telegram.allow_run_command to use it."
            report = run_cycle_fn()
            return format_run_notification(report, config)

        # ------------------------------------------------------ read commands
        if command == "/report":
            return format_report_message(db, config)
        if command == "/call":
            if not args:
                return "Usage: /call TICKER — for example <code>/call SDEV</code>"
            return format_call_detail(db, args[0])
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
    next_offset = None
    for update in updates:
        next_offset = int(update.get("update_id", 0)) + 1
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id", ""))
        command, args = parse_command(message.get("text", ""))
        if not command or not chat_id:
            continue
        sender = message.get("from") or {}
        display_name = (
            chat.get("title")
            or " ".join(
                part for part in (sender.get("first_name"), sender.get("last_name")) if part
            ).strip()
            or sender.get("username")
            or None
        )
        try:
            reply = handle_command(
                command,
                args,
                config=config,
                db_path=db_path,
                chat_id=chat_id,
                owner_chat_id=client.chat_id,
                display_name=display_name,
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


# A chat that will never be reachable again, versus a transient wobble. Only the
# first kind costs someone their subscription.
PERMANENT_SEND_FAILURES = (
    "bot was blocked by the user",
    "user is deactivated",
    "chat not found",
    "bot was kicked",
    "group chat was deleted",
    "have no rights to send",
)


def _is_permanent_failure(message: str) -> bool:
    lowered = str(message).lower()
    return any(marker in lowered for marker in PERMANENT_SEND_FAILURES)


def notify(
    config: dict[str, Any],
    text: str,
    *,
    silent: bool = False,
    transport: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Best-effort send to every subscriber. Never raises: a broken bot must
    not fail a run, and one unreachable friend must not silence the rest."""
    try:
        client = build_client(config, transport=transport)
    except TelegramDisabled as exc:
        return {"sent": False, "reason": str(exc)}

    targets = [client.chat_id]
    if db_path is not None:
        with CallDatabase(db_path) as db:
            targets = ms.broadcast_targets(db, config, owner_chat_id=client.chat_id)

    delivered, failed, reasons = 0, [], []
    for target in targets:
        try:
            client.send_message(text, chat_id=target, silent=silent)
            delivered += 1
        except TelegramError as exc:
            failed.append(target)
            reasons.append(f"{target}: {exc}")
            if db_path is not None and _is_permanent_failure(str(exc)):
                with CallDatabase(db_path) as db:
                    ms.mark_blocked(db, target)

    result: dict[str, Any] = {
        "sent": delivered > 0,
        "delivered": delivered,
        "failed": failed,
        "messages": len(client.sent),
    }
    if reasons:
        result["reason"] = "; ".join(reasons)
    return result


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
    db_path: str | Path | None = None,
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
        db_path=db_path,
    )


def main(argv: list[str] | None = None) -> int:
    load_dotenv()  # credentials may live in .env; a real env var still wins
    parser = argparse.ArgumentParser(description="Telegram bot for the lowcap call tracker")
    parser.add_argument("--config")
    parser.add_argument("--db")
    parser.add_argument("--test", action="store_true", help="Send a connectivity test message")
    parser.add_argument(
        "--setup-profile",
        action="store_true",
        help="Publish the command menu, description and about text to Telegram",
    )
    parser.add_argument(
        "--list-chats",
        action="store_true",
        help="Print the chat ids that messaged the bot (find a group's numeric id)",
    )
    parser.add_argument("--send-stats", action="store_true", help="Push the statistics block")
    parser.add_argument(
        "--report", action="store_true", help="Push the full report (open calls, stats, last run)"
    )
    parser.add_argument(
        "--invite",
        nargs="?",
        const="1",
        metavar="USES",
        help="Mint an invite link from the terminal (default 1 use)",
    )
    parser.add_argument(
        "--invite-days", type=int, default=None, help="Days the minted link stays usable"
    )
    parser.add_argument("--members", action="store_true", help="List the chats with access")
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

    if args.setup_profile:
        result = setup_profile(client, config=config)
        print(f"published {result['published']} commands, description and about text")
        return 0

    if args.invite is not None:
        telegram = config.get("telegram") or {}
        days = args.invite_days
        if days is None:
            days = telegram.get("invite_expiry_days", ms.DEFAULT_EXPIRY_DAYS)
        with CallDatabase(db_path) as db:
            row = ms.create_invite(
                db,
                created_by=str(client.chat_id),
                max_uses=int(args.invite),
                expires_days=days,
            )
        username = bot_username(config)
        if username:
            print(ms.invite_link(username, row["code"]))
        else:
            print(f"code: {row['code']} (send the bot: /start {row['code']})")
        print(
            f"{row['max_uses']} use(s), "
            + (f"expires {row['expires_at'][:10]}" if row["expires_at"] else "no expiry"),
            file=sys.stderr,
        )
        return 0

    if args.members:
        with CallDatabase(db_path) as db:
            rows = ms.list_subscribers(db)
        if not rows:
            print("no members yet")
            return 0
        print(f"{'CHAT ID':>16}  {'ROLE':<7}  {'JOINED':<10}  NAME")
        for row in rows:
            name = row["display_name"] or ""
            print(
                f"{row['chat_id']:>16}  {row['role']:<7}  {(row['joined_at'] or '')[:10]:<10}  {name}"
            )
        return 0

    if args.list_chats:
        print(format_chat_list(discover_chats(client), os.environ.get("TELEGRAM_CHAT_ID")))
        return 0

    if args.test:
        client.send_message("✅ <b>Lowcap tracker</b> is wired up.\n" + format_help(config))
        print("test message sent")
        return 0

    if args.report:
        with CallDatabase(db_path) as db:
            client.send_message(format_report_message(db, config))
        print("report sent")
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
