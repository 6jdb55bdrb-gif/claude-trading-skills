"""Sibling-skill reuse adapters and the VPS deployment kit."""

import os
import re
import stat
import subprocess
from datetime import date, timedelta
from pathlib import Path

import pytest
from publish import publish_reports
from skill_adapters import run_episodic_pivot, run_position_sizer, run_weekly_price_action

from config import repo_root

DEPLOY = Path(__file__).resolve().parents[2] / "deploy"
SKILL_ROOT = Path(__file__).resolve().parents[2]


# ------------------------------------------------------------------- adapters


def test_position_sizer_skill_is_reused(config):
    result = run_position_sizer(entry=4.55, stop=4.05, config=config, sector="Technology")
    assert result is not None and "error" not in result
    assert result["shares"] > 0
    assert result["risk_usd"] == pytest.approx(
        config["tracker"]["account_size"] * config["tracker"]["risk_pct"] / 100, rel=0.2
    )


def test_position_sizer_rejects_a_useless_stop(config):
    assert run_position_sizer(entry=0.0, stop=0.0, config=config) is None


def test_episodic_pivot_skill_classifies_the_catalyst(stock_hit):
    result = run_episodic_pivot(
        stock_hit, headline="Squeezex receives FDA approval for SQX-101", as_of="2026-09-18"
    )
    assert result is not None and "error" not in result
    assert result["catalyst_type"]
    assert result["composite_score"] > 0
    assert result["ep_type"]


def test_adapters_return_none_when_the_sibling_skill_is_absent(monkeypatch, stock_hit, config):
    import skill_adapters

    monkeypatch.setattr(skill_adapters, "repo_root", lambda: Path("/nonexistent-root"))
    assert run_episodic_pivot(stock_hit) is None
    assert run_position_sizer(entry=4.0, stop=3.5, config=config) is None
    assert run_weekly_price_action(stock_hit, [{"date": "2026-01-01", "close": 1}]) is None


def _synthetic_bars(days: int, start_price: float = 3.0) -> list[dict]:
    bars = []
    day = date(2026, 9, 18) - timedelta(days=days)
    price = start_price
    for index in range(days):
        day += timedelta(days=1)
        if day.weekday() >= 5:
            continue
        price *= 1.004
        bars.append(
            {
                "date": day.isoformat(),
                "open": round(price * 0.99, 4),
                "high": round(price * 1.02, 4),
                "low": round(price * 0.97, 4),
                "close": round(price, 4),
                "volume": 1_000_000 + index * 1000,
            }
        )
    return bars


def test_weekly_price_action_skill_is_reused(stock_hit):
    result = run_weekly_price_action(stock_hit, _synthetic_bars(500), as_of="2026-09-18")
    assert result is not None and "error" not in result
    assert result["verdict"]
    assert result["weekly_bars_used"] > 10


def test_weekly_price_action_reports_insufficient_history(stock_hit):
    result = run_weekly_price_action(stock_hit, _synthetic_bars(20), as_of="2026-09-18")
    assert result["verdict"] == "INSUFFICIENT_DATA"
    assert result["checks"] is None


# -------------------------------------------------------------------- publish


def _git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


def test_publish_stages_only_the_two_report_files(config, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "-q", "-b", "main"], repo)
    _git(["config", "user.email", "t@example.com"], repo)
    _git(["config", "user.name", "t"], repo)
    (repo / "code.py").write_text("print('untouched')\n", encoding="utf-8")
    output = repo / "tracker-output"
    output.mkdir()
    (output / "stats.md").write_text("# stats\n", encoding="utf-8")
    (output / "improvements.md").write_text("# improvements\n", encoding="utf-8")

    config["tracker"]["stats_file"] = str(output / "stats.md")
    config["tracker"]["improvements_file"] = str(output / "improvements.md")
    result = publish_reports(config, dry_run=True, root=repo)

    assert sorted(result["files"]) == [
        "tracker-output/improvements.md",
        "tracker-output/stats.md",
    ]
    staged = _git(["diff", "--cached", "--name-only"], repo).stdout.split()
    assert "code.py" not in staged


