"""The push message names each open call's stop and how far it is away.

"How close is this to being cut" is the single most actionable fact about an
open position, and the run notification did not carry it — I had been adding it
by hand to every message, which is exactly the kind of thing that stops
happening the moment nobody is hand-writing them. The cycle now sends its own
summary, so the stop has to be in the formatter.
"""

from telegram_bot import format_run_notification


def _report(**over):
    update = {
        "ticker": "MEDS",
        "instrument": "call",
        "direction": "long",
        "entry_price": 4.30,
        "price": 3.26,
        "pnl_pct": -24.2,
        "kind": "shadow",
        "closed": False,
        "priced": True,
        "peak_price": 4.30,
        "trail_pct": 37.7,
        **over,
    }
    return {
        "run_id": "r1",
        "new_calls": [],
        "duplicates_skipped": [],
        "screening_ran": False,
        "session": {"as_of": "2026-10-06T02:40:00-04:00", "reason": "overnight"},
        "price_update": {"updates": [update], "missing_prices": [], "closed": 0},
    }


def test_the_stop_and_the_room_appear(config):
    text = format_run_notification(_report(), config)
    assert "stop 2.68" in text  # 4.30 x (1 - 0.377)
    assert "+21.7%" in text  # 3.26 is that far above 2.68


def test_a_call_with_no_trail_says_so_rather_than_inventing_one(config):
    text = format_run_notification(_report(trail_pct=None), config)
    assert "stop off" in text
    assert "stop 0" not in text


def test_an_unpriced_call_omits_the_room_but_keeps_the_stop(config):
    text = format_run_notification(_report(price=None, priced=False), config)
    assert "stop 2.68" in text


def test_a_ratcheted_stop_reflects_the_peak_not_the_entry(config):
    """VEEA: peak 5.94 on a 40.3% trail puts the stop above its 3.20 entry."""
    text = format_run_notification(
        _report(
            ticker="VEEA",
            entry_price=3.20,
            price=5.34,
            pnl_pct=66.8,
            peak_price=5.94,
            trail_pct=40.3,
        ),
        config,
    )
    assert "stop 3.55" in text


def test_the_account_block_uses_the_current_book_names(config):
    """ "Portfolio" predates the account/TAKE-only split and reads as neither."""
    report = _report()
    report["stats"] = {
        "account": {
            "portfolio_value_usd": 1235.18,
            "total_return_pct": 23.52,
            "account_usd": 1000.0,
            "allocated_pct": 40.0,
            "cash_usd": 799.16,
            "realized_usd": 199.16,
        },
        "take_only_book": {"portfolio_value_usd": 974.28, "total_return_pct": -2.57},
        "account_funds_all": True,
        "overall": {
            "total": 13,
            "open": 4,
            "right": 5,
            "wrong": 6,
            "neutral": 2,
            "hit_rate_pct": 38.5,
            "avg_pnl_pct": 18.09,
        },
        "portfolio": {
            "total_pnl_pct": 18.09,
            "calls_counted": 13,
            "equal_weight_pnl_pct_take_only": -12.86,
        },
    }
    text = format_run_notification(report, config)
    assert "Account (every call)" in text
    assert "$1,235.18" in text
    assert "realized" in text.lower()
    assert "TAKE only" in text
