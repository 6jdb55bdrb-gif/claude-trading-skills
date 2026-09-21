"""Invite codes, subscribers and multi-chat broadcast."""

from datetime import datetime, timedelta, timezone

import membership as ms
import pytest

from conftest import FIXTURE_HITS

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


# --------------------------------------------------------------- invite codes


def test_generated_codes_are_unambiguous_and_unique():
    codes = {ms.generate_code() for _ in range(200)}
    assert len(codes) > 190  # collisions are vanishingly rare
    for code in codes:
        assert len(code) == ms.CODE_LENGTH
        assert set(code) <= set(ms.CODE_ALPHABET)
        # No characters a person can misread when retyping a link.
        assert not set(code) & set("O0I1l")


def test_invite_link_uses_the_telegram_deep_link_form():
    link = ms.invite_link("Lowcaptrackerbot", "ABCD2345")
    assert link == "https://t.me/Lowcaptrackerbot?start=ABCD2345"
    assert ms.invite_link("@Lowcaptrackerbot", "ABCD2345") == link


def test_create_invite_records_limits(tmp_db):
    invite = ms.create_invite(
        tmp_db, created_by="4242", max_uses=3, expires_days=7, note="poker friends", now=NOW
    )
    assert invite["max_uses"] == 3
    assert invite["uses"] == 0
    assert invite["created_by"] == "4242"
    assert invite["note"] == "poker friends"
    assert invite["expires_at"] == _iso(NOW + timedelta(days=7))
    assert ms.list_invites(tmp_db)[0]["code"] == invite["code"]


def test_invite_without_expiry_never_expires(tmp_db):
    invite = ms.create_invite(tmp_db, created_by="4242", expires_days=None, now=NOW)
    assert invite["expires_at"] is None
    result = ms.redeem_invite(tmp_db, invite["code"], chat_id="99", now=NOW + timedelta(days=3650))
    assert result["ok"] is True


# ------------------------------------------------------------------ redeeming


def test_redeeming_an_invite_creates_a_member(tmp_db):
    invite = ms.create_invite(tmp_db, created_by="4242", now=NOW)
    result = ms.redeem_invite(tmp_db, invite["code"], chat_id="777", display_name="Robin", now=NOW)
    assert result["ok"] is True
    member = ms.subscriber(tmp_db, "777")
    assert member["role"] == ms.ROLE_MEMBER
    assert member["status"] == ms.STATUS_ACTIVE
    assert member["display_name"] == "Robin"
    assert member["invite_code"] == invite["code"]
    assert member["invited_by"] == "4242"
    assert ms.list_invites(tmp_db)[0]["uses"] == 1


def test_code_matching_ignores_case_and_padding(tmp_db):
    invite = ms.create_invite(tmp_db, created_by="4242", now=NOW)
    result = ms.redeem_invite(tmp_db, f"  {invite['code'].lower()} ", chat_id="777", now=NOW)
    assert result["ok"] is True


def test_an_unknown_code_is_refused(tmp_db):
    result = ms.redeem_invite(tmp_db, "NOPENOPE", chat_id="777", now=NOW)
    assert result["ok"] is False
    assert result["reason"] == "unknown"
    assert ms.subscriber(tmp_db, "777") is None


def test_an_expired_code_is_refused(tmp_db):
    invite = ms.create_invite(tmp_db, created_by="4242", expires_days=1, now=NOW)
    result = ms.redeem_invite(tmp_db, invite["code"], chat_id="777", now=NOW + timedelta(days=2))
    assert result["ok"] is False
    assert result["reason"] == "expired"


def test_a_spent_code_is_refused(tmp_db):
    invite = ms.create_invite(tmp_db, created_by="4242", max_uses=1, now=NOW)
    assert ms.redeem_invite(tmp_db, invite["code"], chat_id="777", now=NOW)["ok"] is True
    result = ms.redeem_invite(tmp_db, invite["code"], chat_id="888", now=NOW)
    assert result["ok"] is False
    assert result["reason"] == "spent"
    assert ms.subscriber(tmp_db, "888") is None


