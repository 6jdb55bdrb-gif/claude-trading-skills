#!/usr/bin/env python3
"""Variant definitions and FinViz URL construction for the lowcap screeners.

URL building is delegated to the ``finviz-screener`` skill
(``open_finviz_screener.build_url``) so both skills emit byte-identical URLs and
the view-code table has a single owner. Only the multi-exchange token
(``exch_amex|nasd|nyse``) is built here, because the sibling skill's CLI
validator rejects ``|`` in ``--filters``.

CLI:
    python3 screener_variants.py --list
    python3 screener_variants.py --variant squeeze --urls
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

from config import load_config, repo_root

_TOKEN_RE = re.compile(r"^[a-z0-9_.|\-]+$")

# Import the sibling skill's URL builder rather than re-deriving view codes.
_FINVIZ_SCRIPTS = repo_root() / "skills" / "finviz-screener" / "scripts"
if str(_FINVIZ_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_FINVIZ_SCRIPTS))

try:
    from open_finviz_screener import VIEW_CODES, build_url  # noqa: E402

    HAS_FINVIZ_SKILL = True
except ImportError:  # pragma: no cover - standalone packaging fallback
    HAS_FINVIZ_SKILL = False
    VIEW_CODES = {
        "overview": "111",
        "valuation": "121",
        "ownership": "131",
        "performance": "141",
        "custom": "152",
        "financial": "161",
        "technical": "171",
    }

    def build_url(
        filters: list[str],
        *,
        elite: bool = False,
        view: str = "overview",
        order: str | None = None,
        themes: list[str] | None = None,
        subthemes: list[str] | None = None,
    ) -> str:
        host = "elite.finviz.com" if elite else "finviz.com"
        code = VIEW_CODES.get(view, VIEW_CODES["overview"])
        url = f"https://{host}/screener.ashx?v={code}&f={','.join(filters)}"
        if order:
            url += f"&o={order}"
        return url


class VariantError(ValueError):
    """Raised for an unknown variant or an unsafe filter token."""


def validate_token(token: str) -> str:
    """Validate one FinViz filter token, allowing ``|`` multi-select groups."""
    token = token.strip()
    if not token or not _TOKEN_RE.match(token):
        raise VariantError(
            f"invalid filter token {token!r}: only lowercase letters, digits, "
            "'_', '.', '-' and '|' are allowed"
        )
    return token


def elite_mode(config: dict[str, Any]) -> bool:
    """True when the Elite host/export path should be used."""
    mode = str(config["screener"].get("mode", "auto")).lower()
    if mode == "elite":
        return True
    if mode in {"public", "fixture"}:
        return False
    return bool(os.environ.get("FINVIZ_API_KEY"))


def exchange_mode(config: dict[str, Any]) -> str:
    mode = str(config["screener"].get("exchange_mode", "auto")).lower()
    if mode != "auto":
        return mode
    return "explicit" if elite_mode(config) else "universe"


def exchange_filter_sets(config: dict[str, Any]) -> list[list[str]]:
    """Return the per-pass exchange filter tokens implementing OTC exclusion.

    ``universe`` yields one pass with no exchange token: FinViz's screener
    universe only covers listed venues (AMEX / NASDAQ / NYSE / CBOE), so OTC and
    pink-sheet tickers are already absent, and ``fetch_screener`` additionally
    drops any row whose reported exchange is outside ``allowed_exchanges``.
    """
    exchanges = [str(code).lower() for code in config["screener"].get("exchanges") or []]
    mode = exchange_mode(config)
    if mode == "explicit" and exchanges:
        return [[f"exch_{'|'.join(exchanges)}"]]
    if mode == "per_exchange" and exchanges:
        return [[f"exch_{code}"] for code in exchanges]
    return [[]]


DEFAULT_VERSION = "v1"


def screener_version(config: dict[str, Any]) -> str:
    """Which screener generation is active, e.g. "v1" or "v2"."""
    return str(config["screener"].get("screener_version", DEFAULT_VERSION)).strip().lower()


def version_block(config: dict[str, Any], version: str | None = None) -> dict[str, Any]:
    """The whole config block for one screener version.

    Versions live side by side so a historical call stays explainable: v1's
    filters are preserved exactly, and every call records the version that
    produced it. A pre-versions config (plain ``screener.variants``) still
    loads, and reads as v1.
    """
    name = (version or screener_version(config)).strip().lower()
    versions = config["screener"].get("versions")
    if not versions:
        if name not in {DEFAULT_VERSION, ""}:
            raise VariantError(
                f"screener_version {name!r} requested but this config has no "
                "screener.versions block"
            )
        return {"variants": config["screener"]["variants"]}
    if name not in versions:
        raise VariantError(
            f"unknown screener_version {name!r}; available: {', '.join(sorted(versions))}"
        )
    return versions[name]


def version_variants(config: dict[str, Any], version: str | None = None) -> dict[str, Any]:
    return version_block(config, version)["variants"]


def version_guards(config: dict[str, Any], version: str | None = None) -> dict[str, Any]:
    """Post-screen guards for this version — a FinViz filter can only narrow."""
    return version_block(config, version).get("guards") or {}


def find_variant_spec(config: dict[str, Any], name: str) -> dict[str, Any]:
    """The spec for *name* from any version, active one first, or ``{}``.

    A historical call carries the variant that produced it, and that variant may
    have been retired from the active generation (``etf_momentum`` lives in v1
    only). Reporting on such a call must still be able to quote its filters, so
    this searches every version instead of failing.
    """
    names = [screener_version(config)]
    names += [other for other in (config["screener"].get("versions") or {}) if other not in names]
    for version in names:
        try:
            variants = version_variants(config, version)
        except (VariantError, KeyError):
            continue
        if name in variants:
            return variants[name]
    return {}


def get_variant(config: dict[str, Any], name: str) -> dict[str, Any]:
    variants = version_variants(config)
    if name not in variants:
        raise VariantError(f"unknown variant {name!r}; available: {', '.join(sorted(variants))}")
    return variants[name]


def variant_names(config: dict[str, Any]) -> list[str]:
    return list(version_variants(config))


def variant_filters(config: dict[str, Any], name: str) -> list[str]:
    """Return the validated base filter list for *name* (no exchange token)."""
    variant = get_variant(config, name)
    filters = [validate_token(token) for token in variant["filters"]]
    optional = variant.get("optional_filters") or {}
    for key in variant.get("enable_optional") or []:
        token = optional.get(key)
        if not token:
            raise VariantError(f"variant {name!r}: enable_optional references unknown key {key!r}")
        token = validate_token(token)
        if token not in filters:
            filters.append(token)
    return filters


def variant_views(config: dict[str, Any], name: str) -> list[str]:
    variant = get_variant(config, name)
    views = variant.get("views") or ["overview"]
    unknown = [view for view in views if view not in VIEW_CODES]
    if unknown:
        raise VariantError(f"variant {name!r} references unknown view(s): {', '.join(unknown)}")
    return list(views)


def build_variant_urls(config: dict[str, Any], name: str) -> list[dict[str, Any]]:
    """Return one entry per (view, exchange-pass) request for *name*."""
    variant = get_variant(config, name)
    base = variant_filters(config, name)
    elite = elite_mode(config)
    requests_out: list[dict[str, Any]] = []
    for view in variant_views(config, name):
        for exchange_tokens in exchange_filter_sets(config):
            filters = base + [validate_token(token) for token in exchange_tokens]
            requests_out.append(
                {
                    "variant": name,
                    "asset_type": variant["asset_type"],
                    "view": view,
                    "view_code": VIEW_CODES[view],
                    "filters": filters,
                    "url": build_url(
                        filters,
                        elite=elite,
                        view=view,
                        order=variant.get("order"),
                    ),
                }
            )
    return requests_out


def describe_variants(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Human-readable summary used by the SKILL workflow and the run report."""
    out = []
    for name in variant_names(config):
        variant = get_variant(config, name)
        out.append(
            {
                "variant": name,
                "label": variant.get("label", name),
                "asset_type": variant["asset_type"],
                "filters": variant_filters(config, name),
                "views": variant_views(config, name),
                "exchange_mode": exchange_mode(config),
                "exchange_passes": exchange_filter_sets(config),
                "urls": [entry["url"] for entry in build_variant_urls(config, name)],
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect lowcap screener variants")
    parser.add_argument("--config", help="YAML overrides merged over the packaged default")
    parser.add_argument("--variant", help="Restrict output to one variant")
    parser.add_argument("--list", action="store_true", help="List variant names and filter codes")
    parser.add_argument("--urls", action="store_true", help="Print the FinViz URLs")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    described = describe_variants(config)
    if args.variant:
        described = [entry for entry in described if entry["variant"] == args.variant]
        if not described:
            print(f"ERROR: unknown variant {args.variant!r}", file=sys.stderr)
            return 1

    if args.json:
        print(json.dumps(described, indent=2))
        return 0

    for entry in described:
        print(f"[{entry['variant']}] {entry['label']}  ({entry['asset_type']})")
        print(f"  filters: {','.join(entry['filters'])}")
        print(f"  views:   {', '.join(entry['views'])}  exchange_mode: {entry['exchange_mode']}")
        if args.list or args.urls:
            for url in entry["urls"]:
                print(f"  url: {url}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
