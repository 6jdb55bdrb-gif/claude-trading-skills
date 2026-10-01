"""The trailing stop is scaled to the instrument's own daily range.

A fixed 15% trail is narrower than one session on most of this universe: six
of the first ten calls carried an ATR above 13% of entry and four above 22%.
A trail inside the ATR is hit by noise rather than by thesis failure, so the
distance is now ``max(floor, mult x ATR/entry)``, resolved once at entry and
stored on the call. The floor still governs a quiet name, and a call with no
ATR to scale from keeps the floor exactly as before.
"""

import pytest
from call_db import STATUS_OPEN, STATUS_STOPPED, resolve_trail_pct
from price_update import update_open_calls

from conftest import review_payload


def _cfg(config, *, floor=15.0, mult=1.5):
    return {
        **config,
        "tracker": {
            **config["tracker"],
            "trailing_stop_pct": floor,
            "trailing_stop_atr_mult": mult,
        },
    }


def _open(db, ticker="AAA", entry=10.0, atr=None, *, floor=15.0, mult=1.5):
    review = review_payload(ticker, entry=entry)
    if atr is not None:
        review["hit"] = {"ticker": ticker, "atr": atr, "price": entry}
    return db.insert_call(
        review,
        run_id="r1",
        allocation_usd=100.0,
        trail_floor_pct=floor,
        trail_atr_mult=mult,
    )


def _walk(db, config, ticker, path):
    for price in path:
        update_open_calls(db, config, prices={ticker: price})


# --- the resolver ----------------------------------------------------------


@pytest.mark.parametrize(
    "entry, atr, expected",
    [
        (10.0, 1.0, 15.0),  # ATR 10% -> 1.5x = 15%, exactly the floor
        (10.0, 0.5, 15.0),  # a quiet name stays on the floor
        (3.20, 0.86, 40.3),  # VEEA: ATR 26.9% of entry
        (4.30, 1.08, 37.7),  # MEDS: ATR 25.1% of entry
        (3.20, 0.43, 20.2),  # SDEV: ATR 13.4% of entry
    ],
)
def test_the_trail_is_the_wider_of_the_floor_and_the_atr_multiple(entry, atr, expected):
    assert resolve_trail_pct(entry, atr, floor_pct=15.0, atr_mult=1.5) == expected


@pytest.mark.parametrize("atr", [None, 0, 0.0, -1.0, "", "n/a"])
def test_an_unusable_atr_falls_back_to_the_floor(atr):
    """Never widen a stop on a number we cannot trust, and never crash on one."""
    assert resolve_trail_pct(10.0, atr, floor_pct=15.0, atr_mult=1.5) == 15.0


def test_a_missing_entry_price_falls_back_to_the_floor():
    assert resolve_trail_pct(0, 1.0, floor_pct=15.0, atr_mult=1.5) == 15.0
    assert resolve_trail_pct(None, 1.0, floor_pct=15.0, atr_mult=1.5) == 15.0


def test_a_null_multiplier_disables_scaling_entirely():
    """Setting the multiplier to null must restore the old fixed behaviour."""
    assert resolve_trail_pct(3.20, 0.86, floor_pct=15.0, atr_mult=None) == 15.0


def test_a_null_floor_switches_the_trail_off_entirely():
    """The floor is the master switch: the multiplier only widens a live trail."""
    assert resolve_trail_pct(3.20, 0.86, floor_pct=None, atr_mult=1.5) is None


def test_a_sign_slip_in_the_settings_never_removes_the_stop():
    """-15 means 15. Only an explicit null disables the trail."""
    assert resolve_trail_pct(10.0, 1.0, floor_pct=-15.0, atr_mult=-1.5) == 15.0
    assert resolve_trail_pct(3.20, 0.86, floor_pct=-15.0, atr_mult=-1.5) == 40.3


def test_the_floor_governs_whether_a_trail_exists_at_all(tmp_db, config):
    """A call made with the trail switched off stores none and never stops."""
    call_id = _open(tmp_db, entry=3.91, atr=1.13, floor=None)
    assert tmp_db.call(call_id)["trail_pct"] is None
    _walk(tmp_db, _cfg(config, floor=None), "AAA", [0.40])
    assert tmp_db.call(call_id)["status"] == STATUS_OPEN


# --- storage ---------------------------------------------------------------


def test_the_trail_is_resolved_once_at_entry_and_stored(tmp_db, config):
    call_id = _open(tmp_db, entry=3.20, atr=0.86)
    assert tmp_db.call(call_id)["trail_pct"] == 40.3


def test_a_call_with_no_screener_atr_stores_the_floor(tmp_db, config):
    call_id = _open(tmp_db, entry=10.0, atr=None)
    assert tmp_db.call(call_id)["trail_pct"] == 15.0


def test_the_stored_trail_does_not_move_when_the_price_does(tmp_db, config):
    """The distance is fixed at entry; only the high-water mark ratchets."""
    call_id = _open(tmp_db, entry=3.20, atr=0.86)
    _walk(tmp_db, _cfg(config), "AAA", [4.00, 4.50])
    row = tmp_db.call(call_id)
    assert row["trail_pct"] == 40.3
    assert row["peak_price"] == 4.50


# --- behaviour -------------------------------------------------------------


def test_a_wide_atr_name_survives_a_drop_that_the_old_floor_would_have_cut(tmp_db, config):
    """MEDS 3.91 with ATR 1.13: -18.9% closed it on the floor, and should not now."""
    call_id = _open(tmp_db, entry=3.91, atr=1.13)
    _walk(tmp_db, _cfg(config), "AAA", [3.17])  # -18.9%
    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_OPEN
    assert row["trail_pct"] == 43.4


