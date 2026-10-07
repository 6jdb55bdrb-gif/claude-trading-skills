"""Outcome tracking: what every judged call actually did, TAKE and SKIP alike.

This is the scorecard the version experiment is for. It is deliberately
mechanical — fixed horizons, one stop line, no judgement — because the whole
point is to measure the judgement that happened upstream.
"""

import pytest
from outcome_tracker import (
    evaluate_outcome,
    fill_outcomes,
    settled_return,
)

from conftest import review_payload


def bars(*rows):
    """``("2026-10-08", low, close)`` triples, oldest first."""
    return [{"date": date, "low": low, "close": close} for date, low, close in rows]


FIVE_UP = bars(
    ("2026-10-08", 9.8, 10.5),
    ("2026-10-09", 10.1, 11.0),
    ("2026-10-12", 10.7, 11.5),
    ("2026-10-13", 11.0, 12.0),
    ("2026-10-14", 11.4, 13.0),
)


# --- the horizons ---------------------------------------------------------


def test_returns_are_measured_at_one_three_and_five_sessions():
    out = evaluate_outcome(entry=10.0, sl_price=8.0, bars=FIVE_UP)
    assert out["ret_1d"] == 5.0
    assert out["ret_3d"] == 15.0
    assert out["ret_5d"] == 30.0
    assert out["stopped_out"] is False
    assert out["stopped_out_date"] is None


def test_horizons_count_sessions_not_calendar_days():
    """2026-10-10 is a Saturday: +3 sessions from Thursday is Tuesday the 13th."""
    out = evaluate_outcome(entry=10.0, sl_price=8.0, bars=FIVE_UP)
    assert out["ret_3d"] == 15.0  # the 2026-10-12 close, the third session


def test_a_horizon_that_has_not_elapsed_stays_empty():
    """Two sessions in, the 3- and 5-day columns are unknown, not zero."""
    out = evaluate_outcome(entry=10.0, sl_price=8.0, bars=FIVE_UP[:2])
    assert out["ret_1d"] == 5.0
    assert out["ret_3d"] is None
    assert out["ret_5d"] is None
    assert out["complete"] is False


def test_a_finished_call_is_marked_complete():
    assert evaluate_outcome(entry=10.0, sl_price=8.0, bars=FIVE_UP)["complete"] is True


def test_no_sessions_yet_means_nothing_is_claimed():
    out = evaluate_outcome(entry=10.0, sl_price=8.0, bars=[])
    assert out["ret_1d"] is None and out["stopped_out"] is False and out["complete"] is False


# --- the stop ------------------------------------------------------------


def test_a_low_through_the_stop_closes_the_call_at_the_stop():
    """Day 2 trades down to 7.50 with the stop at 8.00: the position is out at
    8.00, so every horizon from there on is the stop's -20%, not the close."""
    rows = bars(
        ("2026-10-08", 9.8, 10.5),
        ("2026-10-09", 7.5, 9.0),
        ("2026-10-12", 9.0, 14.0),
        ("2026-10-13", 13.0, 15.0),
        ("2026-10-14", 14.0, 16.0),
    )
    out = evaluate_outcome(entry=10.0, sl_price=8.0, bars=rows)
    assert out["stopped_out"] is True
    assert out["stopped_out_date"] == "2026-10-09"
    assert out["ret_1d"] == 5.0  # the session before the stop is real
    assert out["ret_3d"] == -20.0  # out at the stop; the +40% close is not ours
    assert out["ret_5d"] == -20.0
    assert out["complete"] is True


def test_a_stop_on_the_first_session_prices_every_horizon_at_the_stop():
    rows = bars(("2026-10-08", 7.0, 7.2), ("2026-10-09", 7.0, 20.0))
    out = evaluate_outcome(entry=10.0, sl_price=8.0, bars=rows)
    assert (out["ret_1d"], out["ret_3d"], out["ret_5d"]) == (-20.0, -20.0, -20.0)
    assert out["stopped_out_date"] == "2026-10-08"


def test_a_low_exactly_on_the_stop_counts_as_stopped():
    out = evaluate_outcome(entry=10.0, sl_price=8.0, bars=bars(("2026-10-08", 8.0, 9.0)))
    assert out["stopped_out"] is True


