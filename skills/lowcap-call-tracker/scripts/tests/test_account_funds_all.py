"""Which calls the account actually funds is the operator's, not an assumption.

I assumed the account funds only what the Judge said TAKE — "nobody would have
bought the SKIPs". The operator corrected that: they take every call the
screener surfaces, so the all-calls figure IS their account PnL.

`tracker.account_funds` settles it:

* ``all`` (default) — every call is funded. The account is what the operator
  actually runs.
* ``take_only`` — only TAKE calls. What following the Judge would have given.

Both books stay computed either way, because the comparison between them is
the only thing that prices the Judge's selectivity.
"""

from allocation import account_funds_all, portfolio_state, take_only_state

from conftest import review_payload


def _cfg(config, funds="all"):
    return {**config, "tracker": {**config["tracker"], "account_funds": funds}}


def _add(db, ticker, *, decision, entry=10.0, price=None, alloc=100.0):
    call_id = db.insert_call(
        review_payload(ticker, decision=decision, entry=entry), run_id="r1", allocation_usd=alloc
    )
    if price is not None:
        db.apply_price(call_id, price, close_threshold_pct=None)
    return call_id


# --- the setting -----------------------------------------------------------


def test_the_default_funds_every_call(config):
    assert account_funds_all(config) is True


def test_take_only_can_be_asked_for(config):
    assert account_funds_all(_cfg(config, "take_only")) is False


def test_an_unknown_value_falls_back_to_funding_everything(config):
    """A typo must not silently shrink the account to one call."""
    assert account_funds_all(_cfg(config, "nonsense")) is True


# --- the account -----------------------------------------------------------


def test_the_account_counts_a_skip_that_soared(tmp_db, config):
    """SDEV +175.8% was a SKIP, and the operator took it. It is account profit."""
    _add(tmp_db, "SDEV", decision="SKIP", entry=1.04, price=2.868)
    state = portfolio_state(tmp_db, _cfg(config))
    assert round(state["total_return_pct"], 2) == 17.58
    assert state["allocated_usd"] == 100.0


def test_take_only_still_excludes_that_skip(tmp_db, config):
    _add(tmp_db, "SDEV", decision="SKIP", entry=1.04, price=2.868)
    assert take_only_state(tmp_db, _cfg(config))["total_return_pct"] == 0.0


def test_the_live_book_shape_reproduces_both_numbers(tmp_db, config):
    _add(tmp_db, "SDEV", decision="SKIP", entry=1.04, price=2.868)
    _add(tmp_db, "MEDS", decision="TAKE", entry=5.16, price=4.18)
    account = portfolio_state(tmp_db, _cfg(config))
    judge = take_only_state(tmp_db, _cfg(config))
    assert round(account["total_return_pct"], 2) == 15.68
    assert round(judge["total_return_pct"], 2) == -1.90


def test_take_only_mode_swaps_which_is_the_account(tmp_db, config):
    _add(tmp_db, "SDEV", decision="SKIP", entry=1.04, price=2.868)
    _add(tmp_db, "MEDS", decision="TAKE", entry=5.16, price=4.18)
    account = portfolio_state(tmp_db, _cfg(config, "take_only"))
    assert round(account["total_return_pct"], 2) == -1.90


def test_a_voided_call_is_funded_by_neither_book(tmp_db, config):
    call_id = _add(tmp_db, "NCPL", decision="SKIP", entry=1.09, price=1.38)
    tmp_db.void_call(call_id, reason="not executable")
    assert portfolio_state(tmp_db, _cfg(config))["total_return_pct"] == 0.0


def test_an_unreviewed_call_is_funded_when_the_account_takes_everything(tmp_db, config):
    """It is a screener hit the operator would have bought, judged or not."""
    tmp_db.insert_call(
        review_payload("VEEA", decision="UNREVIEWED", entry=3.20), run_id="r1", allocation_usd=100.0
    )
    assert portfolio_state(tmp_db, _cfg(config))["allocated_usd"] == 100.0
    assert take_only_state(tmp_db, _cfg(config))["allocated_usd"] == 0.0


