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


def test_yfinance_uses_compact_security_identity_queries() -> None:
    calls = []

    def fake_search(query: str, news_count: int) -> SimpleNamespace:
        calls.append((query, news_count))
        if query == "MSTR":
            return SimpleNamespace(
                news=[_news_item(title="MSTR announces treasury update")]
            )
        return SimpleNamespace(news=[])

    service = SearchService(yfinance_news_enabled=True, news_max_age_days=3)
    with patch("yfinance.Search", side_effect=fake_search):
        response = service.search_stock_news(
            stock_code="MSTR",
            stock_name="MicroStrategy",
            max_results=3,
        )

    assert calls[0][0] == "MSTR"
    assert "Strategy Inc." in [query for query, _count in calls]
    assert response.results[0].title == "MSTR announces treasury update"


def test_yfinance_rejects_generic_zero_relevance_feed() -> None:
    generic = _news_item(title="Unrelated company reports quarterly earnings")
    service = SearchService(yfinance_news_enabled=True, news_max_age_days=3)

    with patch(
        "yfinance.Search",
        return_value=SimpleNamespace(news=[generic]),
    ):
        response = service.search_stock_news(
            stock_code="SPCX",
            stock_name="Space Exploration Technologies Corporation",
            max_results=3,
        )

    assert response.success is True
    assert response.provider == "Filtered"
    assert response.results == []


def test_yfinance_does_not_treat_lowercase_spy_as_spy_etf_news() -> None:
    generic = _news_item(title="Former U.S. spy faces deportation hearing")
    service = SearchService(yfinance_news_enabled=True, news_max_age_days=3)

    with patch("yfinance.Ticker") as ticker, patch(
        "yfinance.Search", return_value=SimpleNamespace(news=[generic])
    ):
        ticker.return_value.get_news.return_value = []
        response = service.search_stock_news(
            stock_code="SPY",
            stock_name="SPDR S&P 500 ETF Trust",
            max_results=3,
        )

    assert response.provider == "Filtered"
    assert response.results == []


def test_yfinance_uses_ticker_scoped_feed_for_etf_context() -> None:
    market_item = _news_item(title="Technology shares lead the market higher")
    service = SearchService(yfinance_news_enabled=True, news_max_age_days=3)

    with patch("yfinance.Ticker") as ticker, patch(
        "yfinance.Search", return_value=SimpleNamespace(news=[])
    ):
        ticker.return_value.get_news.return_value = [market_item]
        response = service.search_stock_news(
            stock_code="QQQ",
            stock_name="Invesco QQQ Trust",
            max_results=3,
        )

    ticker.assert_called_once_with("QQQ")
    assert response.provider == "YahooFinance"
    assert response.results[0].provider_symbol == "QQQ"
    assert response.results[0].relevance_score > 0


def test_tqqq_is_recognized_as_etf_without_fund_keyword() -> None:
    assert SearchService.is_index_or_etf("TQQQ", "ProShares UltraPro QQQ")


def test_tqqq_uses_qqq_underlying_news_feed() -> None:
    market_item = _news_item(title="Technology shares lead the market higher")
    service = SearchService(yfinance_news_enabled=True, news_max_age_days=3)

    with patch("yfinance.Ticker") as ticker, patch(
        "yfinance.Search", return_value=SimpleNamespace(news=[])
    ):
        ticker.return_value.get_news.return_value = [market_item]
        response = service.search_stock_news(
            stock_code="TQQQ",
            stock_name="ProShares UltraPro QQQ",
            max_results=3,
        )

    ticker.assert_called_once_with("QQQ")
    assert response.provider == "YahooFinance"
    assert response.results[0].provider_symbol == "TQQQ"


def test_yfinance_identity_queries_feed_comprehensive_intelligence() -> None:
    service = SearchService(yfinance_news_enabled=True, news_max_age_days=3)

    def fake_search(query: str, news_count: int) -> SimpleNamespace:
        if query == "APLD":
            return SimpleNamespace(
                news=[_news_item(title="APLD wins new AI infrastructure contract")]
            )
        return SimpleNamespace(news=[])

    with patch("yfinance.Search", side_effect=fake_search):
        results = service.search_comprehensive_intel(
            stock_code="APLD",
            stock_name="Applied Digital Corporation",
            max_searches=1,
        )

    assert results["latest_news"].results
    assert results["latest_news"].results[0].title.startswith("APLD wins")


def test_options_news_dimension_is_enabled_for_us_symbols() -> None:
    service = SearchService(
        yfinance_news_enabled=True,
        options_news_enabled=True,
        news_max_age_days=3,
    )

    with patch("yfinance.Search", return_value=SimpleNamespace(news=[])) as search:
        results = service.search_comprehensive_intel(
            stock_code="MSTR",
            stock_name="MicroStrategy",
            max_searches=2,
        )

    assert "options_flow" in results
    assert any("implied volatility" in call.args[0] for call in search.call_args_list)


def test_options_news_dimension_can_be_disabled() -> None:
    service = SearchService(
        yfinance_news_enabled=True,
        options_news_enabled=False,
        news_max_age_days=3,
    )

    with patch("yfinance.Search", return_value=SimpleNamespace(news=[])):
        results = service.search_comprehensive_intel(
            stock_code="MSTR",
            stock_name="MicroStrategy",
            max_searches=2,
        )

    assert "options_flow" not in results


def test_yfinance_fallback_can_be_disabled() -> None:
    service = SearchService(yfinance_news_enabled=False)

    assert service.is_available is False
    assert not any(isinstance(provider, YFinanceNewsProvider) for provider in service._providers)