def test_a_low_just_above_the_stop_does_not():
    out = evaluate_outcome(entry=10.0, sl_price=8.0, bars=bars(("2026-10-08", 8.01, 9.0)))
    assert out["stopped_out"] is False
    assert out["ret_1d"] == -10.0


def test_a_call_without_a_stop_rides_the_closes():
    """`sl_pct: null` means no fixed stop, so the tracker measures the move."""
    rows = bars(("2026-10-08", 2.0, 3.0), ("2026-10-09", 2.0, 2.5), ("2026-10-12", 1.0, 1.5))
    out = evaluate_outcome(entry=10.0, sl_price=None, bars=rows)
    assert out["stopped_out"] is False
    assert out["ret_3d"] == -85.0


def test_a_missing_low_cannot_stop_a_call():
    """A provider that returns no low is a data gap, not a stop-out."""
    rows = [{"date": "2026-10-08", "low": None, "close": 9.0}]
    out = evaluate_outcome(entry=10.0, sl_price=8.0, bars=rows)
    assert out["stopped_out"] is False
    assert out["ret_1d"] == -10.0


def test_an_unusable_entry_yields_nothing_rather_than_a_division_error():
    assert evaluate_outcome(entry=0, sl_price=8.0, bars=FIVE_UP)["ret_1d"] is None
    assert evaluate_outcome(entry=None, sl_price=8.0, bars=FIVE_UP)["ret_5d"] is None


def test_a_short_call_is_measured_the_other_way_up():
    """allow_short is false today, but a put's PnL still has to read correctly
    if it is ever turned on."""
    rows = bars(("2026-10-08", 8.0, 9.0))
    out = evaluate_outcome(entry=10.0, sl_price=None, bars=rows, direction="short")
    assert out["ret_1d"] == 10.0


# --- the settled return --------------------------------------------------


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"ret_1d": 5.0, "ret_3d": 10.0, "ret_5d": 30.0}, 30.0),
        ({"ret_1d": 5.0, "ret_3d": 10.0, "ret_5d": None}, 10.0),
        ({"ret_1d": 5.0, "ret_3d": None, "ret_5d": None}, 5.0),
        ({"ret_1d": None, "ret_3d": None, "ret_5d": None}, None),
        ({"ret_1d": 0.0, "ret_3d": None, "ret_5d": None}, 0.0),
    ],
)
def test_the_settled_return_is_the_longest_horizon_that_elapsed(row, expected):
    assert settled_return(row) == expected


# --- filling the database ------------------------------------------------


def _call(db, ticker, *, entry=10.0, decision="TAKE", date="2026-10-07", version="v2"):
    payload = review_payload(ticker, entry=entry, decision=decision)
    payload["hit"] = {"ticker": ticker, "screener_version": version}
    return db.insert_call(payload, run_id="r1", now=f"{date}T20:00:00+00:00", sl_pct=20.0)


