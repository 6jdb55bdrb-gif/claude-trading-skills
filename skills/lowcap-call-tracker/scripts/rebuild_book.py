"""Rebuild the lowcap book after the container was recycled and live.db was lost.

Every number here was read out of the live database during the 2026-10-20 scans
and is quoted from that session's output — nothing is estimated. What cannot be
recovered is stated in the report this prints, not papered over:

* closed UNFUNDED calls (APUS, TRUG, JAGX, CTNT, DAIC, TGL, ...) are missing, so
  the equal-weight hit-rate tables restart with fewer rows than before. They
  never touched the cash, so the dollar account is unaffected.
* per-call outcome rows (ret_1d/3d/5d, stop-hit flags) and role verdicts for
  closed calls are gone; the v1-vs-v2 scorecard starts over.
* closed-call dates are set to their known close date where the session output
  recorded one, and to the last date they were seen open otherwise.

The dollar account IS fully recoverable, because it depends only on each funded
call's allocation and its final PnL, and both were printed per row.
"""

import sys
from pathlib import Path

# This repository is public, so no absolute home path may be baked in: resolve
# the scripts directory from this file's own location.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from call_db import CallDatabase  # noqa: E402

from config import load_config, resolve_path  # noqa: E402

# ticker, pnl_pct, allocation, close date, status
CLOSED = [
    ("SDEV", 175.82, 100.00, "2026-10-05", "STOPPED"),
    ("SDEV", 136.88, 100.00, "2026-10-06", "STOPPED"),
    ("VEEA", 35.78, 100.00, "2026-10-16", "STOPPED"),
    ("GRML", 9.88, 100.00, "2026-09-29", "STOPPED"),
    ("NCPL", 11.29, 87.49, "2026-10-19", "STOPPED"),
    ("NCPL", 16.54, 0.47, "2026-10-13", "STOPPED"),
    ("IMMR", -2.14, 100.00, "2026-10-14", "EXPIRED"),
    ("DNA", -9.24, 100.00, "2026-10-16", "EXPIRED"),
    ("BTCS", -10.37, 100.00, "2026-10-14", "EXPIRED"),
    ("MSS", -13.47, 100.00, "2026-09-30", "STOPPED"),
    ("NCPL", -14.17, 100.00, "2026-09-29", "STOPPED"),
    ("MEDS", -15.06, 100.00, "2026-10-02", "STOPPED"),
    ("BIRD", -16.39, 100.00, "2026-10-09", "STOPPED"),
    ("FEAM", -18.98, 100.00, "2026-10-19", "STOPPED"),
    ("MEDS", -18.99, 100.00, "2026-10-06", "STOPPED"),
    ("GDC", -25.52, 100.00, "2026-10-08", "STOPPED"),
    ("MOBX", -25.84, 100.00, "2026-10-09", "STOPPED"),
    ("MEDS", -29.15, 100.00, "2026-10-13", "STOPPED"),
    ("SDEV", -36.21, 100.00, "2026-10-12", "STOPPED"),
    ("TCRT", -38.58, 100.00, "2026-10-15", "STOPPED"),
    ("SDEV", -56.46, 100.00, "2026-10-12", "STOPPED"),
    # Unfunded, so no dollar effect; kept because it closed inside the window.
    ("USDE", -27.20, 0.00, "2026-10-20", "STOPPED"),
]

# ticker, entry, mark, peak, trail_pct, allocation, kind, confidence, call_date
OPEN = [
    ("SKYA", 2.15, 2.82, 2.82, 25.0, 100.00, "shadow", 50, "2026-10-12"),
    ("TBCH", 13.44, 15.48, 16.17, 25.0, None, "shadow", 65, "2026-10-12"),
    ("BYRN", 4.47, 5.11, 5.12, 25.0, 100.00, "shadow", 53, "2026-10-12"),
    ("CRNC", 8.77, 8.94, 9.21, 25.0, None, "shadow", 64, "2026-10-12"),
    ("DH", 1.12, 1.14, 1.17, 15.0, 100.00, "shadow", 49, "2026-10-19"),
    ("DSP", 12.78, 12.96, 13.52, 25.0, 100.00, "active", 66, "2026-10-09"),
    ("VRA", 5.76, 5.76, 6.12, 25.0, 71.40, "shadow", 46, "2026-10-13"),
    ("TCRT", 2.83, 2.83, 3.26, 25.0, 100.00, "active", 71, "2026-10-16"),
    ("QYLD", 18.65, 18.24, 18.70, 25.0, 100.00, "shadow", 91, "2026-10-05"),
    ("OPK", 1.67, 1.63, 1.67, 25.0, 100.00, "active", 61, "2026-10-16"),
    ("NCPL", 1.97, 1.85, 1.97, 15.0, 100.00, "shadow", 52, "2026-10-20"),
    ("AVAT", 1.36, 1.19, 1.39, 25.0, None, "shadow", 28, "2026-10-12"),
    ("AISP", 2.35, 2.00, 2.53, 25.0, 100.00, "active", 71, "2026-10-12"),
    ("XRPN", 17.85, 14.97, 17.85, 25.0, None, "shadow", 54, "2026-10-12"),
    ("GOSS", 10.24, 8.37, 10.24, 25.0, None, "shadow", 58, "2026-10-13"),
]