def test_a_revoked_code_is_refused(tmp_db):
    invite = ms.create_invite(tmp_db, created_by="4242", max_uses=5, now=NOW)
    assert ms.revoke_invite(tmp_db, invite["code"], now=NOW) is True
    result = ms.redeem_invite(tmp_db, invite["code"], chat_id="777", now=NOW)
    assert result["ok"] is False
    assert result["reason"] == "revoked"


def test_revoking_an_unknown_code_reports_failure(tmp_db):
    assert ms.revoke_invite(tmp_db, "NOPENOPE", now=NOW) is False


def test_redeeming_twice_is_idempotent_and_does_not_burn_a_use(tmp_db):
    invite = ms.create_invite(tmp_db, created_by="4242", max_uses=3, now=NOW)
    ms.redeem_invite(tmp_db, invite["code"], chat_id="777", now=NOW)
    again = ms.redeem_invite(tmp_db, invite["code"], chat_id="777", now=NOW)
    assert again["ok"] is True
    assert again["already_member"] is True
    assert ms.list_invites(tmp_db)[0]["uses"] == 1


def test_a_removed_member_can_rejoin_with_a_fresh_code(tmp_db):
    first = ms.create_invite(tmp_db, created_by="4242", now=NOW)
    ms.redeem_invite(tmp_db, first["code"], chat_id="777", now=NOW)
    ms.remove_subscriber(tmp_db, "777", now=NOW)
    assert ms.subscriber(tmp_db, "777")["status"] == ms.STATUS_REMOVED
    assert ms.list_subscribers(tmp_db) == []

    second = ms.create_invite(tmp_db, created_by="4242", now=NOW)
    result = ms.redeem_invite(tmp_db, second["code"], chat_id="777", now=NOW)
    assert result["ok"] is True
    assert ms.subscriber(tmp_db, "777")["status"] == ms.STATUS_ACTIVE


def test_a_banned_member_cannot_rejoin(tmp_db):
    invite = ms.create_invite(tmp_db, created_by="4242", max_uses=5, now=NOW)
    ms.redeem_invite(tmp_db, invite["code"], chat_id="777", now=NOW)
    ms.remove_subscriber(tmp_db, "777", now=NOW, banned=True)
    result = ms.redeem_invite(tmp_db, invite["code"], chat_id="777", now=NOW)
    assert result["ok"] is False
    assert result["reason"] == "banned"
    assert ms.subscriber(tmp_db, "777")["status"] == ms.STATUS_BANNED


# ------------------------------------------------------------------- access


def test_the_configured_owner_chat_is_an_admin(tmp_db, config):
    assert ms.access_for(tmp_db, config, owner_chat_id="4242", chat_id="4242") == ms.ROLE_ADMIN


def test_configured_admin_chat_ids_are_admins(tmp_db, config):
    config = {**config, "telegram": {**config["telegram"], "admin_chat_ids": [555]}}
    assert ms.access_for(tmp_db, config, owner_chat_id="4242", chat_id="555") == ms.ROLE_ADMIN


def test_extra_chat_ids_stay_members(tmp_db, config):
    config = {**config, "telegram": {**config["telegram"], "extra_chat_ids": [666]}}
    assert ms.access_for(tmp_db, config, owner_chat_id="4242", chat_id="666") == ms.ROLE_MEMBER


def test_a_stranger_has_no_access(tmp_db, config):
    assert ms.access_for(tmp_db, config, owner_chat_id="4242", chat_id="999") == ms.ROLE_NONE


def test_a_redeemed_member_has_access(tmp_db, config):
    invite = ms.create_invite(tmp_db, created_by="4242", now=NOW)
    ms.redeem_invite(tmp_db, invite["code"], chat_id="999", now=NOW)
    assert ms.access_for(tmp_db, config, owner_chat_id="4242", chat_id="999") == ms.ROLE_MEMBER