def test_filling_writes_the_returns_onto_the_call(tmp_db, config):
    call_id = _call(tmp_db, "WIN")
    result = fill_outcomes(tmp_db, config, bars={"WIN": FIVE_UP}, as_of="2026-10-15")
    assert result["updated"] == 1
    row = dict(tmp_db.conn.execute("SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone())
    assert (row["ret_1d"], row["ret_3d"], row["ret_5d"]) == (5.0, 15.0, 30.0)
    assert row["stopped_out"] == 0
    assert row["outcome_updated_at"]


def test_skips_are_tracked_exactly_like_takes(tmp_db, config):
    """The Judge's record is only readable if what it refused is measured too."""
    _call(tmp_db, "SHDW", decision="SKIP")
    fill_outcomes(tmp_db, config, bars={"SHDW": FIVE_UP}, as_of="2026-10-15")
    row = tmp_db.conn.execute("SELECT ret_5d, kind FROM calls WHERE ticker = 'SHDW'").fetchone()
    assert row["kind"] == "shadow"
    assert row["ret_5d"] == 30.0


def test_a_stopped_call_records_the_stop_date(tmp_db, config):
    _call(tmp_db, "STOPD")
    rows = bars(("2026-10-08", 7.0, 7.5), ("2026-10-09", 7.0, 7.5))
    fill_outcomes(tmp_db, config, bars={"STOPD": rows}, as_of="2026-10-15")
    row = tmp_db.conn.execute(
        "SELECT stopped_out, stopped_out_date, ret_5d FROM calls WHERE ticker = 'STOPD'"
    ).fetchone()
    assert row["stopped_out"] == 1
    assert row["stopped_out_date"] == "2026-10-08"
    assert row["ret_5d"] == -20.0


def test_bars_before_the_call_are_ignored(tmp_db, config):
    """A call made on the 7th cannot be credited with the 6th's close."""
    _call(tmp_db, "PRE", date="2026-10-07")
    rows = bars(("2026-10-05", 1.0, 1.0), ("2026-10-06", 1.0, 2.0), ("2026-10-08", 9.9, 11.0))
    fill_outcomes(tmp_db, config, bars={"PRE": rows}, as_of="2026-10-15")
    row = tmp_db.conn.execute("SELECT ret_1d FROM calls WHERE ticker = 'PRE'").fetchone()
    assert row["ret_1d"] == 10.0


def test_the_calls_own_session_is_day_zero(tmp_db, config):
    """The entry is the price at scan, so the scan day's own close is not +1d."""
    _call(tmp_db, "ZERO", date="2026-10-07")
    rows = bars(("2026-10-07", 9.0, 9.5), ("2026-10-08", 9.9, 11.0))
    fill_outcomes(tmp_db, config, bars={"ZERO": rows}, as_of="2026-10-15")
    row = tmp_db.conn.execute(
        "SELECT ret_1d, stopped_out FROM calls WHERE ticker = 'ZERO'"
    ).fetchone()
    assert row["ret_1d"] == 10.0
    assert row["stopped_out"] == 0


def test_todays_forming_bar_is_not_treated_as_a_close(tmp_db, config):
    """Mid-session the last bar has no final close; waiting a day costs nothing
    and a wrong +1d return would never be corrected."""
    _call(tmp_db, "FORM", date="2026-10-07")
    rows = bars(("2026-10-08", 9.9, 11.0))
    result = fill_outcomes(tmp_db, config, bars={"FORM": rows}, as_of="2026-10-08")
    row = tmp_db.conn.execute("SELECT ret_1d FROM calls WHERE ticker = 'FORM'").fetchone()
    assert row["ret_1d"] is None
    assert result["updated"] == 0


def test_a_complete_call_is_not_refetched(tmp_db, config):
    _call(tmp_db, "DONE")
    fill_outcomes(tmp_db, config, bars={"DONE": FIVE_UP}, as_of="2026-10-15")
    again = fill_outcomes(tmp_db, config, bars={"DONE": FIVE_UP}, as_of="2026-10-16")
    assert again["pending"] == 0
    assert again["updated"] == 0


def test_a_stopped_call_is_not_refetched_either(tmp_db, config):
    """Stopped is final: the position is closed, so later prices are not ours."""
    _call(tmp_db, "OUT")
    rows = bars(("2026-10-08", 7.0, 7.5))
    fill_outcomes(tmp_db, config, bars={"OUT": rows}, as_of="2026-10-09")
    assert fill_outcomes(tmp_db, config, bars={"OUT": FIVE_UP}, as_of="2026-10-20")["pending"] == 0
    row = tmp_db.conn.execute("SELECT ret_5d FROM calls WHERE ticker = 'OUT'").fetchone()
    assert row["ret_5d"] == -20.0


def test_an_incomplete_call_is_picked_up_again(tmp_db, config):
    _call(tmp_db, "PART")
    fill_outcomes(tmp_db, config, bars={"PART": FIVE_UP[:2]}, as_of="2026-10-10")
    assert fill_outcomes(tmp_db, config, bars={"PART": FIVE_UP}, as_of="2026-10-15")["updated"] == 1
    row = tmp_db.conn.execute("SELECT ret_5d FROM calls WHERE ticker = 'PART'").fetchone()
    assert row["ret_5d"] == 30.0


def test_a_ticker_with_no_bars_is_reported_not_guessed(tmp_db, config):
    _call(tmp_db, "DARK")
    result = fill_outcomes(tmp_db, config, bars={}, as_of="2026-10-15")
    assert result["missing"] == ["DARK"]
    assert result["updated"] == 0