def test_publish_is_a_no_op_without_changes(config, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "-q", "-b", "main"], repo)
    _git(["config", "user.email", "t@example.com"], repo)
    _git(["config", "user.name", "t"], repo)
    (repo / "stats.md").write_text("# stats\n", encoding="utf-8")
    _git(["add", "stats.md"], repo)
    _git(["commit", "-qm", "initial"], repo)

    config["tracker"]["stats_file"] = str(repo / "stats.md")
    config["tracker"]["improvements_file"] = str(repo / "missing.md")
    result = publish_reports(config, root=repo)
    assert result["pushed"] is False
    assert result["reason"] == "no changes in report files"


def test_publish_refuses_paths_outside_the_checkout(config, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "-q", "-b", "main"], repo)
    outside = tmp_path / "stats.md"
    outside.write_text("# stats\n", encoding="utf-8")
    config["tracker"]["stats_file"] = str(outside)
    config["tracker"]["improvements_file"] = str(tmp_path / "nope.md")
    result = publish_reports(config, root=repo)
    assert result["pushed"] is False


# --------------------------------------------------------------- deployment kit


@pytest.mark.parametrize(
    "name",
    [
        "setup_vps.sh",
        "update.sh",
        "run_tracker.sh",
        "run_learning.sh",
        "lowcap-tracker.service",
        "lowcap-tracker.timer",
        "lowcap-learning.service",
        "lowcap-learning.timer",
        "logrotate-lowcap-tracker",
        ".env.example",
        "VPS_SETUP.md",
    ],
)
def test_deploy_file_exists(name):
    assert (DEPLOY / name).is_file()


@pytest.mark.parametrize("name", ["setup_vps.sh", "update.sh", "run_tracker.sh", "run_learning.sh"])
def test_shell_scripts_are_executable_and_parse(name):
    path = DEPLOY / name
    assert path.stat().st_mode & stat.S_IXUSR
    assert subprocess.run(["bash", "-n", str(path)], capture_output=True).returncode == 0
    text = path.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in text


def test_timer_runs_every_four_hours_and_survives_reboots():
    timer = (DEPLOY / "lowcap-tracker.timer").read_text(encoding="utf-8")
    assert "OnCalendar=*-*-* 00/4:05:00" in timer
    assert "Persistent=true" in timer  # a missed run fires after boot
    assert "OnBootSec=" in timer


def test_weekly_learning_timer_exists():
    timer = (DEPLOY / "lowcap-learning.timer").read_text(encoding="utf-8")
    assert "OnCalendar=Sun" in timer
    assert "Unit=lowcap-learning.service" in timer


def test_service_runs_as_an_unprivileged_user():
    service = (DEPLOY / "lowcap-tracker.service").read_text(encoding="utf-8")
    assert "Type=oneshot" in service
    assert "User=lowcap" in service
    assert "NoNewPrivileges=true" in service
    assert "run_tracker.sh" in service


def test_logrotate_config_rotates_and_compresses():
    conf = (DEPLOY / "logrotate-lowcap-tracker").read_text(encoding="utf-8")
    assert "weekly" in conf and "rotate 8" in conf and "compress" in conf


def test_env_example_holds_placeholders_only():
    env = (DEPLOY / ".env.example").read_text(encoding="utf-8")
    assert "ANTHROPIC_API_KEY=sk-ant-..." in env
    assert "GIT_PUSH=1" in env
    # No real-looking secret material may ship in the repository.
    assert "sk-ant-api" not in env


def test_setup_script_covers_the_required_steps():
    script = (DEPLOY / "setup_vps.sh").read_text(encoding="utf-8")
    for needle in (
        "python3-venv",
        "python3 -m venv",
        "requirements.txt",
        "systemctl enable --now lowcap-tracker.timer",
        "logrotate.d/lowcap-tracker",
        "chmod 600",
        "ssh-keygen",
    ):
        assert needle in script, needle


def test_update_script_pulls_and_restarts():
    script = (DEPLOY / "update.sh").read_text(encoding="utf-8")
    assert "git pull --ff-only" in script
    assert "systemctl restart lowcap-tracker.timer" in script


def test_wrapper_loads_env_and_pushes_when_enabled():
    script = (DEPLOY / "run_tracker.sh").read_text(encoding="utf-8")
    assert '. "$APP_DIR/.env"' in script
    assert "--git-push" in script
    assert "run_cycle.py" in script


