"""The pre-market screen, and the session that selects it.

FinViz's public screener has no pre-market filter — `order=-premarketchange`
is silently ignored and falls back to ticker order, which is exactly the trap
this repo already learned about tokens. So the pre-market screen takes the
structural universe from FinViz (market cap, price, float, average volume:
facts that do not change overnight) and measures the actual pre-market move
from the tape.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from market_hours import session_state
from screener_guards import earliest_run_block
from screener_variants import variant_names, variant_sessions


def et(hour, minute=0, day=8):
    return datetime(2026, 10, day, hour, minute, tzinfo=ZoneInfo("America/New_York"))


@pytest.fixture()
def v2(config):
    config["screener"]["screener_version"] = "v2"
    return config


# --- session phase ------------------------------------------------------


@pytest.mark.parametrize(
    ("moment", "phase"),
    [
        (et(3, 30), "closed"),
        (et(4, 0), "premarket"),
        (et(9, 29), "premarket"),
        (et(9, 30), "regular"),
        (et(13, 0), "regular"),
        (et(16, 0), "regular"),
        (et(16, 1), "afterhours"),
        (et(20, 0), "afterhours"),
        (et(20, 1), "closed"),
        (et(11, 0, day=10), "closed"),  # Saturday
    ],
)
def test_the_session_phase(config, moment, phase):
    assert session_state(config, moment)["phase"] == phase


# --- the gate -----------------------------------------------------------


def test_the_gate_moved_to_eight_zurich(v2):
    """08:00 Zurich is 02:00 ET, before the pre-market tape opens, so the
    extended-hours session check becomes the binding constraint — which is the
    point: the operator wants a morning scan, not a 3am one."""
    zurich = ZoneInfo("Europe/Zurich")
    assert earliest_run_block(v2, now=datetime(2026, 10, 8, 7, 59, tzinfo=zurich)) is not None
    assert earliest_run_block(v2, now=datetime(2026, 10, 8, 8, 0, tzinfo=zurich)) is None
    assert earliest_run_block(v2, now=datetime(2026, 10, 8, 10, 30, tzinfo=zurich)) is None


def test_v1_still_has_no_gate(config):
    assert (
        earliest_run_block(
            config, now=datetime(2026, 10, 8, 3, 0, tzinfo=ZoneInfo("Europe/Zurich"))
        )
        is None
    )


# --- variant selection by session --------------------------------------


def test_the_premarket_variant_only_runs_premarket(v2):
    assert variant_sessions(v2, "premarket_gap") == ["premarket"]
    assert variant_names(v2, phase="premarket") == ["premarket_gap"]


def test_the_relative_volume_variants_do_not_run_premarket(v2):
    """squeeze and momentum_breakout rank on relative volume and "up today",
    neither of which exists before the open."""
    premarket = variant_names(v2, phase="premarket")
    assert "squeeze" not in premarket
    assert "momentum_breakout" not in premarket


def test_the_regular_session_runs_the_relative_volume_variants(v2):
    names = variant_names(v2, phase="regular")
    assert set(names) == {"squeeze", "momentum_breakout"}


def test_after_hours_runs_them_too(v2):
    assert set(variant_names(v2, phase="afterhours")) == {"squeeze", "momentum_breakout"}


def test_no_phase_means_every_variant(v2):
    assert set(variant_names(v2)) == {"squeeze", "momentum_breakout", "premarket_gap"}


def test_v1_variants_have_no_session_restriction(config):
    """v1 is frozen; nothing about it changes because v2 grew a phase."""
    for name in ("squeeze", "momentum_breakout", "etf_momentum"):
        assert variant_sessions(config, name) is None
    assert set(variant_names(config, phase="premarket")) == {
        "squeeze",
        "momentum_breakout",
        "etf_momentum",
    }


# --- the premarket filter ----------------------------------------------


def test_the_premarket_variant_is_structural_only(v2):
    """Nothing in its filters may depend on today's tape, because there is no
    today's tape when it runs."""
    from screener_variants import variant_filters

    filters = variant_filters(v2, "premarket_gap")
    for forbidden in ("ta_perf_dup", "sh_relvol", "ta_change"):
        assert not [token for token in filters if token.startswith(forbidden)]
    assert "cap_smallunder" in filters
    assert "sh_price_1to20" in filters


