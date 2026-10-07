"""The v2 explosion-signals layer: nine bonuses, four hard skips, one cap.

Two rules shape every test here:

* a signal whose source failed records n/a and scores nothing. A missing
  source that scored 0 would be indistinguishable from a source that looked
  and found nothing, and those are different facts.
* the layer ranks setups, it does not manufacture them. Hence the cap, and
  hence the hard skips that no amount of bonus can outvote.
"""

import pytest
from explosion_signals import (
    SIGNAL_ORDER,
    evaluate,
    signal_summary,
    signals_enabled,
)


@pytest.fixture()
def v2(config):
    config["screener"]["screener_version"] = "v2"
    return config


def hit(**overrides):
    out = {
        "ticker": "EXPL",
        "price": 4.00,
        "volume": 5_000_000,
        "avg_volume": 1_000_000,
        "float_shares": 20_000_000,
        "rel_volume": 3.0,
        "short_ratio": 1.0,
        "inst_own_pct": 45.0,
        "industry": "Biotechnology",
        "change_pct": 8.0,
        "screener_version": "v2",
    }
    out.update(overrides)
    return out


def points(result, name):
    return result["signals"][name]["points"]


def status(result, name):
    return result["signals"][name]["status"]


# --- the layer as a whole -------------------------------------------------


def test_v1_has_no_signals_layer(config):
    assert signals_enabled(config) is False
    result = evaluate(hit(screener_version="v1"), config)
    assert result["enabled"] is False
    assert result["bonus"] == 0
    assert result["signals"] == {}
    assert result["hard_skips"] == []


def test_v2_runs_the_layer(v2):
    assert signals_enabled(v2) is True
    result = evaluate(hit(), v2)
    assert result["enabled"] is True
    assert set(result["signals"]) == set(SIGNAL_ORDER)


def test_the_layer_can_be_switched_off_without_removing_it(v2):
    v2["screener"]["versions"]["v2"]["explosion_signals"]["enabled"] = False
    assert signals_enabled(v2) is False
    assert evaluate(hit(), v2)["bonus"] == 0


def test_a_hit_from_v1_is_not_scored_during_a_v2_run(v2):
    """Signals belong to the generation that produced the call."""
    result = evaluate(hit(screener_version="v1"), v2)
    assert result["enabled"] is False


# --- float rotation (from the screener row, no network) ------------------


@pytest.mark.parametrize(
    ("volume", "float_shares", "expected"),
    [
        (5_000_000, 20_000_000, 0),  # 0.25x
        (9_900_000, 20_000_000, 0),  # 0.495x
        (10_000_000, 20_000_000, 5),  # exactly 0.50x
        (15_000_000, 20_000_000, 5),  # 0.75x
        (20_000_000, 20_000_000, 10),  # one full rotation
        (60_000_000, 20_000_000, 10),  # 3x, still 10 — rungs do not stack
    ],
)
def test_float_rotation_rungs(v2, volume, float_shares, expected):
    result = evaluate(hit(volume=volume, float_shares=float_shares), v2)
    assert points(result, "float_rotation") == expected


def test_float_rotation_records_the_multiple_it_scored_on(v2):
    result = evaluate(hit(volume=17_700_620, float_shares=15_790_000), v2)
    assert result["signals"]["float_rotation"]["value"] == 1.12
    assert points(result, "float_rotation") == 10


def test_float_rotation_without_a_float_is_not_assumed(v2):
    """FinViz publishes no float for many names; a guess would be a lie."""
    result = evaluate(hit(float_shares=None), v2)
    assert status(result, "float_rotation") == "n/a"
    assert points(result, "float_rotation") == 0


def test_a_zero_float_does_not_divide_by_zero(v2):
    result = evaluate(hit(float_shares=0), v2)
    assert status(result, "float_rotation") == "n/a"


# --- catalyst recency (replaces the role catalyst penalty in v2) ---------


def test_a_filing_inside_the_window_pays(v2):
    result = evaluate(hit(), v2, data={"catalyst_hours_ago": 6.0, "catalyst_form": "8-K"})
    assert points(result, "catalyst_recency") == 10
    assert "8-K" in result["signals"]["catalyst_recency"]["detail"]


def test_a_filing_on_the_window_edge_pays(v2):
    result = evaluate(hit(), v2, data={"catalyst_hours_ago": 24.0, "catalyst_form": "8-K"})
    assert points(result, "catalyst_recency") == 10


def test_an_older_filing_is_charged_as_no_catalyst(v2):
    """Two days stale is not a catalyst for a one-day move."""
    result = evaluate(hit(), v2, data={"catalyst_hours_ago": 50.0, "catalyst_form": "8-K"})
    assert points(result, "catalyst_recency") == -15


