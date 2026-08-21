# -*- coding: utf-8 -*-
"""Tests for the credential-free Yahoo Finance news fallback."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from src.search_service import SearchService, YFinanceNewsProvider


def _news_item(*, title: str, summary: str = "Material company update") -> dict:
    return {
        "content": {
            "title": title,
            "summary": summary,
            "pubDate": datetime.now(timezone.utc).isoformat(),
            "provider": {"displayName": "Reuters"},
            "clickThroughUrl": {"url": "https://finance.yahoo.com/news/example"},
        }
    }


def test_yfinance_provider_parses_current_news_shape() -> None:
    with patch(
        "yfinance.Search",
        return_value=SimpleNamespace(news=[_news_item(title="MSTR reports new treasury update")]),
    ):
        response = YFinanceNewsProvider().search("MSTR latest news", max_results=3, days=3)

    assert response.success is True
    assert response.provider == "YahooFinance"
    assert len(response.results) == 1
    assert response.results[0].title == "MSTR reports new treasury update"
    assert response.results[0].source == "Reuters"
    assert response.results[0].published_date
    assert response.results[0].url == "https://finance.yahoo.com/news/example"


def test_search_service_uses_yfinance_without_api_keys() -> None:
    service = SearchService(yfinance_news_enabled=True, news_max_age_days=3)

    with patch(
        "yfinance.Search",
        return_value=SimpleNamespace(
            news=[
                _news_item(
                    title="Strategy MSTR announces financing update",
                    summary="Strategy disclosed a financing and Bitcoin treasury update.",
                )
            ]
        ),
    ):
        response = service.search_stock_news(
            stock_code="MSTR",
            stock_name="Strategy Inc",
            max_results=3,
        )

    assert service.is_available is True
    assert response.success is True
    assert response.results
    assert response.results[0].relevance_category == "direct_company_news"


def test_yfinance_fallback_can_be_disabled() -> None:
    service = SearchService(yfinance_news_enabled=False)

    assert service.is_available is False
    assert not any(isinstance(provider, YFinanceNewsProvider) for provider in service._providers)
