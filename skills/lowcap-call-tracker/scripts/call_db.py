#!/usr/bin/env python3
"""SQLite persistence for lowcap calls, shadow calls, role verdicts and spend.

Tables
------
``calls``         one row per call. ``kind`` is ``active`` (Judge said TAKE) or
                  ``shadow`` (Judge said SKIP — tracked identically so the value
                  the Judge adds is measurable).
``role_verdicts`` the full JSON verdict of every role, per call.
``price_history`` one row per price observation, per call.
``runs``          one row per tracker run.
``llm_usage``     token spend per role call, used for the monthly cap.
``subscribers``   every chat with access, and the role it holds.
``invites``       invite codes, their use budget and expiry.

A ticker can hold only one open call at a time: a partial unique index on
``ticker WHERE status = 'OPEN'`` enforces de-duplication in the database rather
than in application logic.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUS_OPEN = "OPEN"
STATUS_CLOSED_WRONG = "CLOSED_WRONG"  # legacy stop-out, only when a threshold is configured
STATUS_EXPIRED = "EXPIRED"  # the contract reached its expiration date
KIND_ACTIVE = "active"
KIND_SHADOW = "shadow"
# A hit the screener found while the role backend was down. It is tracked like
# any other call so the screener's own edge stays measurable, but it carries no
# opinion, so it is excluded from every statistic that judges the Judge.
KIND_UNREVIEWED = "unreviewed"
DECISION_UNREVIEWED = "UNREVIEWED"

SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    -- direction is the PnL convention (long/short) derived from the instrument;
    -- instrument is what is actually traded: a call or a put.
    direction TEXT NOT NULL,
    instrument TEXT,
    expiry_date TEXT,
    strike REAL,
    kind TEXT NOT NULL,
    call_date TEXT NOT NULL,
    entry_price REAL NOT NULL,
    screen_variant TEXT,
    judge_decision TEXT NOT NULL,
    confidence INTEGER,
    judge_reason TEXT,
    researcher_score REAL,
    technician_score REAL,
    skeptic_score REAL,
    risk_manager_score REAL,
    stop_price REAL,
    target_price REAL,
    shares REAL,
    position_usd REAL,
    risk_usd REAL,
    status TEXT NOT NULL,
    current_price REAL,
    pnl_pct REAL,
    last_price_at TEXT,
    closed_at TEXT,
    close_reason TEXT,
    run_id TEXT,
    backend TEXT,
    notes TEXT,
    -- When the roles actually spoke. Distinct from call_date on purpose: a call
    -- entered while the backend was down keeps its original entry price and
    -- date, and records separately when it was finally reviewed.
    reviewed_at TEXT,
    review_run_id TEXT,
    -- The screener row, kept so an UNREVIEWED call can be reviewed later.
    hit_json TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_calls_open_ticker
    ON calls (ticker) WHERE status = 'OPEN';
CREATE INDEX IF NOT EXISTS idx_calls_status ON calls (status);
CREATE INDEX IF NOT EXISTS idx_calls_kind ON calls (kind);

CREATE TABLE IF NOT EXISTS role_verdicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id INTEGER NOT NULL REFERENCES calls (id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    score REAL,
    backend TEXT,
    verdict_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_verdicts_call ON role_verdicts (call_id);

CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id INTEGER NOT NULL REFERENCES calls (id) ON DELETE CASCADE,
    observed_at TEXT NOT NULL,
    price REAL NOT NULL,
    pnl_pct REAL
);
CREATE INDEX IF NOT EXISTS idx_prices_call ON price_history (call_id);

CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    screening_ran INTEGER,
    session_reason TEXT,
    hits INTEGER,
    reviewed INTEGER,
    new_calls INTEGER,
    new_takes INTEGER,
    new_shadows INTEGER,
    closed INTEGER,
    priced INTEGER,
    backend TEXT,
    llm_cost_usd REAL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS llm_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    created_at TEXT NOT NULL,
    month TEXT NOT NULL,
    role TEXT,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cache_read_tokens INTEGER,
    cost_usd REAL
);
CREATE INDEX IF NOT EXISTS idx_usage_month ON llm_usage (month);

CREATE TABLE IF NOT EXISTS subscribers (
    chat_id TEXT PRIMARY KEY,
    display_name TEXT,
    role TEXT NOT NULL DEFAULT 'member',
    status TEXT NOT NULL DEFAULT 'active',
    joined_at TEXT NOT NULL,
    left_at TEXT,
    invited_by TEXT,
    invite_code TEXT
);
CREATE INDEX IF NOT EXISTS idx_subscribers_status ON subscribers (status);

CREATE TABLE IF NOT EXISTS invites (
    code TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    created_by TEXT,
    max_uses INTEGER NOT NULL DEFAULT 1,
    uses INTEGER NOT NULL DEFAULT 0,
    expires_at TEXT,
    revoked_at TEXT,
    note TEXT
);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def pnl_pct(entry: float, current: float, direction: str) -> float | None:
    """Direction-corrected PnL in percent (long: up is positive; short: down is)."""
    if not entry or entry <= 0 or current is None:
        return None
    if str(direction).lower() == "short":
        return round((entry - current) / entry * 100.0, 4)
    return round((current - entry) / entry * 100.0, 4)


class CallDatabase:
    """Thin SQLite wrapper; also implements ``llm_client.SpendStore``."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self._migrate()
        self.conn.commit()

    def _migrate(self) -> None:
        """Add columns introduced after a database was first created."""
        existing = {row["name"] for row in self.conn.execute("PRAGMA table_info(calls)")}
        for column, ddl in (
            ("instrument", "ALTER TABLE calls ADD COLUMN instrument TEXT"),
            ("expiry_date", "ALTER TABLE calls ADD COLUMN expiry_date TEXT"),
            ("strike", "ALTER TABLE calls ADD COLUMN strike REAL"),
            ("reviewed_at", "ALTER TABLE calls ADD COLUMN reviewed_at TEXT"),
            ("review_run_id", "ALTER TABLE calls ADD COLUMN review_run_id TEXT"),
            ("hit_json", "ALTER TABLE calls ADD COLUMN hit_json TEXT"),
        ):
            if column not in existing:
                self.conn.execute(ddl)
        # Pre-options rows: a long was a call, a short was a put.
        self.conn.execute(
            "UPDATE calls SET instrument = CASE WHEN direction = 'short' THEN 'put' "
            "ELSE 'call' END WHERE instrument IS NULL"
        )

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> CallDatabase:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # ----------------------------------------------------------------- calls

    def open_call_for(self, ticker: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM calls WHERE ticker = ? AND status = ?",
            (ticker.upper(), STATUS_OPEN),
        ).fetchone()

    def insert_call(
        self, review: dict[str, Any], *, run_id: str, now: str | None = None
    ) -> int | None:
        """Insert a call from a review. Returns the id, or None when a duplicate.

        Both TAKE and SKIP are stored: a SKIP becomes a shadow call, tracked the
        same way so the Judge's selectivity can be measured.
        """
        ticker = str(review["ticker"]).upper()
        if self.open_call_for(ticker):
            return None

        verdicts = review.get("verdicts", {})
        risk = verdicts.get("risk_manager", {})
        entry = review.get("entry") or review.get("price")
        if not entry:
            return None
        decision = review.get("decision", "SKIP")
        unreviewed = decision == DECISION_UNREVIEWED
        instrument = (risk.get("instrument") or "").lower()
        if instrument not in {"call", "put"}:
            instrument = "put" if risk.get("direction") == "short" else "call"
        # A put profits when the underlying falls, so it keeps short PnL maths.
        direction = "short" if instrument == "put" else "long"
        stamp = now or utc_now()

        cursor = self.conn.execute(
            """
            INSERT INTO calls (
                ticker, asset_type, direction, instrument, expiry_date, strike,
                kind, call_date, entry_price,
                screen_variant, judge_decision, confidence, judge_reason,
                researcher_score, technician_score, skeptic_score, risk_manager_score,
                stop_price, target_price, shares, position_usd, risk_usd,
                status, current_price, pnl_pct, last_price_at, run_id, backend, notes,
                reviewed_at, hit_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                ticker,
                review.get("asset_type", "stock"),
                direction,
                instrument,
                risk.get("expiry_date"),
                risk.get("strike"),
                KIND_UNREVIEWED
                if unreviewed
                else (KIND_ACTIVE if decision == "TAKE" else KIND_SHADOW),
                stamp,
                float(entry),
                review.get("variant"),
                decision,
                int(review.get("confidence") or 0),
                (verdicts.get("judge", {}) or {}).get("reason"),
                (verdicts.get("researcher", {}) or {}).get("score"),
                (verdicts.get("technician", {}) or {}).get("score"),
                (verdicts.get("skeptic", {}) or {}).get("score"),
                risk.get("score"),
                risk.get("stop"),
                risk.get("target"),
                risk.get("shares"),
                risk.get("position_usd"),
                risk.get("risk_usd"),
                STATUS_OPEN,
                float(entry),
                0.0,
                stamp,
                run_id,
                review.get("backend"),
                "; ".join(review.get("notes", []))[:500] or None,
                None if unreviewed else stamp,
                json.dumps(review.get("hit"), default=str) if review.get("hit") else None,
            ),
        )
        call_id = int(cursor.lastrowid)
        for role, verdict in verdicts.items():
            self.conn.execute(
                """
                INSERT INTO role_verdicts (call_id, role, score, backend, verdict_json, created_at)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    call_id,
                    role,
                    verdict.get("score"),
                    verdict.get("backend"),
                    json.dumps(verdict, default=str),
                    stamp,
                ),
            )
        self.conn.execute(
            "INSERT INTO price_history (call_id, observed_at, price, pnl_pct) VALUES (?,?,?,?)",
            (call_id, stamp, float(entry), 0.0),
        )
        self.conn.commit()
        return call_id

    def unreviewed_calls(self) -> list[sqlite3.Row]:
        """Open calls still waiting for a role review, oldest first."""
        return list(
            self.conn.execute(
                "SELECT * FROM calls WHERE status = ? AND judge_decision = ? "
                "ORDER BY call_date, id",
                (STATUS_OPEN, DECISION_UNREVIEWED),
            )
        )

    def apply_review(
        self,
        call_id: int,
        review: dict[str, Any],
        *,
        run_id: str,
        now: str | None = None,
    ) -> dict[str, Any]:
        """Attach a late review to an existing call.

        The entry price and call date are never touched: the call was taken when
        the screener found it, and moving its entry to match a later opinion
        would flatter every statistic that follows. ``reviewed_at`` records when
        the roles actually spoke.
        """
        stamp = now or utc_now()
        verdicts = review.get("verdicts", {})
        risk = verdicts.get("risk_manager", {}) or {}
        decision = review.get("decision", "SKIP")
        instrument = (risk.get("instrument") or "").lower()
        if instrument not in {"call", "put"}:
            instrument = "put" if risk.get("direction") == "short" else "call"
        direction = "short" if instrument == "put" else "long"

        self.conn.execute(
            """
            UPDATE calls SET
                direction = ?, instrument = ?, expiry_date = ?, strike = ?,
                kind = ?, judge_decision = ?, confidence = ?, judge_reason = ?,
                researcher_score = ?, technician_score = ?, skeptic_score = ?,
                risk_manager_score = ?, stop_price = ?, target_price = ?,
                shares = ?, position_usd = ?, risk_usd = ?, backend = ?,
                reviewed_at = ?, review_run_id = ?
            WHERE id = ?
            """,
            (
                direction,
                instrument,
                risk.get("expiry_date"),
                risk.get("strike"),
                KIND_ACTIVE if decision == "TAKE" else KIND_SHADOW,
                decision,
                int(review.get("confidence") or 0),
                (verdicts.get("judge", {}) or {}).get("reason"),
                (verdicts.get("researcher", {}) or {}).get("score"),
                (verdicts.get("technician", {}) or {}).get("score"),
                (verdicts.get("skeptic", {}) or {}).get("score"),
                risk.get("score"),
                risk.get("stop"),
                risk.get("target"),
                risk.get("shares"),
                risk.get("position_usd"),
                risk.get("risk_usd"),
                review.get("backend"),
                stamp,
                run_id,
                call_id,
            ),
        )
        for role, verdict in verdicts.items():
            self.conn.execute(
                """
                INSERT INTO role_verdicts (call_id, role, score, backend, verdict_json, created_at)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    call_id,
                    role,
                    verdict.get("score"),
                    verdict.get("backend"),
                    json.dumps(verdict, default=str),
                    stamp,
                ),
            )
        # A put reverses the PnL convention, so any prior marks must be redone.
        self._recompute_pnl(call_id, direction)
        self.conn.commit()
        return dict(self.conn.execute("SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone())

    def _recompute_pnl(self, call_id: int, direction: str) -> None:
        """Re-mark a call after its direction changed."""
        row = self.conn.execute("SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone()
        if row is None or row["current_price"] is None:
            return
        fresh = pnl_pct(row["entry_price"], row["current_price"], direction)
        self.conn.execute("UPDATE calls SET pnl_pct = ? WHERE id = ?", (fresh, call_id))

    def open_calls(self) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM calls WHERE status = ? ORDER BY call_date", (STATUS_OPEN,)
            )
        )

    def all_calls(self) -> list[sqlite3.Row]:
        return list(self.conn.execute("SELECT * FROM calls ORDER BY call_date"))

    def call(self, call_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone()

    def verdicts_for(self, call_id: int) -> dict[str, dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT role, verdict_json FROM role_verdicts WHERE call_id = ?", (call_id,)
        )
        return {row["role"]: json.loads(row["verdict_json"]) for row in rows}

    def expire_call(self, call_id: int, *, now: str | None = None) -> dict[str, Any]:
        """Settle a call whose contract has expired, at its last known price."""
        row = self.call(call_id)
        if row is None:
            raise KeyError(f"unknown call id {call_id}")
        stamp = now or utc_now()
        self.conn.execute(
            """
            UPDATE calls SET status = ?, closed_at = ?, close_reason = ?
             WHERE id = ? AND status = ?
            """,
            (
                STATUS_EXPIRED,
                stamp,
                f"contract expired {row['expiry_date']}",
                call_id,
                STATUS_OPEN,
            ),
        )
        self.conn.commit()
        return {
            "call_id": call_id,
            "ticker": row["ticker"],
            "instrument": row["instrument"],
            "expiry_date": row["expiry_date"],
            "pnl_pct": row["pnl_pct"],
            "expired": True,
        }

    def apply_price(
        self,
        call_id: int,
        price: float,
        *,
        close_threshold_pct: float | None,
        now: str | None = None,
    ) -> dict[str, Any]:
        """Record a price observation, recompute PnL, and close at the threshold."""
        row = self.call(call_id)
        if row is None:
            raise KeyError(f"unknown call id {call_id}")
        stamp = now or utc_now()
        pnl = pnl_pct(row["entry_price"], price, row["direction"])
        closed = False
        stop_out = (
            close_threshold_pct is not None
            and pnl is not None
            and pnl <= close_threshold_pct
            and row["status"] == STATUS_OPEN
        )
        if stop_out:
            closed = True
            self.conn.execute(
                """
                UPDATE calls SET current_price = ?, pnl_pct = ?, last_price_at = ?,
                       status = ?, closed_at = ?, close_reason = ?
                 WHERE id = ?
                """,
                (
                    price,
                    pnl,
                    stamp,
                    STATUS_CLOSED_WRONG,
                    stamp,
                    f"pnl {pnl:.2f}% <= {close_threshold_pct:.2f}% threshold",  # noqa: E501
                    call_id,
                ),
            )
        else:
            self.conn.execute(
                "UPDATE calls SET current_price = ?, pnl_pct = ?, last_price_at = ? WHERE id = ?",
                (price, pnl, stamp, call_id),
            )
        self.conn.execute(
            "INSERT INTO price_history (call_id, observed_at, price, pnl_pct) VALUES (?,?,?,?)",
            (call_id, stamp, price, pnl),
        )
        self.conn.commit()
        return {
            "call_id": call_id,
            "ticker": row["ticker"],
            "price": price,
            "pnl_pct": pnl,
            "closed": closed,
        }

    # ------------------------------------------------------------------ runs

    def start_run(self, run_id: str, *, session_reason: str, screening_ran: bool) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO runs (run_id, started_at, screening_ran, session_reason)
            VALUES (?,?,?,?)
            """,
            (run_id, utc_now(), int(screening_ran), session_reason),
        )
        self.conn.commit()

    def finish_run(self, run_id: str, summary: dict[str, Any]) -> None:
        self.conn.execute(
            """
            UPDATE runs SET finished_at = ?, hits = ?, reviewed = ?, new_calls = ?,
                   new_takes = ?, new_shadows = ?, closed = ?, priced = ?,
                   backend = ?, llm_cost_usd = ?, notes = ?
             WHERE run_id = ?
            """,
            (
                utc_now(),
                summary.get("hits", 0),
                summary.get("reviewed", 0),
                summary.get("new_calls", 0),
                summary.get("new_takes", 0),
                summary.get("new_shadows", 0),
                summary.get("closed", 0),
                summary.get("priced", 0),
                summary.get("backend"),
                summary.get("llm_cost_usd", 0.0),
                summary.get("notes"),
                run_id,
            ),
        )
        self.conn.commit()

    def runs(self, limit: int = 20) -> list[sqlite3.Row]:
        return list(
            self.conn.execute("SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,))
        )

    # ------------------------------------------------------------- llm spend

    def record_llm_usage(self, entry: dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT INTO llm_usage (run_id, created_at, month, role, model,
                                   input_tokens, output_tokens, cache_read_tokens, cost_usd)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                entry.get("run_id"),
                entry.get("created_at", utc_now()),
                entry["month"],
                entry.get("role"),
                entry.get("model"),
                entry.get("input_tokens", 0),
                entry.get("output_tokens", 0),
                entry.get("cache_read_tokens", 0),
                entry.get("cost_usd", 0.0),
            ),
        )
        self.conn.commit()

    def month_to_date_spend(self, month: str) -> float:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0.0) AS total FROM llm_usage WHERE month = ?",
            (month,),
        ).fetchone()
        return float(row["total"] if row else 0.0)