def test_a_removed_member_loses_access(tmp_db, config):
    invite = ms.create_invite(tmp_db, created_by="4242", now=NOW)
    ms.redeem_invite(tmp_db, invite["code"], chat_id="999", now=NOW)
    ms.remove_subscriber(tmp_db, "999", now=NOW)
    assert ms.access_for(tmp_db, config, owner_chat_id="4242", chat_id="999") == ms.ROLE_NONE


def test_open_access_mode_admits_anyone(tmp_db, config):
    config = {**config, "telegram": {**config["telegram"], "access_mode": "open"}}
    assert ms.access_for(tmp_db, config, owner_chat_id="4242", chat_id="999") == ms.ROLE_MEMBER


def test_closed_access_mode_refuses_even_a_valid_code(tmp_db, config):
    config = {**config, "telegram": {**config["telegram"], "access_mode": "closed"}}
    invite = ms.create_invite(tmp_db, created_by="4242", now=NOW)
    result = ms.redeem_invite(tmp_db, invite["code"], chat_id="999", config=config, now=NOW)
    assert result["ok"] is False
    assert result["reason"] == "closed"


def test_promoting_a_member_to_admin(tmp_db, config):
    invite = ms.create_invite(tmp_db, created_by="4242", now=NOW)
    ms.redeem_invite(tmp_db, invite["code"], chat_id="999", now=NOW)
    assert ms.set_role(tmp_db, "999", ms.ROLE_ADMIN) is True
    assert ms.access_for(tmp_db, config, owner_chat_id="4242", chat_id="999") == ms.ROLE_ADMIN


def test_set_role_rejects_an_unknown_role(tmp_db):
    with pytest.raises(ValueError):
        ms.set_role(tmp_db, "999", "superuser")


# ---------------------------------------------------------------- broadcast


def test_broadcast_targets_start_with_the_owner_and_never_repeat(tmp_db, config):
    config = {**config, "telegram": {**config["telegram"], "extra_chat_ids": [4242, 666]}}
    invite = ms.create_invite(tmp_db, created_by="4242", max_uses=5, now=NOW)
    ms.redeem_invite(tmp_db, invite["code"], chat_id="777", now=NOW)
    ms.redeem_invite(tmp_db, invite["code"], chat_id="888", now=NOW)
    targets = ms.broadcast_targets(tmp_db, config, owner_chat_id="4242")
    assert targets[0] == "4242"
    assert set(targets) == {"4242", "666", "777", "888"}
    assert len(targets) == len(set(targets))


def test_broadcast_skips_removed_and_blocked_members(tmp_db, config):
    invite = ms.create_invite(tmp_db, created_by="4242", max_uses=5, now=NOW)
    for chat in ("777", "888", "999"):
        ms.redeem_invite(tmp_db, invite["code"], chat_id=chat, now=NOW)
    ms.remove_subscriber(tmp_db, "888", now=NOW)
    ms.mark_blocked(tmp_db, "999", now=NOW)
    assert ms.broadcast_targets(tmp_db, config, owner_chat_id="4242") == ["4242", "777"]


def test_a_blocked_member_is_recorded_not_deleted(tmp_db):
    invite = ms.create_invite(tmp_db, created_by="4242", now=NOW)
    ms.redeem_invite(tmp_db, invite["code"], chat_id="777", now=NOW)
    ms.mark_blocked(tmp_db, "777", now=NOW)
    row = ms.subscriber(tmp_db, "777")
    assert row["status"] == ms.STATUS_BLOCKED
    assert row["left_at"] == _iso(NOW)


# ------------------------------------------------------------------ rendering


def test_member_list_renders_roles_and_counts(tmp_db):
    invite = ms.create_invite(tmp_db, created_by="4242", max_uses=5, now=NOW)
    ms.redeem_invite(tmp_db, invite["code"], chat_id="777", display_name="Robin", now=NOW)
    text = ms.format_members(ms.list_subscribers(tmp_db), owner_chat_id="4242")
    assert "Robin" in text
    assert "777" in text
    assert "None" not in text


def test_member_list_says_so_when_empty(tmp_db):
    text = ms.format_members(ms.list_subscribers(tmp_db), owner_chat_id="4242")
    assert "no" in text.lower()
    assert "None" not in text