def test_no_catalyst_found_is_charged_fifteen(v2):
    result = evaluate(hit(), v2, data={"catalyst_found": False})
    assert points(result, "catalyst_recency") == -15
    assert status(result, "catalyst_recency") == "ok"


def test_an_unreachable_edgar_charges_nothing(v2):
    """This is the difference the n/a status exists for: EDGAR being down is
    not evidence that the company filed nothing."""
    result = evaluate(hit(), v2, data={"catalyst_found": None})
    assert points(result, "catalyst_recency") == 0
    assert status(result, "catalyst_recency") == "n/a"


def test_a_screener_headline_counts_as_a_catalyst_when_edgar_is_silent(v2):
    """FinViz carries the news tape; a fresh headline is material news even
    when nothing was filed with the SEC."""
    result = evaluate(
        hit(catalyst_headline="FDA clears lead program"), v2, data={"news_hours_ago": 3.0}
    )
    assert points(result, "catalyst_recency") == 10


# --- squeeze pressure ----------------------------------------------------


def test_days_to_cover_at_the_threshold_pays(v2):
    assert points(evaluate(hit(short_ratio=3.0), v2), "short_squeeze_pressure") == 5


def test_days_to_cover_below_the_threshold_does_not(v2):
    assert points(evaluate(hit(short_ratio=2.9), v2), "short_squeeze_pressure") == 0


def test_a_hard_borrow_pays_on_its_own(v2):
    """ "and/or": either side of the lending market saying the same thing."""
    result = evaluate(hit(short_ratio=1.0), v2, data={"borrow_fee_pct": 42.0})
    assert points(result, "short_squeeze_pressure") == 5


def test_both_together_still_pay_once(v2):
    result = evaluate(hit(short_ratio=6.0), v2, data={"borrow_fee_pct": 42.0})
    assert points(result, "short_squeeze_pressure") == 5


def test_no_borrow_data_and_a_low_ratio_is_a_clean_zero(v2):
    result = evaluate(hit(short_ratio=1.0), v2, data={"borrow_fee_pct": None})
    assert points(result, "short_squeeze_pressure") == 0
    assert status(result, "short_squeeze_pressure") == "ok"


def test_neither_source_available_is_n_a(v2):
    result = evaluate(hit(short_ratio=None), v2, data={"borrow_fee_pct": None})
    assert status(result, "short_squeeze_pressure") == "n/a"


# --- volatility contraction ---------------------------------------------


def test_a_coiled_range_with_volume_pays(v2):
    result = evaluate(hit(rel_volume=3.0), v2, data={"range_percentile": 12.0})
    assert points(result, "volatility_contraction") == 10


def test_a_coiled_range_without_volume_does_not(v2):
    """Contraction alone is just a quiet stock."""
    result = evaluate(hit(rel_volume=1.4), v2, data={"range_percentile": 12.0})
    assert points(result, "volatility_contraction") == 0


def test_a_wide_range_with_volume_does_not(v2):
    result = evaluate(hit(rel_volume=4.0), v2, data={"range_percentile": 55.0})
    assert points(result, "volatility_contraction") == 0


def test_the_percentile_boundary_is_inclusive(v2):
    result = evaluate(hit(rel_volume=2.0), v2, data={"range_percentile": 20.0})
    assert points(result, "volatility_contraction") == 10


def test_no_history_means_no_contraction_claim(v2):
    result = evaluate(hit(), v2, data={"range_percentile": None})
    assert status(result, "volatility_contraction") == "n/a"


# --- premarket gap -------------------------------------------------------


def test_a_gap_with_real_premarket_volume_pays(v2):
    result = evaluate(
        hit(), v2, data={"premarket_gap_pct": 14.0, "premarket_volume_pct_of_adv": 25.0}
    )
    assert points(result, "premarket_gap") == 5


def test_a_gap_on_no_volume_does_not(v2):
    """A 12% premarket print on 2% of ADV is one order, not demand."""
    result = evaluate(
        hit(), v2, data={"premarket_gap_pct": 12.0, "premarket_volume_pct_of_adv": 2.0}
    )
    assert points(result, "premarket_gap") == 0


def test_volume_without_a_gap_does_not(v2):
    result = evaluate(
        hit(), v2, data={"premarket_gap_pct": 3.0, "premarket_volume_pct_of_adv": 40.0}
    )
    assert points(result, "premarket_gap") == 0


def test_a_missing_premarket_session_is_n_a(v2):
    result = evaluate(hit(), v2, data={"premarket_gap_pct": None})
    assert status(result, "premarket_gap") == "n/a"


# --- VWAP ----------------------------------------------------------------


