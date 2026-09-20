"""Telegram notifications, command handling and polling."""

from datetime import datetime, timezone

import pytest
import telegram_bot as tb
from run_cycle import run_cycle

from conftest import FIXTURE_HITS, review_payload


@pytest.fixture()
def wired(monkeypatch, config):
    """Config plus credentials, with every send captured instead of posted."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "4242")
    sent: list[dict] = []

    def transport(method, payload):
        sent.append({"method": method, **payload})
        return {"message_id": len(sent)}

    return config, sent, transport


def _client(config, transport, **kwargs):
    return tb.TelegramClient(token="test-token", chat_id="4242", transport=transport, **kwargs)


# ------------------------------------------------------------------- helpers


def test_escape_html_covers_the_reserved_characters():
    assert tb.escape_html("A & B <tag> >") == "A &amp; B &lt;tag&gt; &gt;"
    assert tb.escape_html(3.5) == "3.5"


def test_short_message_is_not_split():
    assert tb.split_message("hello", 100) == ["hello"]


def test_long_message_splits_on_line_boundaries():
    rows = [f"row {index}" for index in range(500)]
    chunks = tb.split_message("\n".join(rows), 200)
    assert len(chunks) > 1
    assert all(len(chunk) <= 200 for chunk in chunks)
    # No content is lost, and every chunk holds whole rows only.
    emitted = [row for chunk in chunks for row in chunk.split("\n")]
    assert emitted == rows


def test_a_single_overlong_line_is_hard_split():
    chunks = tb.split_message("x" * 9000, 3900)
    assert [len(chunk) for chunk in chunks] == [3900, 3900, 1200]


def test_split_never_exceeds_the_telegram_hard_limit():
    chunks = tb.split_message("y" * 20000, 99999)
    assert all(len(chunk) <= tb.TELEGRAM_HARD_LIMIT for chunk in chunks)


# --------------------------------------------------------------- credentials


def test_credentials_require_the_environment(monkeypatch, config):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with pytest.raises(tb.TelegramDisabled, match="TELEGRAM_BOT_TOKEN"):
        tb.credentials(config)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    with pytest.raises(tb.TelegramDisabled, match="TELEGRAM_CHAT_ID"):
        tb.credentials(config)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "9")
    assert tb.credentials(config) == ("t", "9")


def test_disabled_config_short_circuits(monkeypatch, config):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "9")
    config["telegram"]["enabled"] = False
    with pytest.raises(tb.TelegramDisabled, match="enabled"):
        tb.credentials(config)


def test_token_is_never_read_from_configuration(monkeypatch, config):
    """A leaked config file must not be enough to control the bot."""
    serialized = repr(config["telegram"]).lower()
    assert "token" not in serialized
    config["telegram"]["bot_token"] = "config-token"  # must be ignored
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "9")
    with pytest.raises(tb.TelegramDisabled, match="TELEGRAM_BOT_TOKEN"):
        tb.credentials(config)


# -------------------------------------------------------------------- client


def test_send_message_payload(wired):
    config, sent, transport = wired
    client = _client(config, transport)
    client.send_message("hello", silent=True)
    assert sent[0]["method"] == "sendMessage"
    assert sent[0]["chat_id"] == "4242"
    assert sent[0]["text"] == "hello"
    assert sent[0]["parse_mode"] == "HTML"
    assert sent[0]["disable_notification"] is True
    assert sent[0]["disable_web_page_preview"] is True


def test_send_message_chunks_long_text(wired):
    config, sent, transport = wired
    client = _client(config, transport, max_message_chars=100)
    client.send_message("\n".join(f"row {index}" for index in range(100)))
    assert len(sent) > 1
    assert all(len(payload["text"]) <= 100 for payload in sent)


def test_get_updates_passes_the_offset(wired):
    config, sent, transport = wired

    def updates_transport(method, payload):
        sent.append({"method": method, **payload})
        return [{"update_id": 7}]

    client = _client(config, updates_transport)
    assert client.get_updates(offset=5, timeout=0) == [{"update_id": 7}]
    assert sent[0]["offset"] == 5
    assert sent[0]["allowed_updates"] == ["message"]


def test_http_path_retries_a_rate_limit(monkeypatch, wired):
    config, _sent, _transport = wired
    calls = []

    class Response:
        def __init__(self, status, body):
            self.status_code = status
            self._body = body

        def json(self):
            return self._body

    class FakeRequests:
        @staticmethod
        def post(url, json, timeout):  # noqa: A002 - mirrors requests' signature
            calls.append(url)
            if len(calls) == 1:
                return Response(429, {"parameters": {"retry_after": 0}})
            return Response(200, {"ok": True, "result": {"message_id": 1}})

    monkeypatch.setattr(tb, "requests", FakeRequests)
    monkeypatch.setattr(tb, "HAS_REQUESTS", True)
    monkeypatch.setattr(tb.time, "sleep", lambda _seconds: None)
    client = tb.TelegramClient(token="t", chat_id="1")
    client.send_message("hi")
    assert len(calls) == 2  # retried after the 429


def test_api_error_is_raised_as_telegram_error(monkeypatch, wired):
    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"ok": False, "description": "chat not found"}

    class FakeRequests:
        @staticmethod
        def post(url, json, timeout):  # noqa: A002
            return Response()

    monkeypatch.setattr(tb, "requests", FakeRequests)
    monkeypatch.setattr(tb, "HAS_REQUESTS", True)
    client = tb.TelegramClient(token="t", chat_id="1")
    with pytest.raises(tb.TelegramError, match="chat not found"):
        client.send_message("hi")


def test_missing_requests_is_reported_clearly(monkeypatch):
    monkeypatch.setattr(tb, "HAS_REQUESTS", False)
    client = tb.TelegramClient(token="t", chat_id="1")
    with pytest.raises(tb.TelegramError, match="requests"):
        client.send_message("hi")


# ----------------------------------------------------------------- messages


def _report(**overrides):
    report = {
        "run_id": "run_test",
        "session": {"as_of": "2026-09-18T10:00:00-04:00", "reason": "regular trading hours"},
        "screening_ran": True,
        "new_calls": [
            {
                "ticker": "SQZX",
                "asset_type": "stock",
                "variant": "squeeze",
                "direction": "long",
                "decision": "TAKE",
                "confidence": 74,
                "entry": 3.8,
                "stop": 3.22,
                "reason": "FDA approval & uptrend",
                "kind": "active",
            }
        ],
        "price_update": {
            "priced": 1,
            "closed": 0,
            "threshold_pct": -80.0,
            "missing_prices": [],
            "updates": [
                {
                    "ticker": "URAX",
                    "direction": "long",
                    "kind": "active",
                    "entry_price": 18.4,
                    "price": 19.8,
                    "pnl_pct": 7.6,
                    "closed": False,
                }
            ],
        },
        "stats": {
            "overall": {
                "total": 2,
                "open": 2,
                "right": 1,
                "wrong": 0,
                "neutral": 1,
                "hit_rate_pct": 50.0,
                "avg_pnl_pct": 3.8,
                "best_call": {"ticker": "URAX", "pnl_pct": 7.6},
                "worst_call": {"ticker": "SQZX", "pnl_pct": 0.0},
            },
            "portfolio": {"equal_weight_pnl_pct_take_only": 3.8},
            "take_vs_skip": {
                "take": {"avg_pnl_pct": 3.8},
                "skip_shadow": {"avg_pnl_pct": None},
                "verdict": "no comparison yet",
            },
        },
        "llm_cost": {"cost_usd": 0.0123},
        "llm_month_to_date_usd": 0.5,
        "llm_cap_usd": 10.0,
        "errors": [],
        "reviews": [],
    }
    report.update(overrides)
    return report


def test_run_notification_lists_calls_and_prices(config):
    message = tb.format_run_notification(_report(), config)
    assert "Lowcap tracker" in message
    assert "SQZX" in message and "conf 74" in message
    assert "URAX" in message and "+7.6%" in message
    assert "Stats" in message
    assert "LLM $0.0123" in message


def test_run_notification_escapes_user_visible_text(config):
    report = _report()
    report["new_calls"][0]["reason"] = "catalyst <b>hype</b> & noise"
    message = tb.format_run_notification(report, config)
    assert "&lt;b&gt;hype&lt;/b&gt; &amp; noise" in message
    assert "<b>hype</b>" not in message


def test_run_notification_flags_a_stop_out(config):
    report = _report()
    report["price_update"]["updates"][0].update({"closed": True, "pnl_pct": -85.0})
    report["price_update"]["closed"] = 1
    message = tb.format_run_notification(report, config)
    assert "Closed" in message
    assert "-85.0%" in message
    assert "-80% threshold" in message


def test_run_notification_reports_a_skipped_weekend_screen(config):
    report = _report(
        screening_ran=False,
        new_calls=[],
        session={"as_of": "2026-09-19T10:00:00-04:00", "reason": "weekend — US market closed"},
    )
    message = tb.format_run_notification(report, config)
    assert "Screening skipped" in message
    assert "weekend" in message


def test_run_notification_can_include_role_detail(config):
    config["telegram"]["include_role_detail"] = True
    report = _report(
        reviews=[
            {
                "ticker": "SQZX",
                "verdicts": {
                    "researcher": {"score": 8.1},
                    "technician": {"score": 6.0},
                    "skeptic": {"score": 2.0, "strongest_objection": "none found"},
                    "risk_manager": {"score": 7.5},
                },
            }
        ]
    )
    message = tb.format_run_notification(report, config)
    assert "R 8.1" in message and "S 2.0 (severity)" in message
    assert "objection: none found" in message


def test_run_notification_surfaces_errors(config):
    message = tb.format_run_notification(_report(errors=["screening failed: HTTP 503"]), config)
    assert "screening failed: HTTP 503" in message


def test_stats_message_full_includes_every_breakdown(tmp_db, config):
    from stats import compute_stats

    call_id = tmp_db.insert_call(review_payload("AAA", entry=10.0), run_id="r1")
    tmp_db.apply_price(call_id, 12.0, close_threshold_pct=-80.0)
    message = tb.format_stats_message(compute_stats(tmp_db, config))
    for heading in (
        "By direction",
        "By asset type",
        "By variant",
        "By confidence",
        "Role accuracy",
    ):
        assert heading in message
    assert "lower is better" in message  # the skeptic polarity reminder


def test_calls_message_handles_an_empty_list():
    assert "(none)" in tb.format_calls_message([], title="Open calls")


def test_calls_message_marks_winners_and_stop_outs(tmp_db):
    winner = tmp_db.insert_call(review_payload("WIN", entry=10.0), run_id="r1")
    loser = tmp_db.insert_call(review_payload("LOSE", entry=10.0), run_id="r1")
    tmp_db.apply_price(winner, 12.0, close_threshold_pct=-80.0)
    tmp_db.apply_price(loser, 1.0, close_threshold_pct=-80.0)
    message = tb.format_calls_message(list(tmp_db.all_calls()), title="Recent calls")
    assert "🟢" in message and "🔴" in message
    assert "+20.0%" in message and "-90.0%" in message


def test_help_hides_run_when_disabled(config):
    assert "/run" in tb.format_help(config)
    assert "disabled" in tb.format_help(config)
    config["telegram"]["allow_run_command"] = True
    assert "run a full tracker cycle" in tb.format_help(config)


# ----------------------------------------------------------------- commands


def _handle(command, config, db_path, *, chat="4242", args=None, run_fn=None):
    return tb.handle_command(
        command,
        args or [],
        config=config,
        db_path=db_path,
        chat_id=chat,
        allowed=tb.authorized_chats(config, "4242"),
        run_cycle_fn=run_fn,
    )


def test_parse_command_strips_the_bot_mention():
    assert tb.parse_command("/calls@lowcap_bot 25") == ("/calls", ["25"])
    assert tb.parse_command("  /Stats ") == ("/stats", [])
    assert tb.parse_command("not a command") == ("", [])
    assert tb.parse_command("") == ("", [])


def test_unauthorized_chat_gets_nothing_but_a_refusal(config, tmp_db):
    reply = _handle("/stats", config, tmp_db.path, chat="999")
    assert reply == "Not authorized."


def test_id_works_from_any_chat_and_flags_authorization(config, tmp_db):
    mine = _handle("/id", config, tmp_db.path, chat="4242")
    theirs = _handle("/id", config, tmp_db.path, chat="999")
    assert "4242" in mine and "not authorized" not in mine
    assert "999" in theirs and "not authorized" in theirs


def test_extra_chat_ids_are_authorized(config, tmp_db):
    config["telegram"]["extra_chat_ids"] = [777]
    reply = tb.handle_command(
        "/help",
        [],
        config=config,
        db_path=tmp_db.path,
        chat_id="777",
        allowed=tb.authorized_chats(config, "4242"),
    )
    assert "Lowcap tracker bot" in reply


def test_open_and_shadow_commands(config, tmp_db):
    tmp_db.insert_call(review_payload("AAA", entry=10.0), run_id="r1")
    tmp_db.insert_call(review_payload("BBB", decision="SKIP", entry=5.0), run_id="r1")
    assert "AAA" in _handle("/open", config, tmp_db.path)
    shadow = _handle("/shadow", config, tmp_db.path)
    assert "BBB" in shadow and "AAA" not in shadow


def test_calls_command_respects_its_limit(config, tmp_db):
    for index in range(5):
        tmp_db.insert_call(review_payload(f"T{index}", entry=10.0), run_id="r1")
    assert _handle("/calls", config, tmp_db.path, args=["2"]).count("→") == 2


def test_last_command_reports_the_most_recent_run(config, tmp_db):
    assert "No runs recorded yet" in _handle("/last", config, tmp_db.path)
    tmp_db.start_run("run_1", session_reason="regular trading hours", screening_ran=True)
    tmp_db.finish_run(
        "run_1",
        {
            "hits": 4,
            "reviewed": 3,
            "new_calls": 2,
            "new_takes": 1,
            "new_shadows": 1,
            "closed": 0,
            "priced": 3,
            "backend": "heuristic",
            "llm_cost_usd": 0.02,
        },
    )
    reply = _handle("/last", config, tmp_db.path)
    assert "run_1" in reply and "1 TAKE / 1 shadow" in reply


def test_run_command_is_disabled_by_default(config, tmp_db):
    called = []
    reply = _handle("/run", config, tmp_db.path, run_fn=lambda: called.append(1) or _report())
    assert "disabled" in reply
    assert called == []


def test_run_command_executes_when_explicitly_enabled(config, tmp_db):
    config["telegram"]["allow_run_command"] = True
    reply = _handle("/run", config, tmp_db.path, run_fn=_report)
    assert "Lowcap tracker" in reply


def test_unknown_command(config, tmp_db):
    assert "Unknown command" in _handle("/nope", config, tmp_db.path)


# ------------------------------------------------------------------ polling


def _update(update_id, text, chat="4242"):
    return {"update_id": update_id, "message": {"chat": {"id": chat}, "text": text}}


def test_process_updates_replies_and_advances_the_offset(wired, tmp_db):
    config, sent, transport = wired
    client = _client(config, transport)
    offset = tb.process_updates(
        client,
        [_update(10, "/help"), _update(11, "/open")],
        config=config,
        db_path=tmp_db.path,
    )
    assert offset == 12
    assert len(sent) == 2
    assert "Lowcap tracker bot" in sent[0]["text"]


def test_process_updates_ignores_non_commands(wired, tmp_db):
    config, sent, transport = wired
    client = _client(config, transport)
    tb.process_updates(client, [_update(1, "just chatting")], config=config, db_path=tmp_db.path)
    assert sent == []


def test_a_failing_command_replies_instead_of_crashing(wired, tmp_db, monkeypatch):
    config, sent, transport = wired
    client = _client(config, transport)
    monkeypatch.setattr(
        tb, "format_help", lambda _config: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    offset = tb.process_updates(client, [_update(3, "/help")], config=config, db_path=tmp_db.path)
    assert offset == 4
    assert "Command failed" in sent[0]["text"] and "boom" in sent[0]["text"]


def test_poll_once_persists_the_offset(wired, tmp_db, tmp_path):
    config, sent, _transport = wired
    config["telegram"]["offset_file"] = str(tmp_path / "offset.json")
    batches = [[_update(20, "/help")], []]

    def transport(method, payload):
        if method == "getUpdates":
            assert payload.get("offset") in (None, 21)
            return batches.pop(0)
        sent.append(payload)
        return {"message_id": 1}

    client = _client(config, transport)
    assert tb.poll_once(client, config=config, db_path=tmp_db.path) == 1
    assert tb.load_offset(config) == 21
    # A restart must not replay the handled update.
    assert tb.poll_once(client, config=config, db_path=tmp_db.path) == 0
    assert len(sent) == 1


def test_offset_file_survives_corruption(config, tmp_path):
    path = tmp_path / "offset.json"
    path.write_text("not json", encoding="utf-8")
    config["telegram"]["offset_file"] = str(path)
    assert tb.load_offset(config) is None
    tb.save_offset(config, 99)
    assert tb.load_offset(config) == 99


# ------------------------------------------------------------- notify layer


def test_notify_is_a_no_op_without_credentials(monkeypatch, config):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    result = tb.notify(config, "hello")
    assert result == {"sent": False, "reason": "TELEGRAM_BOT_TOKEN is not set"}


def test_notify_swallows_transport_failures(wired):
    config, _sent, _transport = wired

    def broken(_method, _payload):
        raise tb.TelegramError("network down")

    result = tb.notify(config, "hello", transport=broken)
    assert result["sent"] is False
    assert "network down" in result["reason"]


@pytest.mark.parametrize(
    ("when", "report_kwargs", "expected"),
    [
        ("always", {"new_calls": []}, True),
        ("changes", {"new_calls": []}, False),
        ("changes", {}, True),
        ("changes", {"new_calls": [], "errors": ["boom"]}, True),
    ],
)
def test_should_notify_follows_notify_when(config, when, report_kwargs, expected):
    config["telegram"]["notify_when"] = when
    assert tb.should_notify(_report(**report_kwargs), config) is expected


def test_quiet_runs_are_sent_silently(wired):
    config, sent, transport = wired
    config["telegram"]["notify_when"] = "always"
    result = tb.notify_run(_report(new_calls=[]), config, transport=transport)
    assert result["sent"] is True
    assert sent[0]["disable_notification"] is True


def test_runs_with_news_ring_the_phone(wired):
    config, sent, transport = wired
    tb.notify_run(_report(), config, transport=transport)
    assert sent[0]["disable_notification"] is False


# -------------------------------------------------------- cycle integration


def test_cycle_sends_a_notification(wired, tmp_path, monkeypatch):
    config, sent, transport = wired
    config["tracker"]["stats_file"] = str(tmp_path / "stats.md")
    monkeypatch.setattr(
        tb, "build_client", lambda cfg, transport=None: _client(cfg, transport=transport)
    )
    import run_cycle as rc

    monkeypatch.setattr(
        rc, "notify_run", lambda report, cfg: tb.notify_run(report, cfg, transport=transport)
    )
    report = run_cycle(
        config,
        backend="heuristic",
        offline=True,
        fixture=str(FIXTURE_HITS),
        prices={},
        force_screen=True,
        db_path=str(tmp_path / "cycle.db"),
        now=datetime(2026, 9, 18, 15, 0, tzinfo=timezone.utc),
    )
    assert report["telegram"]["sent"] is True
    assert "SQZX" in sent[0]["text"]


def test_cycle_can_opt_out(config, tmp_path):
    config["tracker"]["stats_file"] = str(tmp_path / "stats.md")
    report = run_cycle(
        config,
        backend="heuristic",
        offline=True,
        fixture=str(FIXTURE_HITS),
        prices={},
        force_screen=True,
        db_path=str(tmp_path / "cycle.db"),
        telegram=False,
        now=datetime(2026, 9, 18, 15, 0, tzinfo=timezone.utc),
    )
    assert "telegram" not in report


def test_dry_run_never_notifies(config, tmp_path):
    config["tracker"]["stats_file"] = str(tmp_path / "stats.md")
    report = run_cycle(
        config,
        backend="heuristic",
        offline=True,
        fixture=str(FIXTURE_HITS),
        prices={},
        force_screen=True,
        dry_run=True,
        db_path=str(tmp_path / "cycle.db"),
        now=datetime(2026, 9, 18, 15, 0, tzinfo=timezone.utc),
    )
    assert report["telegram"] == {"sent": False, "reason": "dry run"}


def test_a_broken_bot_never_fails_a_run(wired, tmp_path, monkeypatch):
    config, _sent, _transport = wired
    config["tracker"]["stats_file"] = str(tmp_path / "stats.md")

    def broken(_method, _payload):
        raise tb.TelegramError("telegram is down")

    import run_cycle as rc

    monkeypatch.setattr(
        rc, "notify_run", lambda report, cfg: tb.notify_run(report, cfg, transport=broken)
    )
    report = run_cycle(
        config,
        backend="heuristic",
        offline=True,
        fixture=str(FIXTURE_HITS),
        prices={},
        force_screen=True,
        db_path=str(tmp_path / "cycle.db"),
        now=datetime(2026, 9, 18, 15, 0, tzinfo=timezone.utc),
    )
    assert report["telegram"]["sent"] is False
    assert len(report["new_calls"]) == 3  # the run itself completed


# ------------------------------------------------------------ learning loop


def test_learning_loop_summary_lists_proposals(tmp_db, config):
    from learning_loop import analyse, telegram_summary

    config["learning"]["min_samples"] = 4
    for index in range(6):
        call_id = tmp_db.insert_call(
            review_payload(f"BAD{index}", entry=10.0, variant="squeeze"), run_id="r1"
        )
        tmp_db.apply_price(call_id, 7.0, close_threshold_pct=-80.0)
    message = telegram_summary(analyse(tmp_db, config))
    assert "Weekly learning loop" in message
    assert "nothing applied automatically" in message
    assert "squeeze" in message
    assert "improvements.md" in message


def test_learning_loop_summary_when_there_is_nothing_to_propose(tmp_db, config):
    from learning_loop import analyse, telegram_summary

    message = telegram_summary(analyse(tmp_db, config))
    assert "Weekly learning loop" in message


# --------------------------------------------------------------- group chats


def test_group_chat_ids_are_negative_and_work(monkeypatch, config):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-1001234567890")
    assert tb.credentials(config) == ("t", "-1001234567890")
    assert tb.authorized_chats(config, "-1001234567890") == {"-1001234567890"}


def test_group_member_command_with_mention_is_authorized(config, tmp_db):
    """In privacy mode Telegram only delivers /cmd@bot, which must still work."""
    command, args = tb.parse_command("/calls@lowcap_tracker_bot 5")
    reply = tb.handle_command(
        command,
        args,
        config=config,
        db_path=tmp_db.path,
        chat_id="-1001234567890",
        allowed=tb.authorized_chats(config, "-1001234567890"),
    )
    assert "Recent calls" in reply


def test_a_different_group_is_not_authorized(config, tmp_db):
    reply = tb.handle_command(
        "/stats",
        [],
        config=config,
        db_path=tmp_db.path,
        chat_id="-1009999999999",
        allowed=tb.authorized_chats(config, "-1001234567890"),
    )
    assert reply == "Not authorized."


def test_push_targets_the_configured_group(wired, monkeypatch):
    config, sent, transport = wired
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-1001234567890")
    tb.notify(config, "group push", transport=transport)
    assert sent[0]["chat_id"] == "-1001234567890"


def _chat_update(update_id, chat_id, chat_type, title, text):
    return {
        "update_id": update_id,
        "message": {
            "chat": {"id": chat_id, "type": chat_type, "title": title},
            "from": {"username": "operator"},
            "text": text,
        },
    }


def test_discover_chats_summarizes_pending_updates(wired):
    config, _sent, _transport = wired
    updates = [
        _chat_update(1, -1001234567890, "supergroup", "Lowcap calls", "/id@bot"),
        _chat_update(2, -1001234567890, "supergroup", "Lowcap calls", "again"),
        {
            "update_id": 3,
            "message": {
                "chat": {"id": 4242, "type": "private", "first_name": "You"},
                "from": {"first_name": "You"},
                "text": "/start",
            },
        },
    ]
    client = _client(config, lambda method, payload: updates)
    chats = tb.discover_chats(client)
    assert [chat["chat_id"] for chat in chats] == ["-1001234567890", "4242"]  # de-duplicated
    assert chats[0]["type"] == "supergroup"
    assert chats[0]["title"] == "Lowcap calls"
    assert chats[1]["title"] == "You"


def test_discover_chats_does_not_consume_updates(wired, tmp_path):
    """Reading ids must not advance the offset a running poller depends on."""
    config, _sent, _transport = wired
    config["telegram"]["offset_file"] = str(tmp_path / "offset.json")
    tb.save_offset(config, 500)
    seen_payloads = []

    def transport(method, payload):
        seen_payloads.append(payload)
        return [_chat_update(1, -100123, "group", "G", "/id")]

    tb.discover_chats(_client(config, transport))
    assert "offset" not in seen_payloads[0]
    assert tb.load_offset(config) == 500  # untouched


def test_chat_list_marks_the_configured_chat():
    rendered = tb.format_chat_list(
        [
            {
                "chat_id": "-1001234567890",
                "type": "supergroup",
                "title": "Lowcap calls",
                "from": "",
                "text": "",
            },
            {"chat_id": "4242", "type": "private", "title": "You", "from": "You", "text": ""},
        ],
        configured="-1001234567890",
    )
    assert "<- configured" in rendered
    assert rendered.count("configured") == 1
    assert "group ids are negative" in rendered


def test_empty_chat_list_explains_what_to_do():
    rendered = tb.format_chat_list([])
    assert "No pending updates" in rendered
    assert "/id@yourbot" in rendered
    assert "lowcap-telegram.service" in rendered


# ------------------------------------------------------- chat id validation


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("4242", "4242"),
        ("  4242  ", "4242"),
        ("-1001234567890", "-1001234567890"),
        ("@lowcapcalls", "@lowcapcalls"),
        ("https://t.me/lowcapcalls", "@lowcapcalls"),
        ("t.me/lowcapcalls", "@lowcapcalls"),
    ],
)
def test_accepted_chat_id_forms(raw, expected):
    assert tb.normalize_chat_id(raw) == expected


@pytest.mark.parametrize(
    "link",
    [
        "https://t.me/+xPW86d7J9yQ5YjBk",
        "t.me/+AbCdEfGhIjK",
        "https://t.me/joinchat/AbCdEfGhIjK",
        "T.ME/+MixedCase",
    ],
)
def test_private_invite_links_are_rejected_with_guidance(link):
    """An invite hash is a server-side token; it is not a chat id."""
    with pytest.raises(tb.TelegramDisabled) as excinfo:
        tb.normalize_chat_id(link)
    message = str(excinfo.value)
    assert "invite link" in message
    assert "--list-chats" in message  # the actual next step
    assert "/id@yourbot" in message


def test_nonsense_chat_id_is_rejected():
    with pytest.raises(tb.TelegramDisabled, match="not a chat id"):
        tb.normalize_chat_id("my trading group")


def test_empty_chat_id_keeps_its_original_message():
    with pytest.raises(tb.TelegramDisabled, match="is not set"):
        tb.normalize_chat_id("   ")


def test_an_invite_link_in_the_env_does_not_break_a_run(monkeypatch, config, tmp_path):
    """Misconfiguration is reported, never fatal: the cycle still completes."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "https://t.me/+xPW86d7J9yQ5YjBk")
    config["tracker"]["stats_file"] = str(tmp_path / "stats.md")
    report = run_cycle(
        config,
        backend="heuristic",
        offline=True,
        fixture=str(FIXTURE_HITS),
        prices={},
        force_screen=True,
        db_path=str(tmp_path / "cycle.db"),
        now=datetime(2026, 9, 18, 15, 0, tzinfo=timezone.utc),
    )
    assert report["telegram"]["sent"] is False
    assert "invite link" in report["telegram"]["reason"]
    assert len(report["new_calls"]) == 3


