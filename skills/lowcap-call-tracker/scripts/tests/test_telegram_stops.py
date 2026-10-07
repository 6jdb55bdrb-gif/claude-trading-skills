"""What the push message must say about a new call: the stop it is held to.

A TAKE arrives on a phone and gets acted on there. A message that names an
entry without the line that invalidates it is an invitation to improvise.
"""

from telegram_bot import format_run_notification


def base_report(**overrides):
    report = {
        "run_id": "20261007T2000Z",
        "session": {"as_of": "2026-10-07", "reason": "regular session"},
        "screening_ran": True,
        "screener_version": "v2",
        "new_calls": [],
        "duplicates_skipped": [],
        "guard_skips": [],
        "price_update": {"priced": 0, "closed": 0, "updates": [], "missing_prices": []},
        "stats": {},
        "errors": [],
    }
    report.update(overrides)
    return report


def call(**overrides):
    out = {
        "ticker": "SQZX",
        "asset_type": "stock",
        "variant": "squeeze",
        "direction": "long",
        "decision": "TAKE",
        "confidence": 72,
        "entry": 3.8,
        "stop": 3.42,
        "sl_price": 3.04,
        "screener_version": "v2",
        "reason": "clean base, crowded short",
        "kind": "active",
        "call_id": 1,
    }
    out.update(overrides)
    return out


def test_every_take_carries_its_stop_price(config):
    text = format_run_notification(base_report(new_calls=[call()]), config)
    assert "3.04" in text
    assert "SL" in text


def test_a_shadow_call_shows_its_stop_too(config):
    """A SKIP is tracked at the same stop, or the two books are not comparable."""
    text = format_run_notification(
        base_report(new_calls=[call(decision="SKIP", confidence=48)]), config
    )
    assert "3.04" in text


def test_a_call_without_a_fixed_stop_says_so_rather_than_printing_nothing(config):
    text = format_run_notification(base_report(new_calls=[call(sl_price=None)]), config)
    assert "SQZX" in text
    assert "3.04" not in text


def test_the_message_names_the_screener_version(config):
    text = format_run_notification(base_report(new_calls=[call()]), config)
    assert "v2" in text


def test_a_gated_run_explains_why_it_did_not_screen(config):
    text = format_run_notification(
        base_report(
            screening_ran=False,
            screen_skipped="v2 does not screen before 16:30 Europe/Zurich (now 15:00)",
        ),
        config,
    )
    assert "16:30" in text


def test_a_capped_name_is_named_in_the_message(config):
    text = format_run_notification(
        base_report(
            guard_skips=[{"ticker": "PMPX", "reason": "already up +41.2% today (cap +25%)"}]
        ),
        config,
    )
    assert "PMPX" in text and "41.2" in text


def test_the_scorecard_appears_once_it_is_ready(config):
    text = format_run_notification(
        base_report(scorecard="📊 *Scorecard* (31 calls)\nv2: n=31 hit=55.0% avg=+4.10%"), config
    )
    assert "Scorecard" in text and "31 calls" in text


def test_no_scorecard_line_while_the_sample_is_thin(config):
    assert "Scorecard" not in format_run_notification(base_report(), config)