def test_above_vwap_pays_five(v2):
    result = evaluate(hit(price=4.20), v2, data={"vwap": 4.00})
    assert points(result, "vwap_position") == 5


def test_below_vwap_costs_ten(v2):
    """The only signal that is negative on its own: under VWAP every buyer
    today is underwater, and that is where the supply comes from."""
    result = evaluate(hit(price=3.80), v2, data={"vwap": 4.00})
    assert points(result, "vwap_position") == -10


def test_exactly_on_vwap_counts_as_above(v2):
    result = evaluate(hit(price=4.00), v2, data={"vwap": 4.00})
    assert points(result, "vwap_position") == 5


def test_no_vwap_is_neither_rewarded_nor_punished(v2):
    result = evaluate(hit(), v2, data={"vwap": None})
    assert status(result, "vwap_position") == "n/a"
    assert points(result, "vwap_position") == 0


# --- insider buying -----------------------------------------------------


def test_an_open_market_purchase_inside_the_window_pays(v2):
    result = evaluate(hit(), v2, data={"insider_buy_days_ago": 12})
    assert points(result, "insider_buying") == 5


def test_an_older_purchase_does_not(v2):
    assert points(evaluate(hit(), v2, data={"insider_buy_days_ago": 45}), "insider_buying") == 0


def test_no_purchase_found_is_a_clean_zero(v2):
    result = evaluate(hit(), v2, data={"insider_buy_days_ago": None, "insider_checked": True})
    assert points(result, "insider_buying") == 0
    assert status(result, "insider_buying") == "ok"


def test_an_unchecked_insider_record_is_n_a(v2):
    result = evaluate(hit(), v2, data={})
    assert status(result, "insider_buying") == "n/a"


# --- institutional ownership --------------------------------------------


def test_thin_institutional_ownership_pays(v2):
    assert points(evaluate(hit(inst_own_pct=7.89), v2), "institutional_ownership") == 3


def test_the_ownership_boundary_is_exclusive(v2):
    assert points(evaluate(hit(inst_own_pct=20.0), v2), "institutional_ownership") == 0


def test_heavy_institutional_ownership_does_not_pay(v2):
    assert points(evaluate(hit(inst_own_pct=64.0), v2), "institutional_ownership") == 0


def test_missing_ownership_is_n_a(v2):
    assert status(evaluate(hit(inst_own_pct=None), v2), "institutional_ownership") == "n/a"


# --- sector sympathy ----------------------------------------------------


def test_two_peers_running_pays(v2):
    result = evaluate(hit(), v2, data={"sector_peers_up": 2})
    assert points(result, "sector_sympathy") == 5


def test_one_peer_is_not_a_theme(v2):
    assert points(evaluate(hit(), v2, data={"sector_peers_up": 1}), "sector_sympathy") == 0


def test_no_peer_scan_is_n_a(v2):
    assert status(evaluate(hit(), v2, data={"sector_peers_up": None}), "sector_sympathy") == "n/a"


# --- the cap ------------------------------------------------------------


def test_everything_firing_is_capped_at_thirty(v2):
    result = evaluate(
        hit(
            volume=40_000_000,
            float_shares=20_000_000,
            short_ratio=6.0,
            inst_own_pct=5.0,
            rel_volume=4.0,
            price=4.50,
        ),
        v2,
        data={
            "catalyst_hours_ago": 2.0,
            "catalyst_form": "8-K",
            "borrow_fee_pct": 80.0,
            "range_percentile": 5.0,
            "premarket_gap_pct": 20.0,
            "premarket_volume_pct_of_adv": 50.0,
            "vwap": 4.00,
            "insider_buy_days_ago": 3,
            "sector_peers_up": 4,
        },
    )
    assert result["raw_bonus"] == 58
    assert result["bonus"] == 30
    assert result["capped"] is True


def test_a_penalty_stays_visible_under_the_cap(v2):
    """The cap is on the layer's net effect, but the charge that was netted
    off has to stay on the record — "signals +30" with a VWAP failure hidden
    inside it is the kind of number that gets a call bought."""
    result = evaluate(
        hit(
            volume=40_000_000,
            float_shares=20_000_000,
            short_ratio=6.0,
            inst_own_pct=5.0,
            rel_volume=4.0,
            price=3.50,
        ),
        v2,
        data={
            "catalyst_hours_ago": 2.0,
            "catalyst_form": "8-K",
            "range_percentile": 5.0,
            "vwap": 4.00,
            "insider_buy_days_ago": 3,
            "sector_peers_up": 4,
        },
    )
    assert result["signals"]["vwap_position"]["points"] == -10
    assert result["bonus"] == 30