def test_public_link_form_is_usable_as_a_push_target(wired, monkeypatch):
    config, sent, transport = wired
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "https://t.me/lowcapcalls")
    tb.notify(config, "channel push", transport=transport)
    assert sent[0]["chat_id"] == "@lowcapcalls"


# ------------------------------------------------------------- bot profile


def test_setup_profile_publishes_the_menu_description_and_about(config):
    calls = {}

    def transport(method, payload):
        calls[method] = payload
        return True

    result = tb.setup_profile(_client(config, transport), config=config)
    assert set(calls) == {"setMyCommands", "setMyDescription", "setMyShortDescription"}
    names = [entry["command"] for entry in calls["setMyCommands"]["commands"]]
    assert names == [
        "report",
        "stats",
        "open",
        "calls",
        "shadow",
        "call",
        "last",
        "id",
        "help",
    ]
    assert "run" not in names  # disabled by default, so not advertised
    assert result["published"] == 9
    # Telegram's own limits.
    assert len(calls["setMyDescription"]["description"]) <= 512
    assert len(calls["setMyShortDescription"]["short_description"]) <= 120
    for entry in calls["setMyCommands"]["commands"]:
        assert entry["command"] == entry["command"].lower()
        assert len(entry["description"]) <= 256


def test_setup_profile_advertises_run_only_when_enabled(config):
    calls = {}
    config["telegram"]["allow_run_command"] = True
    tb.setup_profile(_client(config, lambda m, p: calls.setdefault(m, p) or True), config=config)
    names = [entry["command"] for entry in calls["setMyCommands"]["commands"]]
    assert "run" in names
    assert names[-1] == "help"  # help stays last in the menu