# What the live book reported at 2026-10-20 09:30 ET, before the loss.
EXPECTED = {"realized": 37.75, "allocated": 971.40, "cash": 66.35, "portfolio": 1060.73}


def review(ticker, *, decision, confidence, entry):
    return {
        "ticker": ticker,
        "asset_type": "stock",
        "variant": "squeeze",
        "decision": decision,
        "confidence": confidence,
        "entry": entry,
        "price": entry,
        "backend": "rebuilt",
        "notes": ["rebuilt from session output after live.db was lost"],
        "verdicts": {
            "judge": {
                "role": "judge",
                "decision": decision,
                "reason": "rebuilt after data loss; original verdict not recoverable",
            }
        },
    }


def main() -> int:
    config = load_config()
    db_path = Path(resolve_path(config, "db_path"))
    if db_path.exists():
        print(f"refusing to overwrite an existing database at {db_path}", file=sys.stderr)
        return 1
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with CallDatabase(db_path) as db:
        db.start_run("rebuild", session_reason="rebuild after data loss", screening_ran=False)
        for index, (ticker, pnl, alloc, date, status) in enumerate(CLOSED):
            # Entry 10.00 is a placeholder for closed rows: the dollar result is
            # allocation x pnl_pct, and the original entries are not recoverable
            # for every row. The percentage and the size ARE the record.
            call_id = db.insert_call(
                review(f"{ticker}~{index}", decision="SKIP", confidence=50, entry=10.0),
                run_id="rebuild",
                allocation_usd=alloc or None,
            )
            db.conn.execute(
                "UPDATE calls SET ticker = ?, status = ?, pnl_pct = ?, call_date = ?, "
                "closed_at = ?, close_reason = ?, current_price = ? WHERE id = ?",
                (
                    ticker,
                    status,
                    pnl,
                    date,
                    f"{date}T00:00:00+00:00",
                    "rebuilt after data loss — original close reason not recoverable",
                    round(10.0 * (1 + pnl / 100.0), 4),
                    call_id,
                ),
            )
        for ticker, entry, mark, peak, trail, alloc, kind, confidence, date in OPEN:
            call_id = db.insert_call(
                review(
                    ticker,
                    decision="TAKE" if kind == "active" else "SKIP",
                    confidence=confidence,
                    entry=entry,
                ),
                run_id="rebuild",
                allocation_usd=alloc,
                trail_floor_pct=trail,
                trail_atr_mult=None,
                sl_pct=config["tracker"].get("sl_pct"),
            )
            db.conn.execute(
                "UPDATE calls SET current_price = ?, peak_price = ?, pnl_pct = ?, "
                "call_date = ?, trail_pct = ? WHERE id = ?",
                (
                    mark,
                    peak,
                    round((mark - entry) / entry * 100.0, 4),
                    date,
                    trail,
                    call_id,
                ),
            )
        db.conn.commit()
        db.finish_run(
            "rebuild", {"hits": 0, "new_calls": len(CLOSED) + len(OPEN), "notes": "rebuild"}
        )

        from allocation import portfolio_state

        state = portfolio_state(db, config)

    print("REBUILT BOOK vs WHAT THE LIVE BOOK REPORTED AT 2026-10-20 09:30 ET")
    checks = [
        ("realized", state["realized_usd"], EXPECTED["realized"]),
        ("allocated", state["allocated_usd"], EXPECTED["allocated"]),
        ("cash", state["cash_usd"], EXPECTED["cash"]),
        ("portfolio", state["portfolio_value_usd"], EXPECTED["portfolio"]),
    ]
    worst = 0.0
    for name, got, want in checks:
        diff = got - want
        worst = max(worst, abs(diff))
        print(f"  {name:<11}rebuilt ${got:9.2f}  was ${want:9.2f}  diff ${diff:+.2f}")
    print(f"\n  largest difference ${worst:.2f}")
    print(
        f"  open positions funded: {len(state['positions'])}, tracked unfunded: "
        f"{len(state['unallocated_calls'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
