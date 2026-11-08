#!/usr/bin/env python3
"""Strategy A live runner: hold SPY + 30-minute ORB overlay on Alpaca.

PAPER TRADING BY DEFAULT. Not investment advice; use at your own risk.

What it does each trading day (run it at ~09:25 ET, it exits after the close):
  1. Core: keeps a buy-and-hold SPY position (bought once, $core_dollars).
  2. Opening range: high/low of 09:30-10:00 ET from 5-min bars.
  3. Filters: sits out FOMC days and days whose opening range is wider than
     0.4x the prior 10-day average daily range.
  4. Overlay (one per day, entries until 15:30):
       - 5-min close above the range -> BUY $overlay_dollars more SPY
       - 5-min close below the range -> SELL core shares worth $overlay_dollars
         (the account goes flat, never net short; same P&L as a short overlay
         as long as the core is at least as large as the overlay)
  5. Exit: 3x ATR(14, 5-min) trailing stop, never looser than 5%, checked on
     every price poll; otherwise closed at 15:57 ET (or 3 minutes before an
     early close). The core position is never sold by the exit.

The trading rules in DayEngine are the same as orb_backtest.py with
--stop-mode atr --atr-mult 3 --skip-fomc --max-or-width-rel 0.4 --no-target
(tests/test_live_orb_overlay.py replays days through both and compares).

Account requirements (live): the long overlay needs margin buying power
(Alpaca: margin needs >= $2,000 equity) and every overlay is a day trade, so
accounts under $25,000 hit the pattern-day-trader limit (3 per 5 days).

Usage:
    export ALPACA_API_KEY=... ALPACA_SECRET_KEY=...       # paper keys
    python3 live_orb_overlay.py --dry-run                 # log only, no orders
    python3 live_orb_overlay.py                           # paper orders
    python3 live_orb_overlay.py --live --i-understand-live-risk   # real money
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orb_backtest import FOMC_DATES, add_atr, normalize  # noqa: E402

TZ = "America/New_York"
PAPER_URL = "https://paper-api.alpaca.markets"
LIVE_URL = "https://api.alpaca.markets"
DATA_URL = "https://data.alpaca.markets"
log = logging.getLogger("orb_overlay")


def _now() -> pd.Timestamp:  # patched in tests
    return pd.Timestamp.now(tz=TZ)


def _sleep(seconds: float) -> None:  # patched in tests
    time.sleep(seconds)


# ------------------------------------------------------------------- settings


@dataclass
class Settings:
    symbol: str = "SPY"
    core_dollars: float = 1000.0
    overlay_dollars: float = 1000.0
    range_minutes: int = 30
    atr_period: int = 14
    atr_mult: float = 3.0
    stop_pct: float = 5.0
    max_or_width_rel: float | None = 0.4
    adr_days: int = 10
    skip_fomc: bool = True
    last_entry: str = "15:30"
    exit_at: str = "15:57"
    poll_seconds: int = 15


# --------------------------------------------------------------- trading rules


@dataclass
class DayEngine:
    """One session's ORB state machine: range -> watch -> in_trade -> done."""

    day: str
    phase: str = "range"
    or_high: float | None = None
    or_low: float | None = None
    day_open: float | None = None
    direction: int = 0
    entry_price: float | None = None
    stop: float | None = None
    initial_stop: float | None = None
    extreme: float | None = None
    entry_atr: float | None = None
    entry_ts: str | None = None
    exit_reason: str | None = None
    exit_price: float | None = None
    overlay_qty: float = 0.0
    last_bar_ts: str | None = None
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> DayEngine:
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in names})

    # -- helpers
    def _done(self, note: str):
        self.phase, self.note = "done", note
        return None

    def _set_stop(self, entry: float, atr, s: Settings):
        pct_stop = entry * (1 - self.direction * s.stop_pct / 100)
        if atr is None or pd.isna(atr):
            stop = pct_stop
        else:
            atr_stop = entry - self.direction * s.atr_mult * float(atr)
            stop = max(atr_stop, pct_stop) if self.direction == 1 else min(atr_stop, pct_stop)
        self.entry_price, self.stop, self.initial_stop, self.extreme = entry, stop, stop, entry

    def _exit(self, reason: str, price: float) -> dict:
        moved = (
            self.initial_stop is not None
            and (self.stop - self.initial_stop) * self.direction > 1e-12
        )
        if reason == "stop" and moved:
            reason = "trail_stop"
        self.phase, self.exit_reason, self.exit_price = "done", reason, price
        return {"action": "exit", "reason": reason, "ref_price": price}

    # -- events
    def start(self, s: Settings) -> None:
        if s.skip_fomc and self.day in FOMC_DATES:
            self._done("FOMC day - sitting out")

    def on_bar(self, bar: dict, s: Settings, adr_pct: float | None) -> dict | None:
        """Process one COMPLETED 5-min bar (keys: ts, open, high, low, close, atr)."""
        ts = pd.Timestamp(bar["ts"])
        self.last_bar_ts = ts.isoformat()
        if self.phase == "done":
            return None
        or_end = ts.normalize() + pd.Timedelta(hours=9, minutes=30 + s.range_minutes)

        if self.phase == "range":
            if ts < or_end:
                if self.day_open is None:
                    self.day_open = float(bar["open"])
                self.or_high = max(self.or_high or -math.inf, float(bar["high"]))
                self.or_low = min(self.or_low or math.inf, float(bar["low"]))
                return None
            if self.or_high is None:
                return self._done("no opening-range bars")
            if s.max_or_width_rel is not None:
                if adr_pct is None or pd.isna(adr_pct) or adr_pct <= 0:
                    return self._done("no daily-range history for width filter")
                width = (self.or_high - self.or_low) / self.day_open * 100
                if width / adr_pct > s.max_or_width_rel:
                    return self._done(f"range too wide ({width:.2f}% vs avg {adr_pct:.2f}%)")
            self.phase = "watch"

        if self.phase == "watch":
            if ts.time() > pd.Timestamp(s.last_entry).time():
                return self._done("no breakout before last entry time")
            close = float(bar["close"])
            if close > self.or_high:
                self.direction = 1
            elif close < self.or_low:
                self.direction = -1
            else:
                return None
            self.phase, self.entry_ts, self.entry_atr = "in_trade", ts.isoformat(), bar.get("atr")
            self._set_stop(close, bar.get("atr"), s)
            return {"action": "enter", "direction": self.direction, "ref_price": close}

        if self.phase == "in_trade":
            if self.entry_ts == ts.isoformat():
                return None  # the entry bar itself is not checked (matches backtest)
            o, h, low = float(bar["open"]), float(bar["high"]), float(bar["low"])
            if self.direction == 1 and low <= self.stop:
                return self._exit("stop", min(self.stop, o))
            if self.direction == -1 and h >= self.stop:
                return self._exit("stop", max(self.stop, o))
            atr = bar.get("atr")
            if atr is not None and not pd.isna(atr):
                if self.direction == 1:
                    self.extreme = max(self.extreme, h)
                    self.stop = max(self.stop, self.extreme - s.atr_mult * float(atr))
                else:
                    self.extreme = min(self.extreme, low)
                    self.stop = min(self.stop, self.extreme + s.atr_mult * float(atr))
        return None

    def on_price(
        self, price: float, now: pd.Timestamp, s: Settings, exit_at: str | None = None
    ) -> dict | None:
        """Live tick between bars: stop check and end-of-day exit."""
        if self.phase != "in_trade":
            return None
        if now.time() >= pd.Timestamp(exit_at or s.exit_at).time():
            return self._exit("eod", price)
        if (self.direction == 1 and price <= self.stop) or (
            self.direction == -1 and price >= self.stop
        ):
            return self._exit("stop", price)
        return None

    def confirm_entry(self, fill_price: float, qty: float, s: Settings) -> None:
        """Re-anchor the stop on the actual fill."""
        self._set_stop(fill_price, self.entry_atr, s)
        self.overlay_qty = qty