def test_menu_and_help_cover_the_same_commands(config):
    """The published menu must not drift from what the bot actually answers."""
    help_text = tb.format_help(config)
    for name, _description in tb.BOT_COMMANDS:
        assert f"/{name}" in help_text


# ------------------------------------------------------- reporting contract


def test_stats_on_an_empty_tracker_reads_as_a_sentence(tmp_db, config):
    """'hit rate None%' is not an acceptable thing to send someone."""
    from stats import compute_stats

    message = tb.format_stats_message(compute_stats(tmp_db, config), compact=True)
    assert "None" not in message
    assert "No calls yet" in message


def test_no_message_ever_contains_the_word_none(tmp_db, config):
    """A None leaking into a message is a reporting bug, everywhere."""
    from stats import compute_stats

    call_id = tmp_db.insert_call(review_payload("AAA", entry=10.0), run_id="r1")
    tmp_db.conn.execute(
        "UPDATE calls SET current_price = NULL, pnl_pct = NULL WHERE id = ?", (call_id,)
    )
    tmp_db.conn.commit()
    rows = list(tmp_db.all_calls())
    messages = [
        tb.format_stats_message(compute_stats(tmp_db, config)),
        tb.format_calls_message(rows, title="Recent calls"),
        tb.format_report_message(tmp_db, config),
        tb.format_call_detail(tmp_db, "AAA"),
        tb.format_run_notification(_report(), config),
    ]
    for message in messages:
        assert "None" not in message, message
        assert "—" in message or "no price" in message