def test_invite_list_shows_remaining_uses(tmp_db):
    ms.create_invite(tmp_db, created_by="4242", max_uses=3, expires_days=7, now=NOW)
    text = ms.format_invites(ms.list_invites(tmp_db), "Lowcaptrackerbot", now=NOW)
    assert "3 left" in text
    assert "https://t.me/Lowcaptrackerbot?start=" in text
    assert "None" not in text


def test_invite_list_says_so_when_empty(tmp_db):
    text = ms.format_invites([], "Lowcaptrackerbot", now=NOW)
    assert "no" in text.lower()


# ------------------------------------------------- bot commands and broadcast


@pytest.fixture()
def bot_env(monkeypatch, config, tmp_path):
    """Config with credentials, a database path, and a capturing transport."""
    import telegram_bot as tb

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "4242")
    monkeypatch.setattr(tb, "load_offset", lambda cfg: None)
    monkeypatch.setattr(tb, "save_offset", lambda cfg, offset: None)
    return tb, config, tmp_path / "bot.db"


def _reply(tb, config, db_path, text, chat_id="4242"):
    command, args = tb.parse_command(text)
    return tb.handle_command(
        command, args, config=config, db_path=db_path, chat_id=chat_id, owner_chat_id="4242"
    )


def test_a_stranger_is_refused_and_told_how_to_join(bot_env):
    tb, config, db_path = bot_env
    reply = _reply(tb, config, db_path, "/report", chat_id="999")
    assert "invite" in reply.lower()
    assert "SDEV" not in reply


def test_start_with_a_valid_code_admits_a_friend(bot_env):
    tb, config, db_path = bot_env
    from call_db import CallDatabase

    with CallDatabase(db_path) as db:
        invite = ms.create_invite(db, created_by="4242", now=NOW)
    reply = _reply(tb, config, db_path, f"/start {invite['code']}", chat_id="999")
    assert "welcome" in reply.lower()
    assert _reply(tb, config, db_path, "/open", chat_id="999") != "Not authorized."
    with CallDatabase(db_path) as db:
        assert ms.subscriber(db, "999")["status"] == ms.STATUS_ACTIVE


def test_start_with_a_bad_code_explains_why(bot_env):
    tb, config, db_path = bot_env
    reply = _reply(tb, config, db_path, "/start NOPENOPE", chat_id="999")
    assert "invite" in reply.lower()
    from call_db import CallDatabase

    with CallDatabase(db_path) as db:
        assert ms.subscriber(db, "999") is None


def test_only_an_admin_may_mint_an_invite(bot_env):
    tb, config, db_path = bot_env
    from call_db import CallDatabase

    with CallDatabase(db_path) as db:
        invite = ms.create_invite(db, created_by="4242", now=NOW)
    _reply(tb, config, db_path, f"/start {invite['code']}", chat_id="999")
    assert "admin" in _reply(tb, config, db_path, "/invite", chat_id="999").lower()


def test_an_admin_mints_a_link_a_friend_can_tap(bot_env, monkeypatch):
    tb, config, db_path = bot_env
    monkeypatch.setattr(tb, "bot_username", lambda config=None: "Lowcaptrackerbot")
    reply = _reply(tb, config, db_path, "/invite", chat_id="4242")
    assert "https://t.me/Lowcaptrackerbot?start=" in reply
    code = reply.split("?start=")[1].split()[0].split("<")[0].strip()
    assert _reply(tb, config, db_path, f"/start {code}", chat_id="777").lower().count("welcome")


def test_invite_accepts_a_use_count_and_a_lifetime(bot_env, monkeypatch):
    tb, config, db_path = bot_env
    monkeypatch.setattr(tb, "bot_username", lambda config=None: "Lowcaptrackerbot")
    _reply(tb, config, db_path, "/invite 5 30", chat_id="4242")
    from call_db import CallDatabase

    with CallDatabase(db_path) as db:
        row = ms.list_invites(db)[0]
    assert row["max_uses"] == 5
    assert row["expires_at"] is not None