# --- cash ------------------------------------------------------------------


def test_cash_falls_for_every_funded_call(tmp_db, config):
    _add(tmp_db, "AAA", decision="TAKE", entry=10.0)
    _add(tmp_db, "BBB", decision="SKIP", entry=10.0)
    state = portfolio_state(tmp_db, _cfg(config))
    assert state["cash_usd"] == 800.0
    assert state["allocated_pct"] == 20.0


# --- the report ------------------------------------------------------------


def test_the_report_leads_with_the_funded_account(tmp_db, config):
    from stats import compute_stats, render_text

    _add(tmp_db, "SDEV", decision="SKIP", entry=1.04, price=2.868)
    _add(tmp_db, "MEDS", decision="TAKE", entry=5.16, price=4.18)
    text = render_text(compute_stats(tmp_db, _cfg(config)))
    assert "ACCOUNT (every call)" in text
    assert "$1,156.78" in text
    assert "TAKE only" in text  # kept as the Judge's scorecard


def test_the_report_names_take_only_mode_when_chosen(tmp_db, config):
    from stats import compute_stats, render_text

    _add(tmp_db, "MEDS", decision="TAKE", entry=5.16, price=4.18)
    text = render_text(compute_stats(tmp_db, _cfg(config, "take_only")))
    assert "ACCOUNT (TAKE only)" in text


def test_allocated_pct_is_measured_against_current_capital(tmp_db, config):
    """A fully invested book must read 100%, not 110%.

    Realized gains are capital: after +$100 of banked profit the account has
    $1,100 to commit, and committing all of it is being fully invested, not
    levered. Measuring against the STARTING size made a correct book look
    over-committed — which is the one thing an allocation percentage exists to
    warn about, so the false alarm is worse than no number.
    """
    from allocation import portfolio_state

    # Two closed winners bank $100, then the whole book is committed.
    won = tmp_db.insert_call(review_payload("WON", entry=10.0), run_id="r1", allocation_usd=100.0)
    tmp_db.apply_price(won, 20.0, close_threshold_pct=None, allow_stop=False)
    tmp_db.close_call(won, reason="target_hit")
    for index in range(11):
        tmp_db.insert_call(
            review_payload(f"OPEN{index}", entry=10.0), run_id="r1", allocation_usd=100.0
        )

    state = portfolio_state(tmp_db, config)
    assert state["realized_usd"] == 100.0
    assert state["allocated_usd"] == 1100.0
    assert state["cash_usd"] == 0.0
    assert state["allocated_pct"] == 100.0
    # The growth is still visible, just not disguised as leverage.
    assert state["capital_usd"] == 1100.0


def test_a_half_invested_book_still_reads_half(tmp_db, config):
    from allocation import portfolio_state

    for index in range(5):
        tmp_db.insert_call(
            review_payload(f"HALF{index}", entry=10.0), run_id="r1", allocation_usd=100.0
        )
    state = portfolio_state(tmp_db, config)
    assert state["allocated_pct"] == 50.0
    assert state["capital_usd"] == 1000.0


def test_realized_losses_shrink_the_capital_the_percentage_is_measured_against(tmp_db, config):
    from allocation import portfolio_state

    lost = tmp_db.insert_call(review_payload("LOST", entry=10.0), run_id="r1", allocation_usd=100.0)
    tmp_db.apply_price(lost, 5.0, close_threshold_pct=None, allow_stop=False)
    tmp_db.close_call(lost, reason="stopped")
    for index in range(9):
        tmp_db.insert_call(
            review_payload(f"OPEN{index}", entry=10.0), run_id="r1", allocation_usd=100.0
        )
    state = portfolio_state(tmp_db, config)
    assert state["realized_usd"] == -50.0
    assert state["capital_usd"] == 950.0
    assert state["allocated_pct"] == round(900.0 / 950.0 * 100.0, 1)