def test_an_unpriced_open_call_still_appears_in_the_run_report(config):
    """Regression: a call yfinance cannot price used to vanish from the message."""
    report = _report()
    report["price_update"]["updates"] = [
        {
            "ticker": "SSDEV",
            "direction": "long",
            "kind": "shadow",
            "entry_price": 1.04,
            "price": 1.04,
            "pnl_pct": 0.0,
            "closed": False,
            "priced": False,
            "stale_days": 3,
            "age_days": 4,
        }
    ]
    report["price_update"]["missing_prices"] = ["SSDEV"]
    message = tb.format_run_notification(report, config)
    assert "SSDEV" in message
    assert "no price for 3d" in message
    assert "4d" in message  # how long the call has been open


def test_report_command_covers_open_closed_and_stats(tmp_db, config):
    winner = tmp_db.insert_call(review_payload("WIN", entry=10.0), run_id="r1")
    tmp_db.apply_price(winner, 13.0, close_threshold_pct=-80.0)
    dead = tmp_db.insert_call(review_payload("DEAD", entry=10.0), run_id="r1")
    tmp_db.apply_price(dead, 1.0, close_threshold_pct=-80.0)
    tmp_db.start_run("r1", session_reason="regular trading hours", screening_ran=True)
    tmp_db.finish_run(
        "r1",
        {
            "hits": 2,
            "reviewed": 2,
            "new_calls": 2,
            "new_takes": 2,
            "new_shadows": 0,
            "closed": 1,
            "priced": 2,
            "backend": "heuristic",
            "llm_cost_usd": 0.0,
        },
    )
    message = tb.format_report_message(tmp_db, config)
    assert "Tracker report" in message
    assert "WIN" in message and "+30.0%" in message
    assert "Closed" in message and "DEAD" in message
    assert "hit rate" in message
    assert "last run" in message