def test_an_admin_sees_and_removes_a_member(bot_env):
    tb, config, db_path = bot_env
    from call_db import CallDatabase

    with CallDatabase(db_path) as db:
        invite = ms.create_invite(db, created_by="4242", now=NOW)
    _reply(tb, config, db_path, f"/start {invite['code']}", chat_id="999")
    assert "999" in _reply(tb, config, db_path, "/members", chat_id="4242")
    assert "removed" in _reply(tb, config, db_path, "/remove 999", chat_id="4242").lower()
    assert "invite" in _reply(tb, config, db_path, "/open", chat_id="999").lower()


def test_a_member_may_leave_on_their_own(bot_env):
    tb, config, db_path = bot_env
    from call_db import CallDatabase

    with CallDatabase(db_path) as db:
        invite = ms.create_invite(db, created_by="4242", now=NOW)
    _reply(tb, config, db_path, f"/start {invite['code']}", chat_id="999")
    assert _reply(tb, config, db_path, "/stop", chat_id="999")
    with CallDatabase(db_path) as db:
        assert ms.subscriber(db, "999")["status"] == ms.STATUS_REMOVED


def test_the_owner_cannot_remove_themselves(bot_env):
    tb, config, db_path = bot_env
    reply = _reply(tb, config, db_path, "/stop", chat_id="4242")
    assert "owner" in reply.lower()


def test_help_shows_admin_commands_only_to_admins(bot_env):
    tb, config, db_path = bot_env
    from call_db import CallDatabase

    with CallDatabase(db_path) as db:
        invite = ms.create_invite(db, created_by="4242", now=NOW)
    _reply(tb, config, db_path, f"/start {invite['code']}", chat_id="999")
    assert "/invite" in _reply(tb, config, db_path, "/help", chat_id="4242")
    assert "/invite" not in _reply(tb, config, db_path, "/help", chat_id="999")


def test_a_member_cannot_run_a_cycle(bot_env):
    tb, config, db_path = bot_env
    config = {**config, "telegram": {**config["telegram"], "allow_run_command": True}}
    from call_db import CallDatabase

    with CallDatabase(db_path) as db:
        invite = ms.create_invite(db, created_by="4242", now=NOW)
    _reply(tb, config, db_path, f"/start {invite['code']}", chat_id="999")
    command, args = tb.parse_command("/run")
    reply = tb.handle_command(
        command,
        args,
        config=config,
        db_path=db_path,
        chat_id="999",
        owner_chat_id="4242",
        run_cycle_fn=lambda: {"run_id": "x"},
    )
    assert "admin" in reply.lower()


def test_a_notification_reaches_every_member(bot_env):
    tb, config, db_path = bot_env
    from call_db import CallDatabase

    sent: list[dict] = []

    def transport(method, payload):
        sent.append(payload)
        return {"message_id": len(sent)}

    with CallDatabase(db_path) as db:
        invite = ms.create_invite(db, created_by="4242", max_uses=5, now=NOW)
        ms.redeem_invite(db, invite["code"], chat_id="777", now=NOW)
        ms.redeem_invite(db, invite["code"], chat_id="888", now=NOW)

    result = tb.notify(config, "hello", db_path=db_path, transport=transport)
    assert result["sent"] is True
    assert result["delivered"] == 3
    assert [payload["chat_id"] for payload in sent] == ["4242", "777", "888"]


def test_one_blocked_member_does_not_stop_the_others(bot_env):
    tb, config, db_path = bot_env
    from call_db import CallDatabase

    sent: list[dict] = []

    def transport(method, payload):
        if payload["chat_id"] == "777":
            raise tb.TelegramError("sendMessage: Forbidden: bot was blocked by the user")
        sent.append(payload)
        return {"message_id": len(sent)}

    with CallDatabase(db_path) as db:
        invite = ms.create_invite(db, created_by="4242", max_uses=5, now=NOW)
        ms.redeem_invite(db, invite["code"], chat_id="777", now=NOW)
        ms.redeem_invite(db, invite["code"], chat_id="888", now=NOW)

    result = tb.notify(config, "hello", db_path=db_path, transport=transport)
    assert result["delivered"] == 2
    assert result["failed"] == ["777"]
    assert [payload["chat_id"] for payload in sent] == ["4242", "888"]
    with CallDatabase(db_path) as db:
        assert ms.subscriber(db, "777")["status"] == ms.STATUS_BLOCKED