def test_a_wide_atr_name_still_stops_once_the_wider_trail_is_breached(tmp_db, config):
    call_id = _open(tmp_db, entry=3.91, atr=1.13)
    _walk(tmp_db, _cfg(config), "AAA", [2.00])  # -48.8%, past the 43.4% trail
    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_STOPPED
    assert "43.4%" in row["close_reason"]


def test_a_quiet_name_behaves_exactly_as_it_did_on_the_fixed_trail(tmp_db, config):
    """The floor is unchanged, so a low-ATR call must not drift."""
    call_id = _open(tmp_db, entry=10.0, atr=0.5)
    _walk(tmp_db, _cfg(config), "AAA", [9.5, 8.4])
    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_STOPPED
    assert row["pnl_pct"] == -16.0
    assert "15%" in row["close_reason"]


def test_the_wider_trail_still_ratchets_from_the_peak(tmp_db, config):
    """Up 50%, then a fade past the ATR trail: the exit banks what is left."""
    call_id = _open(tmp_db, entry=3.20, atr=0.43)  # trail 20.2%
    _walk(tmp_db, _cfg(config), "AAA", [4.80, 3.80])  # peak 4.80, -20.8% off it
    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_STOPPED
    assert row["peak_price"] == 4.80
    assert round(row["pnl_pct"], 1) == 18.8  # still green, which is the point


def test_turning_the_multiplier_off_reproduces_the_old_stop(tmp_db, config):
    """The multiplier is read at entry, so it must be off when the call is made."""
    call_id = _open(tmp_db, entry=3.91, atr=1.13, mult=None)
    assert tmp_db.call(call_id)["trail_pct"] == 15.0
    _walk(tmp_db, _cfg(config, mult=None), "AAA", [3.17])
    assert tmp_db.call(call_id)["status"] == STATUS_STOPPED


# --- migration -------------------------------------------------------------


def _make_legacy(db, _call_id=None):
    """Reopen the book as one written before the column existed.

    Nulling the value is NOT the same thing: a NULL trail on a current schema
    means the call was made with the stop switched off, and the migration must
    leave it alone. Only a missing column is a legacy book, so the column is
    removed by rebuilding the table the way the previous schema declared it.
    """
    cols = [row[1] for row in db.conn.execute("PRAGMA table_info(calls)") if row[1] != "trail_pct"]
    names = ", ".join(cols)
    db.conn.executescript(
        f"""
        PRAGMA foreign_keys=off;
        CREATE TABLE calls_legacy AS SELECT {names} FROM calls;
        DROP TABLE calls;
        ALTER TABLE calls_legacy RENAME TO calls;
        """
    )
    db.conn.commit()
    return type(db)(db.path)


def test_a_legacy_row_without_a_trail_is_backfilled_from_its_screener_atr(tmp_db, config):
    """Reopening an older book must not leave open calls on a mis-sized stop."""
    call_id = _open(tmp_db, entry=3.20, atr=0.86)
    reopened = _make_legacy(tmp_db)
    assert reopened.call(call_id)["trail_pct"] == 40.3


def test_a_legacy_row_with_no_atr_at_all_is_backfilled_to_the_floor(tmp_db, config):
    call_id = _open(tmp_db, entry=10.0, atr=None)
    reopened = _make_legacy(tmp_db)
    assert reopened.call(call_id)["trail_pct"] == 15.0


def test_a_deliberately_untrailed_call_is_left_alone_on_every_reopen(tmp_db, config):
    """The migration must not switch a stop back on behind the operator."""
    call_id = _open(tmp_db, entry=3.91, atr=1.13, floor=None)
    assert type(tmp_db)(tmp_db.path).call(call_id)["trail_pct"] is None
    assert type(tmp_db)(tmp_db.path).call(call_id)["trail_pct"] is None


def test_the_backfill_runs_once_and_not_again(tmp_db, config):
    """After the column exists, a cleared trail stays cleared."""
    call_id = _open(tmp_db, entry=3.20, atr=0.86)
    reopened = _make_legacy(tmp_db)
    assert reopened.call(call_id)["trail_pct"] == 40.3
    reopened.conn.execute("UPDATE calls SET trail_pct = NULL WHERE id = ?", (call_id,))
    reopened.conn.commit()
    assert type(tmp_db)(tmp_db.path).call(call_id)["trail_pct"] is None


def test_the_stored_trail_wins_over_the_config_floor_at_price_time(tmp_db, config):
    """A book written under one setting keeps its geometry when the config moves."""
    call_id = _open(tmp_db, entry=3.91, atr=1.13)  # stored 43.4
    _walk(tmp_db, _cfg(config, floor=15.0, mult=1.5), "AAA", [3.17])
    assert tmp_db.call(call_id)["status"] == STATUS_OPEN


# --- reporting -------------------------------------------------------------


def test_the_report_names_each_call_s_own_trail(tmp_db, config):
    """With the distance varying per position, the operator must be able to see it."""
    from price_update import format_updates

    _open(tmp_db, "WIDE", entry=3.20, atr=0.86)  # 40.3%
    _open(tmp_db, "TIGHT", entry=10.0, atr=0.5)  # floor, 15%
    result = update_open_calls(tmp_db, _cfg(config), prices={"WIDE": 3.30, "TIGHT": 10.1})
    text = format_updates(result)
    assert "trail=40.3%" in text
    assert "trail=15%" in text


def test_the_report_says_off_when_a_call_carries_no_trail(tmp_db, config):
    from price_update import format_updates

    _open(tmp_db, "NONE", entry=3.20, atr=0.86, floor=None)
    result = update_open_calls(tmp_db, _cfg(config, floor=None), prices={"NONE": 3.30})
    assert "trail=off" in format_updates(result)