def replay_day(day: pd.DataFrame, s: Settings, adr_pct: float | None) -> dict | None:
    """Run a historical session (with an 'atr' column) through DayEngine."""
    eng = DayEngine(day=day.index[0].date().isoformat())
    eng.start(s)
    for ts, row in day.iterrows():
        eng.on_bar({"ts": ts, **row.to_dict()}, s, adr_pct)
    if eng.phase == "in_trade":
        eng._exit("eod", float(day["close"].iloc[-1]))
    if eng.entry_price is None:
        return None
    return {
        "direction": "long" if eng.direction == 1 else "short",
        "entry_price": eng.entry_price,
        "exit_price": eng.exit_price,
        "exit_reason": eng.exit_reason,
    }


def plan_entry(direction: int, price: float, core_qty: float, s: Settings) -> dict:
    if direction == 1:
        return {"side": "buy", "notional": round(s.overlay_dollars, 2)}
    want = math.floor(s.overlay_dollars / price * 1e6) / 1e6
    return {"side": "sell", "qty": round(min(want, core_qty), 6)}


def plan_exit(direction: int, overlay_qty: float) -> dict:
    return {"side": "sell" if direction == 1 else "buy", "qty": round(overlay_qty, 6)}


# ---------------------------------------------------------------- Alpaca I/O