def test_report_on_an_empty_tracker_says_so(tmp_db, config):
    message = tb.format_report_message(tmp_db, config)
    assert "<b>Open</b> — none" in message
    assert "No calls yet" in message


def test_call_detail_shows_every_role(tmp_db, config):
    call_id = tmp_db.insert_call(
        review_payload("AAA", entry=10.0, scores=(8.0, 7.0, 2.0, 6.0)), run_id="r1"
    )
    tmp_db.apply_price(call_id, 11.0, close_threshold_pct=-80.0)
    message = tb.format_call_detail(tmp_db, "aaa")  # case-insensitive
    assert "AAA" in message
    assert "Researcher 8.0" in message
    assert "Technician 7.0" in message
    assert "Skeptic 2.0" in message and "severity" in message
    assert "Risk 6.0" in message
    assert "+10.0%" in message


def test_call_detail_labels_an_unanswered_objection_correctly(tmp_db, config):
    review = review_payload("BBB", decision="SKIP", entry=4.0)
    review["verdicts"]["judge"] = {
        "role": "judge",
        "decision": "SKIP",
        "reason": "Skeptic objection unanswered (dilution)",
        "skeptic_objections_answered": False,
        "skeptic_answer": "Objection stands unanswered: offering risk",
        "gate_overrides": ["Skeptic objection not explicitly answered"],
    }
    tmp_db.insert_call(review, run_id="r1")
    message = tb.format_call_detail(tmp_db, "BBB")
    assert "objection NOT answered" in message
    assert "gate:" in message


def test_call_detail_for_an_unknown_ticker(tmp_db):
    assert "No call for" in tb.format_call_detail(tmp_db, "NOPE")


def test_call_command_requires_a_ticker(config, tmp_db):
    assert "Usage: /call" in _handle("/call", config, tmp_db.path)


def test_report_and_call_are_in_help_and_the_menu(config):
    help_text = tb.format_help(config)
    assert "/report" in help_text and "/call TICKER" in help_text
    assert [name for name, _ in tb.BOT_COMMANDS if name in {"report", "call"}] == ["report", "call"]
