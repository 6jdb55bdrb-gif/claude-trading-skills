"""A missing backend reason must not render as the word "None".

`.get('reason', 'unknown reason')` only defaults when the key is ABSENT. The
health dict always carries `reason`, so a None value sailed straight through and
stats.md read "The role review could not run: None." for several commits —
the same "None%" class of defect already fixed in the numeric renderers.
"""

from stats import compute_stats, format_backend_line, render_markdown


def _md(tmp_db, config, health):
    return render_markdown(compute_stats(tmp_db, config, backend_health=health))


def test_a_present_reason_is_printed(tmp_db, config):
    md = _md(tmp_db, config, {"ok": False, "reason": "the 'anthropic' package is not installed"})
    assert "could not run: the 'anthropic' package is not installed." in md


def test_a_none_reason_never_prints_the_word_none(tmp_db, config):
    md = _md(tmp_db, config, {"ok": False, "reason": None})
    assert "BACKEND DOWN" in md
    assert "run: None" not in md
    assert "no reason recorded" in md


def test_a_missing_reason_key_never_prints_the_word_none(tmp_db, config):
    md = _md(tmp_db, config, {"ok": False})
    assert "run: None" not in md
    assert "no reason recorded" in md


def test_an_empty_reason_is_treated_as_missing(tmp_db, config):
    md = _md(tmp_db, config, {"ok": False, "reason": "   "})
    assert "run: None" not in md
    assert "no reason recorded" in md


def test_a_healthy_backend_prints_no_down_banner(tmp_db, config):
    md = _md(tmp_db, config, {"ok": True, "model": "claude-haiku-4-5", "latency_ms": 120})
    assert "BACKEND DOWN" not in md


def test_the_one_line_summary_never_prints_none_either(tmp_db, config):
    stats = compute_stats(tmp_db, config, backend_health={"ok": False, "reason": None})
    assert "None" not in format_backend_line(stats["backend"])