def test_vps_guide_is_written_for_a_non_coder():
    guide = (DEPLOY / "VPS_SETUP.md").read_text(encoding="utf-8")
    for needle in (
        "## Step 1 — Create the server",
        "## Step 2 — Connect to the server (SSH)",
        "## Step 3 — Download the repository and run the setup script",
        "## Step 4 — Add your API key",
        "## Step 5 — Let the server push results back to GitHub",
        "## Step 6 — Run it once, right now",
        "## Step 7 — Check that it keeps running",
        "## Step 8 — Updating later",
        "## Troubleshooting",
        "Ubuntu 24.04",
        "CX22",
        "systemctl list-timers",
        "tail -f",
    ):
        assert needle in guide, needle


def test_env_files_are_not_committed():
    tracked = subprocess.run(
        ["git", "ls-files", "skills/lowcap-call-tracker"],
        cwd=repo_root(),
        capture_output=True,
        text=True,
        check=False,
    ).stdout.split()
    assert not [path for path in tracked if path.endswith("/.env")]


def test_requirements_declare_optional_dependencies():
    text = (SKILL_ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "pyyaml" in text and "requests" in text and "yfinance" in text
    for line in text.splitlines():
        if line.startswith(("anthropic", "beautifulsoup4")):
            assert "# optional:" in line


def test_config_asset_is_packaged_with_the_skill():
    assert (SKILL_ROOT / "assets" / "tracker_config.yaml").is_file()
    assert (SKILL_ROOT / "scripts" / "fixtures" / "dry_run_hits.json").is_file()


def test_runtime_scripts_do_not_hardcode_home_paths():
    """This is a public repository: no developer paths in packaged code."""
    for path in (SKILL_ROOT / "scripts").glob("*.py"):  # tests/ is excluded
        text = path.read_text(encoding="utf-8")
        assert "/Users" + os.sep not in text
        assert os.sep + "home" + os.sep not in text


# ------------------------------------------------------ telegram deployment


def test_telegram_unit_and_wrapper_exist():
    assert (DEPLOY / "lowcap-telegram.service").is_file()
    wrapper = DEPLOY / "run_telegram.sh"
    assert wrapper.is_file()
    assert wrapper.stat().st_mode & stat.S_IXUSR
    assert subprocess.run(["bash", "-n", str(wrapper)], capture_output=True).returncode == 0


def test_telegram_service_restarts_on_failure():
    """Long-polling drops on any network blip, so the bot must come back."""
    unit = (DEPLOY / "lowcap-telegram.service").read_text(encoding="utf-8")
    assert "Restart=always" in unit
    assert "run_telegram.sh" in unit
    assert "User=lowcap" in unit


def test_telegram_wrapper_exits_quietly_without_a_token():
    script = (DEPLOY / "run_telegram.sh").read_text(encoding="utf-8")
    assert 'if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]' in script
    assert "--poll" in script


def test_setup_enables_the_bot_only_when_a_token_is_present():
    script = (DEPLOY / "setup_vps.sh").read_text(encoding="utf-8")
    assert "lowcap-telegram.service" in script
    assert "TELEGRAM_BOT_TOKEN=.+" in script  # the grep guard
    assert "systemctl enable --now lowcap-telegram.service" in script


def test_update_script_only_bounces_an_enabled_bot():
    script = (DEPLOY / "update.sh").read_text(encoding="utf-8")
    assert "is-enabled --quiet lowcap-telegram.service" in script


def test_env_example_has_empty_telegram_placeholders():
    env = (DEPLOY / ".env.example").read_text(encoding="utf-8")
    assert "TELEGRAM_BOT_TOKEN=" in env
    assert "TELEGRAM_CHAT_ID=" in env
    # No token-shaped string may ship in the repository.
    assert not re.search(r"\d{8,10}:[0-9A-Za-z_-]{30,}", env)


def test_vps_guide_documents_the_telegram_step():
    guide = (DEPLOY / "VPS_SETUP.md").read_text(encoding="utf-8")
    for needle in (
        "## Step 9 — Telegram alerts",
        "@BotFather",
        "TELEGRAM_CHAT_ID",
        "--test",
        "lowcap-telegram.service",
        "Not authorized",
    ):
        assert needle in guide, needle


def test_telegram_reference_exists():
    reference = SKILL_ROOT / "references" / "telegram_bot.md"
    assert reference.is_file()
    text = reference.read_text(encoding="utf-8")
    assert "never from" in text and "environment" in text  # credential rule
    assert "/shadow" in text
