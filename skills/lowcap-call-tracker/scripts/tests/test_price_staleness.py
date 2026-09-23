"""A mark must never move backwards in time."""

from datetime import datetime, timezone

from price_update import update_open_calls

from conftest import review_payload

NOW = datetime(2026, 9, 23, 5, 13, tzinfo=timezone.utc)


def test_a_stale_bar_never_overwrites_a_newer_mark(tmp_db, config):
    """The reported failure: an overnight run reverted every call to the
    previous session's close, because the forming daily bar has no Close yet
    and the fetcher silently fell back to the last complete one."""
    call_id = tmp_db.insert_call(review_payload("GRML", entry=10.67), run_id="r1")

    # Intraday on the 22nd: a real, newer observation.
    tmp_db.apply_price(
        call_id,
        14.20,
        close_threshold_pct=None,
        as_of="2026-09-22",
        now="2026-09-22T18:25:00+00:00",
    )
    assert tmp_db.call(call_id)["current_price"] == 14.20

    # Overnight: the provider offers the 21st's close. It must be refused.
    result = update_open_calls(
        tmp_db, config, prices={"GRML": {"price": 9.42, "as_of": "2026-09-21"}}
    )
    update = result["updates"][0]
    assert update["priced"] is False
    assert update["stale_source"] is True
    assert update["price"] == 14.20
    assert tmp_db.call(call_id)["current_price"] == 14.20


def test_a_same_day_refresh_is_applied(tmp_db, config):
    call_id = tmp_db.insert_call(review_payload("GRML", entry=10.67), run_id="r1")
    tmp_db.apply_price(call_id, 14.20, close_threshold_pct=None, as_of="2026-09-22")
    update_open_calls(tmp_db, config, prices={"GRML": {"price": 15.10, "as_of": "2026-09-22"}})
    assert tmp_db.call(call_id)["current_price"] == 15.10


def test_a_newer_bar_is_applied(tmp_db, config):
    call_id = tmp_db.insert_call(review_payload("GRML", entry=10.67), run_id="r1")
    tmp_db.apply_price(call_id, 14.20, close_threshold_pct=None, as_of="2026-09-22")
    update_open_calls(tmp_db, config, prices={"GRML": {"price": 9.42, "as_of": "2026-09-23"}})
    assert tmp_db.call(call_id)["current_price"] == 9.42


def test_a_plain_float_still_works(tmp_db, config):
    """--prices-json and every existing caller pass bare numbers."""
    call_id = tmp_db.insert_call(review_payload("GRML", entry=10.67), run_id="r1")
    update_open_calls(tmp_db, config, prices={"GRML": 12.00})
    assert tmp_db.call(call_id)["current_price"] == 12.00


def test_the_first_price_is_always_accepted(tmp_db, config):
    """A call with no recorded bar date has nothing to regress from."""
    call_id = tmp_db.insert_call(review_payload("GRML", entry=10.67), run_id="r1")
    update_open_calls(tmp_db, config, prices={"GRML": {"price": 9.42, "as_of": "2020-01-01"}})
    assert tmp_db.call(call_id)["current_price"] == 9.42


def test_a_stale_call_is_still_reported(tmp_db, config):
    """A refused price must not make the position vanish from the report."""
    call_id = tmp_db.insert_call(review_payload("GRML", entry=10.67), run_id="r1")
    tmp_db.apply_price(call_id, 14.20, close_threshold_pct=None, as_of="2026-09-22")
    result = update_open_calls(
        tmp_db, config, prices={"GRML": {"price": 9.42, "as_of": "2026-09-21"}}
    )
    assert len(result["updates"]) == 1
    assert result["updates"][0]["ticker"] == "GRML"
    assert "GRML" in result["stale_sources"]


def test_fetch_price_points_carries_the_bar_date(monkeypatch):
    """The fetcher must report WHICH session each close belongs to."""
    import price_update

    class _Frame:
        def __init__(self, rows):
            self.rows = rows

        @property
        def empty(self):
            return not self.rows

    # A forming bar with no Close is exactly what produced the regression.
    series = [("2026-09-21", 9.42), ("2026-09-22", float("nan"))]
    monkeypatch.setattr(price_update, "_download_closes", lambda _t: {"GRML": series})
    points = price_update.fetch_price_points(["GRML"])
    assert points["GRML"] == {"price": 9.42, "as_of": "2026-09-21"}


def test_a_held_mark_reads_differently_from_a_missing_one(tmp_db, config):
    """ "Held" and "no price" are different facts and must not look the same."""
    import telegram_bot as tb
    from price_update import format_updates

    call_id = tmp_db.insert_call(review_payload("GRML", entry=10.67), run_id="r1")
    tmp_db.apply_price(call_id, 14.20, close_threshold_pct=None, as_of="2026-09-22")
    result = update_open_calls(
        tmp_db, config, prices={"GRML": {"price": 9.42, "as_of": "2026-09-21"}}
    )
    text = format_updates(result)
    assert "HELD (source behind)" in text
    assert "NO PRICE" not in text

    note = tb._stale_note(result["updates"][0])
    assert "held" in note
    assert "no price" not in note