class Alpaca:
    def __init__(self, key: str, secret: str, trading_url: str, dry_run: bool):
        self.h = {
            "APCA-API-KEY-ID": key,
            "APCA-API-SECRET-KEY": secret,
            "Content-Type": "application/json",
        }
        self.url, self.dry = trading_url, dry_run

    def _req(self, method, url, body=None, retries=4):
        data = json.dumps(body).encode() if body is not None else None
        for i in range(retries):
            try:
                req = urllib.request.Request(url, data=data, headers=self.h, method=method)
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.loads(r.read() or b"null")
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
                if e.code == 429 or e.code >= 500:
                    time.sleep(2**i)
                    continue
                raise RuntimeError(
                    f"Alpaca {method} {url} -> {e.code}: {e.read()[:300].decode(errors='replace')}"
                ) from e
            except urllib.error.URLError:
                time.sleep(2**i)
        raise RuntimeError(f"Alpaca {method} {url}: retries exhausted")

    def clock(self):
        return self._req("GET", f"{self.url}/v2/clock")

    def account(self):
        return self._req("GET", f"{self.url}/v2/account")

    def position_qty(self, symbol) -> float:
        p = self._req("GET", f"{self.url}/v2/positions/{symbol}")
        return float(p["qty"]) if p else 0.0

    def latest_price(self, symbol) -> float:
        d = self._req("GET", f"{DATA_URL}/v2/stocks/{symbol}/trades/latest?feed=iex")
        return float(d["trade"]["p"])

    def bars(self, symbol, start, end, feed) -> pd.DataFrame:
        out, token = [], None
        while True:
            q = {
                "timeframe": "5Min",
                "start": start,
                "end": end,
                "feed": feed,
                "limit": 10000,
                "adjustment": "split",
            }
            if token:
                q["page_token"] = token
            d = self._req("GET", f"{DATA_URL}/v2/stocks/{symbol}/bars?" + urllib.parse.urlencode(q))
            out += d.get("bars") or []
            token = d.get("next_page_token")
            if not token:
                break
        if not out:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        df = pd.DataFrame(out).rename(
            columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}
        )
        df.index = pd.to_datetime(df["t"], utc=True)
        return normalize(df[["open", "high", "low", "close", "volume"]])

    def order(self, symbol, side, qty=None, notional=None, ref_price=None) -> tuple[float, float]:
        """Market order; returns (filled_qty, avg_price). Dry-run fills at ref_price."""
        if self.dry:
            q = qty if qty is not None else notional / ref_price
            log.info(
                "[DRY-RUN] %s %s qty=%s notional=%s @~%.2f", side, symbol, qty, notional, ref_price
            )
            return float(q), float(ref_price)
        body = {"symbol": symbol, "side": side, "type": "market", "time_in_force": "day"}
        body.update({"qty": str(qty)} if qty is not None else {"notional": str(notional)})
        o = self._req("POST", f"{self.url}/v2/orders", body)
        for _ in range(60):
            o = self._req("GET", f"{self.url}/v2/orders/{o['id']}")
            if o["status"] == "filled":
                return float(o["filled_qty"]), float(o["filled_avg_price"])
            if o["status"] in ("canceled", "rejected", "expired"):
                raise RuntimeError(f"order {o['id']} {o['status']}")
            time.sleep(1)
        raise RuntimeError(f"order {o['id']} not filled after 60s (status {o['status']})")