def test_a_gapping_name_on_real_volume_survives(v2):
    from fetch_screener import apply_premarket_filter

    rows = [{"ticker": "GAPU", "price": 4.00, "avg_volume": 1_000_000}]
    moves = {"GAPU": {"gap_pct": 12.0, "volume_pct_of_adv": 25.0, "last": 4.48}}
    kept, skipped = apply_premarket_filter(rows, v2, "premarket_gap", moves=moves)
    assert [hit["ticker"] for hit in kept] == ["GAPU"]
    assert kept[0]["premarket_gap_pct"] == 12.0
    assert skipped == []


def test_the_measured_gap_becomes_the_hits_change(v2):
    """So the +25% chase cap reads the pre-market move, not yesterday's."""
    from fetch_screener import apply_premarket_filter

    rows = [{"ticker": "GAPU", "price": 4.00, "avg_volume": 1_000_000, "change_pct": -3.0}]
    moves = {"GAPU": {"gap_pct": 12.0, "volume_pct_of_adv": 25.0, "last": 4.48}}
    kept, _ = apply_premarket_filter(rows, v2, "premarket_gap", moves=moves)
    assert kept[0]["change_pct"] == 12.0


def test_the_premarket_print_becomes_the_entry_price(v2):
    """A pre-market call entered at yesterday's close is priced at a level
    nobody can get."""
    from fetch_screener import apply_premarket_filter

    rows = [{"ticker": "GAPU", "price": 4.00, "avg_volume": 1_000_000}]
    moves = {"GAPU": {"gap_pct": 12.0, "volume_pct_of_adv": 25.0, "last": 4.48}}
    kept, _ = apply_premarket_filter(rows, v2, "premarket_gap", moves=moves)
    assert kept[0]["price"] == 4.48
    assert kept[0]["prior_close"] == 4.00


def test_a_small_gap_is_dropped(v2):
    from fetch_screener import apply_premarket_filter

    rows = [{"ticker": "QUIET", "price": 4.00, "avg_volume": 1_000_000}]
    moves = {"QUIET": {"gap_pct": 1.5, "volume_pct_of_adv": 40.0, "last": 4.06}}
    kept, skipped = apply_premarket_filter(rows, v2, "premarket_gap", moves=moves)
    assert kept == []
    assert "gap" in skipped[0]["reason"]


def test_a_gap_on_no_volume_is_dropped(v2):
    """A 20% premarket print on 1% of ADV is one order, not demand."""
    from fetch_screener import apply_premarket_filter

    rows = [{"ticker": "THIN", "price": 4.00, "avg_volume": 1_000_000}]
    moves = {"THIN": {"gap_pct": 20.0, "volume_pct_of_adv": 1.0, "last": 4.80}}
    kept, skipped = apply_premarket_filter(rows, v2, "premarket_gap", moves=moves)
    assert kept == []
    assert "volume" in skipped[0]["reason"]


def test_a_name_with_no_premarket_tape_is_dropped_quietly(v2):
    """No pre-market print is the normal case for most of the universe; it is
    not a finding, so it does not clutter the report."""
    from fetch_screener import apply_premarket_filter

    rows = [{"ticker": "DARK", "price": 4.00, "avg_volume": 1_000_000}]
    kept, skipped = apply_premarket_filter(rows, v2, "premarket_gap", moves={})
    assert kept == []
    assert skipped == []


def test_a_gap_down_is_not_a_long_setup(v2):
    from fetch_screener import apply_premarket_filter

    rows = [{"ticker": "DUMP", "price": 4.00, "avg_volume": 1_000_000}]
    moves = {"DUMP": {"gap_pct": -18.0, "volume_pct_of_adv": 60.0, "last": 3.28}}
    kept, skipped = apply_premarket_filter(rows, v2, "premarket_gap", moves=moves)
    assert kept == []
    assert "gap" in skipped[0]["reason"]


def test_the_universe_is_capped_before_any_tape_is_fetched(v2):
    """One yfinance call per name: an unbounded universe would make a
    pre-market scan slower than the pre-market session."""
    from fetch_screener import premarket_universe

    rows = [{"ticker": f"T{index:03d}", "volume": index} for index in range(200)]
    capped = premarket_universe(rows, v2, "premarket_gap")
    assert len(capped) == 60
    # Ordered by the most-traded names: liquidity is what makes a gap real.
    assert capped[0]["ticker"] == "T199"


def test_a_regular_variant_has_no_premarket_block(v2):
    from fetch_screener import premarket_spec

    assert premarket_spec(v2, "squeeze") == {}
    assert premarket_spec(v2, "premarket_gap")["min_gap_pct"] == 5.0
