"""The headline number: every call, equally weighted."""

from stats import compute_stats, render_markdown, render_text

from conftest import review_payload


def _seed(db, specs):
    for ticker, entry, now_price, decision in specs:
        call_id = db.insert_call(
            review_payload(ticker, entry=entry, decision=decision), run_id="r1"
        )
        db.apply_price(call_id, now_price, close_threshold_pct=None)


def test_total_pnl_is_the_equal_weight_return_of_every_call(tmp_db, config):
    # +10%, -20%, +40%  ->  mean +10%
    _seed(
        tmp_db,
        [("AAA", 10.0, 11.0, "TAKE"), ("BBB", 10.0, 8.0, "SKIP"), ("CCC", 10.0, 14.0, "SKIP")],
    )
    portfolio = compute_stats(tmp_db, config)["portfolio"]
    assert portfolio["total_pnl_pct"] == 10.0
    assert portfolio["calls_counted"] == 3


def test_the_total_includes_unreviewed_calls(tmp_db, config, stock_hit):
    """ "All the calls" means all of them, judged or not."""
    from run_cycle import unreviewed_review

    _seed(tmp_db, [("AAA", 10.0, 12.0, "SKIP")])
    call_id = tmp_db.insert_call(
        unreviewed_review({**stock_hit, "ticker": "ZZZ", "price": 10.0}, "down"), run_id="r1"
    )
    tmp_db.apply_price(call_id, 10.0, close_threshold_pct=None)
    portfolio = compute_stats(tmp_db, config)["portfolio"]
    assert portfolio["calls_counted"] == 2
    assert portfolio["total_pnl_pct"] == 10.0  # (+20% + 0%) / 2


def test_a_short_call_counts_with_its_own_sign(tmp_db, config):
    """A put that worked is a gain, even though the stock fell."""
    call_id = tmp_db.insert_call(
        review_payload("PUT1", entry=10.0, decision="SKIP", direction="short"), run_id="r1"
    )
    tmp_db.apply_price(call_id, 8.0, close_threshold_pct=None)
    assert compute_stats(tmp_db, config)["portfolio"]["total_pnl_pct"] == 20.0


def test_an_empty_tracker_reports_no_total(tmp_db, config):
    portfolio = compute_stats(tmp_db, config)["portfolio"]
    assert portfolio["total_pnl_pct"] is None
    assert portfolio["calls_counted"] == 0


def test_the_total_leads_the_terminal_block(tmp_db, config):
    _seed(tmp_db, [("AAA", 10.0, 11.0, "TAKE")])
    text = render_text(compute_stats(tmp_db, config))
    assert "TOTAL PnL" in text
    assert "+10.00%" in text
    assert "None" not in text


def test_the_total_leads_the_statistics_file(tmp_db, config):
    _seed(tmp_db, [("AAA", 10.0, 11.0, "TAKE")])
    markdown = render_markdown(compute_stats(tmp_db, config))
    assert "Total PnL" in markdown
    assert "+10.00%" in markdown


def test_telegram_shows_the_total(tmp_db, config):
    import telegram_bot as tb

    _seed(tmp_db, [("AAA", 10.0, 11.0, "TAKE"), ("BBB", 10.0, 9.0, "SKIP")])
    message = tb.format_stats_message(compute_stats(tmp_db, config))
    assert "total" in message.lower()
    assert "0.00%" in message  # (+10% - 10%) / 2
    assert "None" not in message
