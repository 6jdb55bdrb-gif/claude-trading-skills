"""Tests for walk-forward selection logic."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from walk_forward import walk_forward  # noqa: E402


def test_picks_best_on_prior_years_only():
    yearly = {
        "a": {"2022": 10, "2023": 10, "2024": -50, "2025": 0},
        "b": {"2022": 0, "2023": 5, "2024": 30, "2025": 40},
    }
    res = walk_forward(yearly, test_years=["2024", "2025"])
    # 2024: train 2022-23 -> a (20 vs 5) -> scores -50.
    assert res[0] == {"test_year": "2024", "chosen": "a", "train_pnl": 20, "test_pnl": -50}
    # 2025: train 2022-24 -> b (35 vs -30) -> scores 40.
    assert res[1]["chosen"] == "b" and res[1]["test_pnl"] == 40


def test_missing_years_count_as_zero():
    res = walk_forward({"a": {"2023": 5}, "b": {"2022": 1, "2024": 7}}, test_years=["2024"])
    assert res[0]["chosen"] == "a" and res[0]["test_pnl"] == 0
