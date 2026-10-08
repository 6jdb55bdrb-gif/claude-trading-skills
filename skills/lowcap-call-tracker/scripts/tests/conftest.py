"""Shared fixtures for lowcap-call-tracker tests."""

import os
import sys
from pathlib import Path

# Skill scripts directory first, then the tests directory (for helpers).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import pytest  # noqa: E402

from config import load_config, repo_root  # noqa: E402

FIXTURE_HITS = Path(__file__).resolve().parents[1] / "fixtures" / "dry_run_hits.json"


# The committed artefacts a cycle writes. A test that reaches these has
# escaped its temporary directory, and the damage is invisible: the file still
# looks like a valid report, just one generated from an empty test database.
COMMITTED_OUTPUTS = (
    repo_root() / "tracker-output" / "stats.md",
    repo_root() / "tracker-output" / "improvements.md",
    repo_root() / "tracker-output" / "state_snapshot.json",
)


@pytest.fixture(autouse=True)
def _never_write_the_committed_outputs():
    """Fail any test that writes the repository's own report files.

    Two tests have now done this — one through the `config` fixture's default
    paths, one by driving the CLI, which loads its own config. Both overwrote
    a real report with an empty-book one and were only noticed because git
    showed the file dirty. This turns that into a test failure, named after
    the file, at the moment it happens.
    """
    before = {path: path.read_bytes() if path.is_file() else None for path in COMMITTED_OUTPUTS}
    yield
    for path, original in before.items():
        current = path.read_bytes() if path.is_file() else None
        if current != original:
            if original is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(original)
            raise AssertionError(
                f"this test wrote {path.relative_to(repo_root())}, a committed file. "
                "Point tracker.stats_file / improvements_file / snapshot_file at "
                "tmp_path (see the `config` fixture, or _output_overlay for a test "
                "that drives main())."
            )


@pytest.fixture()
def config(tmp_path):
    """The packaged default configuration, writing into a temporary directory.

    The real paths resolve against the repository root, so a test that runs a
    full cycle would otherwise overwrite the committed ``tracker-output/``
    files — the suite would dirty the working tree and a hook would then
    "fix" a generated artefact. A test that wants the real path sets it back
    explicitly.
    """
    loaded = load_config()
    # The suite pins the generation it describes. Most tests here run the
    # three-hit fixture, which includes an etf_momentum row that only v1
    # screens, so riding on the live default would mean flipping
    # screener_version silently rewrote 29 tests. A v2 test opts in
    # explicitly, and test_the_shipped_default_version pins what ships.
    loaded["screener"]["screener_version"] = "v1"
    output = tmp_path / "tracker-output"
    output.mkdir(exist_ok=True)
    loaded["tracker"]["stats_file"] = str(output / "stats.md")
    loaded["tracker"]["improvements_file"] = str(output / "improvements.md")
    loaded["tracker"]["reports_dir"] = str(tmp_path / "reports")
    return loaded


@pytest.fixture()
def tmp_db(tmp_path):
    """A fresh call database in a temporary directory."""
    from call_db import CallDatabase

    with CallDatabase(tmp_path / "calls.db") as db:
        yield db


@pytest.fixture()
def stock_hit():
    return {
        "ticker": "SQZX",
        "company": "Squeezex Therapeutics Inc.",
        "asset_type": "stock",
        "variant": "squeeze",
        "sector": "Healthcare",
        "price": 3.80,
        "change_pct": 22.4,
        "volume": 14_500_000,
        "avg_volume": 3_100_000,
        "rel_volume": 5.2,
        "float_shares": 6_500_000,
        "short_float_pct": 28.4,
        "sma20_pct": 18.0,
        "sma50_pct": 26.0,
        "sma200_pct": 44.0,
        "high52w_pct": -3.0,
        "rsi": 74.0,
        "atr": 0.42,
        "catalyst_headline": "FDA approval for SQX-101",
    }


@pytest.fixture()
def etf_hit():
    return {
        "ticker": "URAX",
        "company": "Northshore Junior Uranium Miners ETF",
        "asset_type": "etf",
        "variant": "etf_momentum",
        "theme": "uranium",
        "price": 18.40,
        "change_pct": 4.2,
        "volume": 2_600_000,
        "avg_volume": 1_200_000,
        "rel_volume": 2.6,
        "sma20_pct": 6.5,
        "sma50_pct": 11.0,
        "high52w_pct": -0.5,
        "rsi": 68.0,
        "atr": 0.55,
    }


def review_payload(
    ticker="AAA",
    *,
    decision="TAKE",
    confidence=70,
    entry=10.0,
    direction="long",
    variant="squeeze",
    asset_type="stock",
    scores=(7.0, 6.0, 3.0, 6.0),
):
    """Minimal review dict accepted by CallDatabase.insert_call."""
    return {
        "ticker": ticker,
        "asset_type": asset_type,
        "variant": variant,
        "decision": decision,
        "confidence": confidence,
        "entry": entry,
        "price": entry,
        "backend": "heuristic",
        "notes": [],
        "verdicts": {
            "researcher": {"role": "researcher", "score": scores[0]},
            "technician": {"role": "technician", "score": scores[1]},
            "skeptic": {"role": "skeptic", "score": scores[2]},
            "risk_manager": {
                "role": "risk_manager",
                "score": scores[3],
                "direction": direction,
                "stop": round(entry * 0.9, 2),
                "target": round(entry * 1.2, 2),
                "shares": 100,
                "position_usd": entry * 100,
                "risk_usd": 100.0,
            },
            "judge": {"role": "judge", "decision": decision, "reason": "test"},
        },
    }


class FakeServerToolUse:
    def __init__(self, web_search_requests=0):
        self.web_search_requests = web_search_requests


class FakeUsage:
    def __init__(self, input_tokens=500, output_tokens=200, web_search_requests=0):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cache_read_input_tokens = 0
        self.server_tool_use = (
            FakeServerToolUse(web_search_requests) if web_search_requests else None
        )


class FakeBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class FakeResponse:
    stop_reason = "end_turn"

    def __init__(self, text, web_search_requests=0):
        self.content = [FakeBlock(text)]
        self.usage = FakeUsage(web_search_requests=web_search_requests)


class FakeMessages:
    def __init__(self, replies, web_search_requests=0):
        self._replies = replies
        self.calls = []
        self._web_search_requests = web_search_requests

    def create(self, **kwargs):
        self.calls.append(kwargs)
        reply = self._replies.pop(0) if self._replies else "{}"
        return FakeResponse(reply, web_search_requests=self._web_search_requests)


class FakeAnthropic:
    """Stand-in for anthropic.Anthropic with scripted JSON replies."""

    def __init__(self, replies, web_search_requests=0):
        self.messages = FakeMessages(list(replies), web_search_requests)

    @property
    def calls(self):
        """Every kwargs dict passed to messages.create, in order."""
        return self.messages.calls


@pytest.fixture()
def review_fn():
    """``review_payload`` as a fixture, for tests that build several calls."""
    return review_payload
