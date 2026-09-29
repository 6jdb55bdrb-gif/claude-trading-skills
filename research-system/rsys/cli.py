"""Command line entry point: python -m rsys.cli <command>.

universe          live CMC listings -> filtered, exchange-mapped universe JSON
download          ccxt OHLCV for the universe (+ BTC/ETH) -> canonical CSV + validation report
export-freqtrade  canonical CSV -> freqtrade json datadir
freqtrade-config  write paper-only freqtrade configs from settings + universe
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import ohlcv, universe
from .config import DATA_DIR, ROOT, load_settings

UNIVERSE_DIR = DATA_DIR / "universe"
CANONICAL_DIR = DATA_DIR / "ohlcv"
FREQTRADE_DIR = ROOT / "freqtrade" / "user_data"


def _label(role: str, msg: str) -> None:
    print(f"[{role}] {msg}")


def _utc_ms(day: str | None) -> int | None:
    if not day:
        return None
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def _universe_pairs(path: Path, settings: dict) -> list[str]:
    quote = settings["data"]["quote"]
    majors = [f"{s}/{quote}" for s in settings["universe"]["always_include"]]
    if not path.exists():
        _label("DATA ENGINEER", f"no universe file at {path}; using {majors} only")
        return majors
    pairs = [a["pair"] for a in json.loads(path.read_text())["assets"]]
    return list(dict.fromkeys(majors + pairs))


def cmd_universe(args, settings) -> int:
    if args.listings_json:
        payload = json.loads(Path(args.listings_json).read_text())
        listings = payload.get("data", payload)
        _label("DATA ENGINEER", f"using saved CMC listings from {args.listings_json}")
    else:
        try:
            listings = universe.fetch_listings(api_key=None, limit=100)
        except universe.MissingApiKey as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        _label("DATA ENGINEER", f"fetched {len(listings)} live listings from CoinMarketCap")
    exchange = ohlcv.make_exchange(settings["data"]["exchange"])
    start_ms = _utc_ms(settings["data"]["start"])
    result = universe.build_universe(
        listings,
        settings,
        markets=exchange.markets,
        first_candle_ms=lambda pair: ohlcv.first_candle_ms(exchange, pair, start_ms),
    )
    UNIVERSE_DIR.mkdir(parents=True, exist_ok=True)
    dated = UNIVERSE_DIR / f"universe_{result['as_of'][:10]}.json"
    for path in (dated, UNIVERSE_DIR / "latest.json"):
        path.write_text(json.dumps(result, indent=2) + "\n")
    _label(
        "DATA ENGINEER",
        f"{len(result['assets'])} pairs kept, {len(result['rejected'])} rejected -> {dated}",
    )
    for asset in result["assets"]:
        flag = " (survivorship-biased)" if asset["survivorship_biased"] else ""
        print(
            f"  #{asset['cmc_rank']:>3} {asset['pair']:<12} vol24h ${asset['volume_24h_usd']:,.0f}{flag}"
        )
    return 0


def cmd_download(args, settings) -> int:
    data = settings["data"]
    pairs = args.pairs or _universe_pairs(UNIVERSE_DIR / "latest.json", settings)
    timeframes = args.timeframes or data["timeframes"]
    exchange = ohlcv.make_exchange(data["exchange"])
    start_ms, end_ms = _utc_ms(data["start"]), _utc_ms(data.get("end"))
    reports, failed = {}, []
    for pair in pairs:
        for tf in timeframes:
            df = ohlcv.download(exchange, pair, tf, start_ms, end_ms)
            if df.empty:
                failed.append(f"{pair} {tf}: no data")
                continue
            path = ohlcv.save_csv(df, CANONICAL_DIR, data["exchange"], pair, tf)
            report = ohlcv.validate(df, tf)
            reports[f"{pair} {tf}"] = report
            status = "ok" if report["ok"] else "CHECK"
            _label(
                "DATA ENGINEER",
                f"{pair:<11} {tf:<3} {report['rows']:>6} rows {report['start'][:10]}..{report['end'][:10]} "
                f"gaps={report['gaps']} missing={report['missing_candles']} [{status}] -> {path.name}",
            )
            if not report["ok"]:
                failed.append(f"{pair} {tf}: validation")
    report_path = CANONICAL_DIR / data["exchange"] / "validation_report.json"
    report_path.write_text(json.dumps(reports, indent=2) + "\n")
    if failed:
        print("problems: " + "; ".join(failed), file=sys.stderr)
    return 1 if failed else 0


def cmd_export_freqtrade(args, settings) -> int:
    exchange = settings["data"]["exchange"]
    src = CANONICAL_DIR / exchange
    dst = FREQTRADE_DIR / "data" / exchange
    count = 0
    for csv in sorted(src.glob("*.csv")):
        pair_part, tf = csv.stem.rsplit("-", 1)
        ohlcv.export_freqtrade(ohlcv.load_csv(csv), dst, pair_part.replace("_", "/"), tf)
        count += 1
    _label("DATA ENGINEER", f"exported {count} files to {dst}")
    return 0 if count else 1


def cmd_freqtrade_config(args, settings) -> int:
    from . import freqtrade_config

    pairs = _universe_pairs(UNIVERSE_DIR / "latest.json", settings)
    written = freqtrade_config.write_all(settings, pairs, FREQTRADE_DIR)
    for path in written:
        _label("DEVELOPER", f"wrote {path.relative_to(ROOT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rsys", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("universe")
    p.add_argument("--listings-json", help="offline: saved CMC listings/latest response")
    p = sub.add_parser("download")
    p.add_argument("--pairs", nargs="*")
    p.add_argument("--timeframes", nargs="*")
    sub.add_parser("export-freqtrade")
    sub.add_parser("freqtrade-config")
    args = parser.parse_args(argv)
    settings = load_settings()
    handler = {
        "universe": cmd_universe,
        "download": cmd_download,
        "export-freqtrade": cmd_export_freqtrade,
        "freqtrade-config": cmd_freqtrade_config,
    }[args.command]
    return handler(args, settings)


if __name__ == "__main__":
    sys.exit(main())