# -------------------------------------------------------------------- runner


def _load(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    os.replace(tmp, path)


def run(s: Settings, api: Alpaca, state_dir: Path) -> int:
    now = _now()
    clock = api.clock()
    if not clock["is_open"]:
        nxt = pd.Timestamp(clock["next_open"]).tz_convert(TZ)
        if nxt.date() != now.date():
            log.info("Market closed today; next open %s. Nothing to do.", nxt)
            return 0
        log.info("Waiting for the open at %s", nxt)
        while _now() < nxt:
            _sleep(min(30, max(1, (nxt - _now()).total_seconds())))
        clock = api.clock()
    close_ts = pd.Timestamp(clock["next_close"]).tz_convert(TZ)
    exit_at = min(
        pd.Timestamp(f"{close_ts.date()} {s.exit_at}", tz=TZ), close_ts - pd.Timedelta(minutes=3)
    )
    exit_at_str = exit_at.strftime("%H:%M")
    today = _now().date().isoformat()

    # --- core position
    core_path = state_dir / f"{s.symbol.lower()}_core.json"
    core = _load(core_path, {})
    day_path = state_dir / f"{s.symbol.lower()}_{today}.json"
    eng = DayEngine.from_dict(_load(day_path, {"day": today}))
    expected_overlay = eng.overlay_qty * (eng.direction if eng.phase == "in_trade" else 0)
    if not core:
        price = api.latest_price(s.symbol)
        qty, px = api.order(s.symbol, "buy", notional=round(s.core_dollars, 2), ref_price=price)
        core = {"qty": qty, "bought_at": px, "date": today}
        _save(core_path, core)
        log.info("Bought core %.6f %s @ %.2f", qty, s.symbol, px)
    elif not api.dry:
        held = api.position_qty(s.symbol)
        expect = core["qty"] + expected_overlay
        if abs(held - expect) > 1e-4:
            log.error(
                "Position mismatch: broker %.6f vs expected %.6f. Not trading today.", held, expect
            )
            return 1

    # --- history for ATR warm-up and the 10-day average range (SIP, >15 min old)
    hist = api.bars(s.symbol, (now - pd.Timedelta(days=25)).strftime("%Y-%m-%d"), today, "sip")
    hist = hist[hist.index.date < now.date()]
    g = hist.groupby(hist.index.date)
    ranges = ((g["high"].max() - g["low"].min()) / g["close"].last() * 100).tail(s.adr_days)
    adr = float(ranges.mean()) if len(ranges) == s.adr_days else None
    log.info(
        "%s | prior %d-day avg range %s | exit at %s",
        today,
        s.adr_days,
        f"{adr:.2f}%" if adr else "n/a",
        exit_at_str,
    )

    eng.start(s)
    _save(day_path, eng.to_dict())
    if eng.phase == "done":
        log.info("Skipping: %s", eng.note)
        return 0

    start_utc = (
        pd.Timestamp(f"{today} 09:30", tz=TZ).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    while True:
        now = _now()
        # completed bars only
        live = api.bars(
            s.symbol, start_utc, now.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"), "iex"
        )
        live = live[live.index + pd.Timedelta(minutes=5) <= now]
        full = add_atr(pd.concat([hist, live]), s.atr_period)
        new = full[(full.index.date == now.date())]
        if eng.last_bar_ts:
            new = new[new.index > pd.Timestamp(eng.last_bar_ts)]
        actions = []
        for ts, row in new.iterrows():
            act = eng.on_bar({"ts": ts, **row.to_dict()}, s, adr)
            if act:
                actions.append(act)
        if eng.phase == "in_trade" and not any(a["action"] == "exit" for a in actions):
            act = eng.on_price(api.latest_price(s.symbol), now, s, exit_at_str)
            if act:
                actions.append(act)

        for act in actions:
            if act["action"] == "enter":
                price = api.latest_price(s.symbol)
                plan = plan_entry(eng.direction, price, core["qty"], s)
                try:
                    if plan["side"] == "buy" and not api.dry:
                        bp = float(api.account().get("buying_power", 0))
                        if bp < plan["notional"]:
                            raise RuntimeError(f"buying power ${bp:.2f} < ${plan['notional']:.2f}")
                    qty, px = api.order(
                        s.symbol, plan["side"], plan.get("qty"), plan.get("notional"), price
                    )
                except RuntimeError as e:
                    log.error("Entry failed (%s); done for today.", e)
                    eng._done(f"entry failed: {e}")
                    break
                eng.confirm_entry(px, qty, s)
                log.info(
                    "ENTER %s %.6f @ %.2f | range %.2f-%.2f | stop %.2f",
                    "LONG" if eng.direction == 1 else "SHORT(sell core)",
                    qty,
                    px,
                    eng.or_low,
                    eng.or_high,
                    eng.stop,
                )
            elif act["action"] == "exit" and eng.overlay_qty > 0:
                plan = plan_exit(eng.direction, eng.overlay_qty)
                price = api.latest_price(s.symbol)
                try:
                    qty, px = api.order(s.symbol, plan["side"], plan["qty"], ref_price=price)
                except RuntimeError as e:
                    log.error("EXIT ORDER FAILED (%s) - will retry. Check the broker!", e)
                    eng.phase = "in_trade"  # retry next loop
                    break
                pnl = (px - eng.entry_price) * eng.direction * eng.overlay_qty
                log.info(
                    "EXIT %s %.6f @ %.2f (%s) | overlay P&L $%.2f",
                    plan["side"],
                    qty,
                    px,
                    eng.exit_reason,
                    pnl,
                )
                eng.exit_price, eng.overlay_qty = px, 0.0
        _save(day_path, eng.to_dict())

        if eng.phase == "done" or now >= close_ts:
            log.info("Done for today: %s", eng.exit_reason or eng.note or "no trade")
            return 0
        _sleep(s.poll_seconds)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--symbol", default="SPY")
    p.add_argument("--core-dollars", type=float, default=1000.0)
    p.add_argument("--overlay-dollars", type=float, default=1000.0)
    p.add_argument("--dry-run", action="store_true", help="Log decisions, place no orders")
    p.add_argument("--live", action="store_true", help="Trade the LIVE account (default: paper)")
    p.add_argument("--i-understand-live-risk", action="store_true")
    p.add_argument("--state-dir", default="state/orb_overlay")
    p.add_argument("--log-dir", default="logs")
    a = p.parse_args(argv)

    key, secret = os.environ.get("ALPACA_API_KEY"), os.environ.get("ALPACA_SECRET_KEY")
    if not key or not secret:
        print(
            "Set ALPACA_API_KEY and ALPACA_SECRET_KEY (paper keys from app.alpaca.markets)",
            file=sys.stderr,
        )
        return 1
    if a.live and not a.i_understand_live_risk:
        print("--live also needs --i-understand-live-risk", file=sys.stderr)
        return 1

    Path(a.log_dir).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(Path(a.log_dir) / f"orb_overlay_{datetime.now():%Y-%m-%d}.log"),
        ],
    )
    s = Settings(
        symbol=a.symbol.upper(), core_dollars=a.core_dollars, overlay_dollars=a.overlay_dollars
    )
    api = Alpaca(key, secret, LIVE_URL if a.live else PAPER_URL, a.dry_run)
    log.info("Mode: %s%s", "LIVE" if a.live else "PAPER", " (dry-run)" if a.dry_run else "")
    try:
        return run(s, api, Path(a.state_dir))
    except KeyboardInterrupt:
        log.warning(
            "Interrupted. State is saved; re-run to resume (open overlay is still at the broker)."
        )
        return 130


if __name__ == "__main__":
    sys.exit(main())