def test_a_transient_failure_does_not_unsubscribe_anyone(bot_env):
    tb, config, db_path = bot_env
    from call_db import CallDatabase

    def transport(method, payload):
        if payload["chat_id"] == "777":
            raise tb.TelegramError("sendMessage: Bad Gateway")
        return {"message_id": 1}

    with CallDatabase(db_path) as db:
        invite = ms.create_invite(db, created_by="4242", now=NOW)
        ms.redeem_invite(db, invite["code"], chat_id="777", now=NOW)

    result = tb.notify(config, "hello", db_path=db_path, transport=transport)
    assert result["failed"] == ["777"]
    with CallDatabase(db_path) as db:
        assert ms.subscriber(db, "777")["status"] == ms.STATUS_ACTIVE


# --------------------------------------------------------------- command menu


def test_the_default_menu_is_the_member_menu(bot_env):
    tb, config, _db = bot_env
    published: list[dict] = []

    def transport(method, payload):
        published.append({"method": method, **payload})
        return {}

    client = tb.TelegramClient(token="t", chat_id="4242", transport=transport)
    tb.setup_profile(client, config=config)
    default = next(
        call for call in published if call["method"] == "setMyCommands" and "scope" not in call
    )
    names = {entry["command"] for entry in default["commands"]}
    assert "invite" not in names
    assert {"report", "stats", "stop"} <= names


def test_admin_chats_get_the_admin_menu(bot_env):
    tb, config, _db = bot_env
    published: list[dict] = []

    def transport(method, payload):
        published.append({"method": method, **payload})
        return {}

    config = {**config, "telegram": {**config["telegram"], "admin_chat_ids": [555]}}
    client = tb.TelegramClient(token="t", chat_id="4242", transport=transport)
    tb.setup_profile(client, config=config)
    scoped = [call for call in published if call["method"] == "setMyCommands" and "scope" in call]
    assert {call["scope"]["chat_id"] for call in scoped} == {"4242", "555"}
    for call in scoped:
        assert "invite" in {entry["command"] for entry in call["commands"]}


# ------------------------------------------------------------------ snapshot


def test_the_committed_snapshot_carries_no_codes_or_chat_ids(tmp_path):
    """tracker-output/ is committed to a public repo: no secrets, no people."""
    from call_db import CallDatabase
    from state_snapshot import export_snapshot

    path = tmp_path / "snap.json"
    with CallDatabase(tmp_path / "a.db") as db:
        invite = ms.create_invite(db, created_by="4242", max_uses=5, now=NOW)
        ms.redeem_invite(db, invite["code"], chat_id="777", display_name="Robin", now=NOW)
        snapshot = export_snapshot(db, path)

    assert "subscribers" not in snapshot["tables"]
    assert "invites" not in snapshot["tables"]
    written = path.read_text()
    assert invite["code"] not in written
    assert "Robin" not in written


def test_members_and_invites_survive_their_own_round_trip(tmp_path):
    from call_db import CallDatabase
    from state_snapshot import export_members, import_members

    path = tmp_path / "members.json"
    with CallDatabase(tmp_path / "a.db") as db:
        invite = ms.create_invite(db, created_by="4242", max_uses=5, now=NOW)
        ms.redeem_invite(db, invite["code"], chat_id="777", display_name="Robin", now=NOW)
        exported = export_members(db, path)

    assert exported["counts"]["subscribers"] == 1

    with CallDatabase(tmp_path / "b.db") as db:
        import_members(db, path)
        member = ms.subscriber(db, "777")
        assert member["display_name"] == "Robin"
        assert ms.list_invites(db)[0]["uses"] == 1