def test_a_net_negative_sheet_stays_negative(v2):
    result = evaluate(hit(price=3.50), v2, data={"vwap": 4.00, "catalyst_found": False})
    assert result["bonus"] == -25
    assert result["capped"] is False


def test_a_blank_sheet_scores_nothing(v2):
    """Every source down: no bonus, no penalty, no crash."""
    result = evaluate(hit(float_shares=None, short_ratio=None, inst_own_pct=None), v2, data={})
    assert result["bonus"] == 0
    assert all(entry["status"] == "n/a" for entry in result["signals"].values())


# --- hard skips ---------------------------------------------------------


def test_a_recent_shelf_is_a_hard_skip(v2):
    result = evaluate(hit(), v2, data={"dilution_filings": [{"form": "S-3", "days_ago": 12}]})
    assert result["hard_skips"]
    assert "S-3" in result["hard_skips"][0]
    assert result["hard_skip"] is True


def test_an_old_shelf_is_not(v2):
    result = evaluate(hit(), v2, data={"dilution_filings": [{"form": "S-3", "days_ago": 200}]})
    assert result["hard_skips"] == []


def test_a_clean_filing_record_is_not_a_skip(v2):
    result = evaluate(hit(), v2, data={"dilution_filings": []})
    assert result["hard_skips"] == []
    assert result["hard_skip"] is False


def test_a_reverse_split_inside_six_months_is_a_hard_skip(v2):
    result = evaluate(hit(), v2, data={"reverse_split_days_ago": 40})
    assert any("reverse split" in reason.lower() for reason in result["hard_skips"])


def test_an_older_reverse_split_is_not(v2):
    assert evaluate(hit(), v2, data={"reverse_split_days_ago": 400})["hard_skips"] == []


def test_a_short_cash_runway_is_a_hard_skip(v2):
    result = evaluate(hit(), v2, data={"cash_runway_months": 2.5})
    assert any("runway" in reason.lower() for reason in result["hard_skips"])


def test_a_long_runway_is_not(v2):
    assert evaluate(hit(), v2, data={"cash_runway_months": 18.0})["hard_skips"] == []


def test_a_profitable_company_is_not_skipped_for_runway(v2):
    """No burn means no runway to run out of; a negative burn must not read as
    zero months left."""
    assert evaluate(hit(), v2, data={"cash_runway_months": float("inf")})["hard_skips"] == []


def test_three_halts_in_a_session_is_a_hard_skip(v2):
    result = evaluate(hit(), v2, data={"halts_today": 3})
    assert any("halt" in reason.lower() for reason in result["hard_skips"])


def test_two_halts_is_not(v2):
    assert evaluate(hit(), v2, data={"halts_today": 2})["hard_skips"] == []


def test_unavailable_hard_skip_data_never_skips(v2):
    """A hard skip is an accusation. Missing data does not get to make it."""
    result = evaluate(
        hit(),
        v2,
        data={
            "dilution_filings": None,
            "reverse_split_days_ago": None,
            "cash_runway_months": None,
            "halts_today": None,
        },
    )
    assert result["hard_skips"] == []
    assert result["hard_skip"] is False
    assert all(entry["status"] == "n/a" for entry in result["hard_skip_checks"].values())


def test_every_hard_skip_fires_together_and_all_are_named(v2):
    result = evaluate(
        hit(),
        v2,
        data={
            "dilution_filings": [{"form": "424B5", "days_ago": 3}],
            "reverse_split_days_ago": 10,
            "cash_runway_months": 1.0,
            "halts_today": 5,
        },
    )
    assert len(result["hard_skips"]) == 4


def test_a_hard_skip_can_be_disabled(v2):
    v2["screener"]["versions"]["v2"]["explosion_signals"]["hard_skips"]["cash_runway"][
        "enabled"
    ] = False
    result = evaluate(hit(), v2, data={"cash_runway_months": 1.0})
    assert result["hard_skips"] == []


# --- rendering ----------------------------------------------------------


def test_the_summary_names_the_signals_that_scored(v2):
    result = evaluate(
        hit(volume=20_000_000, float_shares=20_000_000, inst_own_pct=5.0),
        v2,
        data={"catalyst_hours_ago": 1.0, "catalyst_form": "8-K", "vwap": 3.90},
    )
    text = signal_summary(result)
    assert "rotation" in text
    assert "+10" in text
    assert "catalyst" in text


def test_the_summary_of_an_empty_sheet_says_so(v2):
    assert "no signals" in signal_summary(evaluate(hit(float_shares=None), v2, data={})).lower()


def test_the_summary_of_a_v1_hit_is_empty(config):
    assert signal_summary(evaluate(hit(screener_version="v1"), config)) == ""
