#!/usr/bin/env python3
"""Credential-free production news smoke test for configured watchlist symbols."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_config  # noqa: E402
from src.data.stock_mapping import STOCK_NAME_MAP  # noqa: E402
from src.search_service import SearchService  # noqa: E402
from src.services.stock_list_parser import split_stock_list  # noqa: E402


def _build_search_service(config: object) -> SearchService:
    return SearchService(
        bocha_keys=getattr(config, "bocha_api_keys", None),
        tavily_keys=getattr(config, "tavily_api_keys", None),
        anspire_keys=getattr(config, "anspire_api_keys", None),
        brave_keys=getattr(config, "brave_api_keys", None),
        serpapi_keys=getattr(config, "serpapi_keys", None),
        minimax_keys=getattr(config, "minimax_api_keys", None),
        searxng_base_urls=getattr(config, "searxng_base_urls", None),
        searxng_public_instances_enabled=getattr(
            config,
            "searxng_public_instances_enabled",
            False,
        ),
        yfinance_news_enabled=getattr(config, "yfinance_news_enabled", True),
        news_max_age_days=getattr(config, "news_max_age_days", 3),
        news_strategy_profile=getattr(config, "news_strategy_profile", "short"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stocks",
        default=os.getenv("STOCK_LIST", ""),
        help="Comma/space/newline separated symbols; defaults to STOCK_LIST.",
    )
    parser.add_argument("--max-results", type=int, default=3)
    args = parser.parse_args()

    symbols = [symbol.upper() for symbol in split_stock_list(args.stocks)]
    if not symbols:
        print("NEWS_CHECK_ERROR: no symbols configured", file=sys.stderr)
        return 2

    service = _build_search_service(get_config())
    if not service.is_available:
        print("NEWS_CHECK_ERROR: no news provider is available", file=sys.stderr)
        return 2

    failures = []
    for symbol in symbols:
        name = STOCK_NAME_MAP.get(symbol, symbol)
        response = service.search_stock_news(
            stock_code=symbol,
            stock_name=name,
            max_results=max(1, args.max_results),
        )
        titles = [item.title for item in (response.results or [])]
        record = {
            "symbol": symbol,
            "name": name,
            "provider": response.provider,
            "success": bool(response.success and titles),
            "count": len(titles),
            "titles": titles,
            "error": response.error_message,
        }
        print(json.dumps(record, ensure_ascii=False))
        if not record["success"]:
            failures.append(symbol)

    if failures:
        print(
            f"NEWS_CHECK_ERROR: no usable recent headlines for {','.join(failures)}",
            file=sys.stderr,
        )
        return 1
    print(f"NEWS_CHECK_OK: usable recent headlines found for {len(symbols)} symbols")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
