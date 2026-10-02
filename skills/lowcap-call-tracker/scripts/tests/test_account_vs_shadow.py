"""The account funds what the system TOOK. Shadows are a separate book.

`portfolio_state` funded every call at a full slice, SKIPs included, so the
headline account value was the return of a portfolio that bought all ten
screener hits — nine of which the Judge had explicitly rejected. On the live
book that read +11.57% ($1,115.72) while following the system actually gave
-1.90% ($981.01): the entire gain came from the one SKIP that ran (SDEV
+175.8%), and the single TAKE lost money.

Two books now, each honest about what it is:

* **account** — TAKE calls only. What following the system is worth.
* **shadow**  — every call. What the screener found, regardless of verdict.

Shadow calls also no longer consume the account's cash, so a run of SKIPs
cannot starve a real TAKE of its slice.
"""

from allocation import portfolio_state, shadow_state, slice_usd

from conftest import review_payload


def _add(db, ticker, *, decision, entry=10.0, price=None, alloc=100.0):
    call_id = db.insert_call(
        review_payload(ticker, decision=decision, entry=entry),
        run_id="r1",
        allocation_usd=alloc,
    )
    if price is not None:
        db.apply_price(call_id, price, close_threshold_pct=None)
    return call_id


# --- the account counts only what was taken -------------------------------


def test_the_account_ignores_a_skip_that_soared(tmp_db, config):
    """SDEV +175.8% was a SKIP. It must not appear as account profit."""
    _add(tmp_db, "SDEV", decision="SKIP", entry=1.04, price=2.87)
    state = portfolio_state(tmp_db, config)
    assert state["portfolio_value_usd"] == 1000.0
    assert state["total_return_pct"] == 0.0
    assert state["allocated_usd"] == 0.0


def test_the_account_counts_a_take_that_lost(tmp_db, config):
    _add(tmp_db, "MEDS", decision="TAKE", entry=5.16, price=4.18)
    state = portfolio_state(tmp_db, config)
    assert state["allocated_usd"] == 100.0
    assert round(state["positions_value_usd"], 2) == 81.01
    assert round(state["total_return_pct"], 2) == -1.90


def test_the_live_book_shape_reproduces_both_numbers(tmp_db, config):
    """One TAKE down 19%, one SKIP up 175.8%: two very different books."""
    _add(tmp_db, "SDEV", decision="SKIP", entry=1.04, price=2.868)
    _add(tmp_db, "MEDS", decision="TAKE", entry=5.16, price=4.18)
    account = portfolio_state(tmp_db, config)
    shadow = shadow_state(tmp_db, config)
    assert round(account["total_return_pct"], 2) == -1.90
    assert round(shadow["total_return_pct"], 2) == 15.68
    assert account["portfolio_value_usd"] < 1000.0 < shadow["portfolio_value_usd"]


# --- the shadow book keeps every call -------------------------------------


def test_the_shadow_book_counts_skips_and_takes_alike(tmp_db, config):
    _add(tmp_db, "SDEV", decision="SKIP", entry=1.04, price=2.08)  # +100%
    _add(tmp_db, "MEDS", decision="TAKE", entry=10.0, price=5.0)  # -50%
    shadow = shadow_state(tmp_db, config)
    assert round(shadow["total_return_pct"], 2) == 5.0  # +100 -50 = +50 on 1000


def test_a_voided_call_is_in_neither_book(tmp_db, config):
    call_id = _add(tmp_db, "NCPL", decision="SKIP", entry=1.09, price=1.38)
    tmp_db.void_call(call_id, reason="not executable")
    assert shadow_state(tmp_db, config)["total_return_pct"] == 0.0
    assert portfolio_state(tmp_db, config)["total_return_pct"] == 0.0


def test_an_unreviewed_call_is_not_in_the_account(tmp_db, config):
    """Nobody decided to take it, so the account cannot have funded it."""
    review = review_payload("VEEA", decision="UNREVIEWED", entry=3.20)
    tmp_db.insert_call(review, run_id="r1", allocation_usd=100.0)
    assert portfolio_state(tmp_db, config)["allocated_usd"] == 0.0
    assert shadow_state(tmp_db, config)["allocated_usd"] == 100.0


# --- cash is the account's, not the shadow book's -------------------------


def test_shadow_calls_cannot_starve_a_real_take_of_cash(tmp_db, config):
    """Ten SKIPs used to consume the whole account and leave a TAKE unfunded."""
    for i in range(10):
        _add(tmp_db, f"SK{i}", decision="SKIP", entry=10.0)
    cash = portfolio_state(tmp_db, config)["cash_usd"]
    assert cash == 1000.0
    assert slice_usd(config, cash_available=cash) == 100.0


def test_the_account_cash_falls_only_for_takes(tmp_db, config):
    _add(tmp_db, "AAA", decision="TAKE", entry=10.0)
    _add(tmp_db, "BBB", decision="SKIP", entry=10.0)
    state = portfolio_state(tmp_db, config)
    assert state["cash_usd"] == 900.0
    assert state["allocated_pct"] == 10.0


# --- the report cannot present one as the other ---------------------------


def test_the_report_labels_both_books(tmp_db, config):
    from stats import compute_stats, render_text

    _add(tmp_db, "SDEV", decision="SKIP", entry=1.04, price=2.868)
    _add(tmp_db, "MEDS", decision="TAKE", entry=5.16, price=4.18)
    text = render_text(compute_stats(tmp_db, config))
    assert "ACCOUNT (TAKE only)" in text
    assert "SHADOW BOOK" in text
    assert "$981.01" in text  # the account, down 1.90%
    assert "-1.90%" in text


def test_the_markdown_report_says_which_is_which(tmp_db, config):
    from stats import compute_stats, render_markdown

    _add(tmp_db, "MEDS", decision="TAKE", entry=5.16, price=4.18)
    md = render_markdown(compute_stats(tmp_db, config))
    assert "Account (TAKE calls only)" in md
    assert "Shadow book" in md
    assert "nobody would have bought the SKIPs" in md
