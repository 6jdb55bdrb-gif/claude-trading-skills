"""A mark from an earlier session must say so.

At 06:02 ET on Friday 2 October the book showed `SDEV now=3.66 pnl=+14.4%`.
That was Thursday's close. SDEV was trading 5.21 in pre-market at that moment,
+62.8% from the 3.20 entry. Holding yesterday's close is correct — no daily bar
exists for today until the session produces one — but printing it as "now" with
no label is not, and it is the same class of error as pricing a call on a bar
that predates it.

The tag is derived from the bar's own date against the current Eastern date, so
it is honest overnight as well: at 00:54 Friday, Thursday's close IS the
freshest mark, and saying which session it belongs to still helps.
"""

from price_update import format_updates, update_open_calls

from conftest import review_payload


def _open(db, ticker="AAA", entry=3.20, called="2026-09-30T15:00:00+00:00"):
    """A call made BEFORE the bar that prices it.

    The call date matters: a bar older than the call is refused outright by the
    pre-entry guard, so the prior-close case only arises once a call has
    outlived the session it was made in — which is every call, by the next day.
    """
    review = review_payload(ticker, entry=entry)
    review["hit"] = {"ticker": ticker, "atr": 0.43, "price": entry}
    return db.insert_call(
        review,
        run_id="r1",
        now=called,
        allocation_usd=100.0,
        trail_floor_pct=15.0,
        trail_atr_mult=1.5,
    )


def test_a_mark_from_an_earlier_session_is_tagged(tmp_db, config):
    _open(tmp_db)
    result = update_open_calls(
        tmp_db,
        config,
        prices={"AAA": {"price": 3.66, "as_of": "2026-10-01"}},
        today="2026-10-02",
    )
    assert result["updates"][0]["prior_session"] is True
    assert "PRIOR CLOSE (2026-10-01)" in format_updates(result)


def test_a_mark_from_the_current_session_is_not_tagged(tmp_db, config):
    _open(tmp_db)
    result = update_open_calls(
        tmp_db,
        config,
        prices={"AAA": {"price": 4.20, "as_of": "2026-10-02"}},
        today="2026-10-02",
    )
    assert result["updates"][0]["prior_session"] is False
    assert "PRIOR CLOSE" not in format_updates(result)


def test_a_price_with_no_session_is_not_tagged(tmp_db, config):
    """A bare float from --prices-json or a fixture claims no session."""
    _open(tmp_db)
    result = update_open_calls(tmp_db, config, prices={"AAA": 4.20}, today="2026-10-02")
    assert result["updates"][0]["prior_session"] is False
    assert "PRIOR CLOSE" not in format_updates(result)


def test_the_tag_survives_alongside_a_stop_out(tmp_db, config):
    """A stop is the louder fact, but the stale bar must not be hidden."""
    call_id = _open(tmp_db, entry=3.20)
    update_open_calls(
        tmp_db, config, prices={"AAA": {"price": 4.24, "as_of": "2026-10-01"}}, today="2026-10-01"
    )
    result = update_open_calls(
        tmp_db, config, prices={"AAA": {"price": 3.00, "as_of": "2026-10-01"}}, today="2026-10-02"
    )
    assert tmp_db.call(call_id)["status"] == "STOPPED"
    text = format_updates(result)
    assert "STOPPED" in text
    assert "2026-10-01" in text


def test_an_unpriced_call_still_reports_its_last_session(tmp_db, config):
    _open(tmp_db)
    update_open_calls(
        tmp_db, config, prices={"AAA": {"price": 3.66, "as_of": "2026-10-01"}}, today="2026-10-01"
    )
    result = update_open_calls(tmp_db, config, prices={}, today="2026-10-02")
    assert result["updates"][0]["prior_session"] is True


def test_today_defaults_to_the_eastern_date(tmp_db, config):
    """Nothing passes `today` in production; it must resolve on its own.

    The bar has to post-date the call or the pre-entry guard refuses it, and
    pre-date today or there is nothing to tag — so it is dated yesterday,
    relative to the Eastern clock the tracker actually runs on.
    """
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    now_et = datetime.now(ZoneInfo("America/New_York"))
    today = now_et.strftime("%Y-%m-%d")
    yesterday = (now_et - timedelta(days=1)).strftime("%Y-%m-%d")
    _open(tmp_db, called=(now_et - timedelta(days=3)).strftime("%Y-%m-%dT15:00:00+00:00"))
    result = update_open_calls(tmp_db, config, prices={"AAA": {"price": 3.66, "as_of": yesterday}})
    assert result["today"] == today
    assert result["updates"][0]["prior_session"] is True
    assert result["prior_session_marks"] == ["AAA"]
