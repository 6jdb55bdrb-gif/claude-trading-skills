import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import decide  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data" / "phase1_scores.json"


def _tool(trading, investing, assets):
    return {"scores": {"trading": trading, "investing": investing}, "asset_classes": assets}


def _data(tools, paths):
    return {"tools": tools, "paths": paths}


def test_weighted_stack_score():
    tools = {"a": _tool(9, 1, ["crypto"]), "b": _tool(6, 1, ["crypto"])}
    path = {"core": {"a": 2, "b": 1}, "validation_chain": [], "asset_class": "crypto"}
    assert decide.stack_score(tools, path, "trading") == 8.0


def test_validation_coverage_counts_engines_supporting_asset_class():
    tools = {"x": _tool(5, 5, ["crypto"]), "y": _tool(5, 5, ["equities", "crypto"])}
    path = {"core": {}, "validation_chain": ["x", "y"], "asset_class": "equities"}
    assert decide.validation_coverage(tools, path) == (1, 2)


def test_missing_engine_coverage_is_penalised():
    tools = {
        "e1": _tool(7, 7, ["crypto", "equities"]),
        "e2": _tool(7, 7, ["crypto"]),
    }
    paths = {
        "trading": {
            "core": {"e1": 1, "e2": 1},
            "validation_chain": ["e1", "e2"],
            "asset_class": "crypto",
        },
        "investing": {
            "core": {"e1": 1, "e2": 1},
            "validation_chain": ["e1", "e2"],
            "asset_class": "equities",
        },
    }
    result = decide.decide(_data(tools, paths))
    assert result["paths"]["investing"]["penalty"] > 0
    assert result["decision"] == "TRADING"


def test_close_scores_return_both():
    tools = {"e": _tool(7.0, 6.8, ["crypto", "equities"])}
    paths = {
        "trading": {"core": {"e": 1}, "validation_chain": ["e"], "asset_class": "crypto"},
        "investing": {"core": {"e": 1}, "validation_chain": ["e"], "asset_class": "equities"},
    }
    assert decide.decide(_data(tools, paths))["decision"] == "BOTH"


def test_unknown_tool_in_path_raises():
    paths = {"trading": {"core": {"ghost": 1}, "validation_chain": [], "asset_class": "crypto"}}
    try:
        decide.stack_score({}, paths["trading"], "trading")
    except KeyError as exc:
        assert "ghost" in str(exc)
    else:
        raise AssertionError("expected KeyError")


def test_committed_phase1_data_decides_trading():
    result = decide.decide(json.loads(DATA.read_text()))
    assert result["decision"] == "TRADING"
    assert result["paths"]["trading"]["coverage"] == [3, 3]