def test_importing_members_does_not_clobber_a_live_member_list(tmp_path):
    from call_db import CallDatabase
    from state_snapshot import export_members, import_members

    path = tmp_path / "members.json"
    with CallDatabase(tmp_path / "a.db") as db:
        invite = ms.create_invite(db, created_by="4242", now=NOW)
        ms.redeem_invite(db, invite["code"], chat_id="777", now=NOW)
        export_members(db, path)

    with CallDatabase(tmp_path / "b.db") as db:
        other = ms.create_invite(db, created_by="4242", now=NOW)
        ms.redeem_invite(db, other["code"], chat_id="888", now=NOW)
        result = import_members(db, path)
        assert result["imported"] is False
        assert ms.subscriber(db, "888") is not None


def test_an_unknown_access_mode_is_rejected(tmp_path):
    import yaml

    from config import ConfigError, load_config

    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump({"telegram": {"access_mode": "everyone"}}))
    with pytest.raises(ConfigError, match="access_mode"):
        load_config(path)


def test_the_three_access_modes_load(tmp_path):
    import yaml

    from config import load_config

    for mode in ("invite", "open", "closed"):
        path = tmp_path / f"{mode}.yaml"
        path.write_text(yaml.safe_dump({"telegram": {"access_mode": mode}}))
        assert load_config(path)["telegram"]["access_mode"] == mode


# ----------------------------------------------------------------------- CLI


def test_cli_mints_an_invite(monkeypatch, tmp_path, capsys):
    import telegram_bot as tb
    from call_db import CallDatabase

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "4242")
    monkeypatch.setattr(tb, "bot_username", lambda config=None: "Lowcaptrackerbot")
    db_path = tmp_path / "cli.db"

    code = tb.main(["--db", str(db_path), "--invite", "3", "--invite-days", "5"])
    assert code == 0
    assert "https://t.me/Lowcaptrackerbot?start=" in capsys.readouterr().out
    with CallDatabase(db_path) as db:
        row = ms.list_invites(db)[0]
    assert row["max_uses"] == 3


def test_cli_lists_members(monkeypatch, tmp_path, capsys):
    import telegram_bot as tb
    from call_db import CallDatabase

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "4242")
    db_path = tmp_path / "cli.db"
    with CallDatabase(db_path) as db:
        invite = ms.create_invite(db, created_by="4242", now=NOW)
        ms.redeem_invite(db, invite["code"], chat_id="777", display_name="Robin", now=NOW)

    assert tb.main(["--db", str(db_path), "--members"]) == 0
    out = capsys.readouterr().out
    assert "777" in out and "Robin" in out


def test_a_cycle_keeps_members_out_of_the_committed_snapshot(tmp_path, config, monkeypatch):
    """The snapshot path a scheduled run commits must never carry a code."""
    from call_db import CallDatabase
    from run_cycle import run_cycle

    snapshot = tmp_path / "snap.json"
    members = tmp_path / "members.json"
    config = {
        **config,
        "tracker": {
            **config["tracker"],
            "snapshot_file": str(snapshot),
            "members_file": str(members),
            # Never the repository's own files: a test must not rewrite them.
            "stats_file": str(tmp_path / "stats.md"),
            "improvements_file": str(tmp_path / "improvements.md"),
            "reports_dir": str(tmp_path / "reports"),
        },
    }
    db_path = tmp_path / "cycle.db"
    with CallDatabase(db_path) as db:
        invite = ms.create_invite(db, created_by="4242", now=NOW)
        ms.redeem_invite(db, invite["code"], chat_id="777", display_name="Robin", now=NOW)

    run_cycle(
        config,
        backend="heuristic",
        offline=True,
        fixture=str(FIXTURE_HITS),
        prices={},
        force_screen=True,
        telegram=False,
        db_path=str(db_path),
        now=datetime(2026, 9, 18, 15, 0, tzinfo=timezone.utc),
    )

    assert invite["code"] not in snapshot.read_text()
    assert "Robin" not in snapshot.read_text()
    assert invite["code"] in members.read_text()
