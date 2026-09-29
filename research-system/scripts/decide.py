#!/usr/bin/env python3
"""STRATEGIST decision rule: TRADING vs INVESTING from the RESEARCHER's scores.

Reads data/phase1_scores.json and scores each path's tool stack:

1. Weighted mean of each core tool's score for that path (main engine weighted higher).
2. Penalty of 1.0 point per engine in the Phase-4 validation chain
   (primary -> cross-check -> high-fidelity) that cannot trade the path's asset class,
   because results that cannot be cross-checked are less reliable.

The higher net score wins; a margin below MARGIN is reported as BOTH (no clear winner).
Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MARGIN = 0.5
COVERAGE_PENALTY = 1.0
DEFAULT_DATA = Path(__file__).resolve().parents[1] / "data" / "phase1_scores.json"


def stack_score(tools: dict, path: dict, path_name: str) -> float:
    total = weight_sum = 0.0
    for name, weight in path["core"].items():
        if name not in tools:
            raise KeyError(f"core tool '{name}' has no Phase 1 score")
        total += tools[name]["scores"][path_name] * weight
        weight_sum += weight
    return round(total / weight_sum, 2) if weight_sum else 0.0


def validation_coverage(tools: dict, path: dict) -> tuple[int, int]:
    chain = path["validation_chain"]
    covered = sum(1 for name in chain if path["asset_class"] in tools[name]["asset_classes"])
    return covered, len(chain)


def decide(data: dict) -> dict:
    tools, results = data["tools"], {}
    for name, path in data["paths"].items():
        raw = stack_score(tools, path, name)
        covered, total = validation_coverage(tools, path)
        penalty = COVERAGE_PENALTY * (total - covered)
        results[name] = {
            "stack_score": raw,
            "coverage": [covered, total],
            "penalty": penalty,
            "net_score": round(raw - penalty, 2),
            "min_annual_data_cost_usd": path.get("min_annual_data_cost_usd"),
        }
    trading = results["trading"]["net_score"]
    investing = results["investing"]["net_score"]
    if abs(trading - investing) < MARGIN:
        decision = "BOTH"
    else:
        decision = "TRADING" if trading > investing else "INVESTING"
    return {"decision": decision, "margin": round(abs(trading - investing), 2), "paths": results}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.data.read_text())
        result = decide(data)
    except (OSError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("[STRATEGIST] decision from Phase 1 scores")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
