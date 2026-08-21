# -*- coding: utf-8 -*-
"""Tests for NEWS_STRATEGY_PROFILE parsing and effective window calculation."""

import unittest
from unittest.mock import patch

from src.config import Config, resolve_news_window_days


class NewsStrategyConfigTestCase(unittest.TestCase):
    def test_yfinance_news_fallback_defaults_on_and_is_configurable(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertTrue(Config._load_from_env().yfinance_news_enabled)
        with patch.dict("os.environ", {"YFINANCE_NEWS_ENABLED": "false"}, clear=True):
            self.assertFalse(Config._load_from_env().yfinance_news_enabled)

    def test_options_news_defaults_on_and_is_configurable(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertTrue(Config._load_from_env().options_news_enabled)
        with patch.dict("os.environ", {"OPTIONS_NEWS_ENABLED": "false"}, clear=True):
            self.assertFalse(Config._load_from_env().options_news_enabled)

    def test_invalid_profile_fallback_to_short(self) -> None:
        self.assertEqual(Config._parse_news_strategy_profile("bad_value"), "short")

    def test_window_respects_news_max_age_days(self) -> None:
        # medium=7 but max-age=3 -> effective=3
        self.assertEqual(resolve_news_window_days(3, "medium"), 3)
        # long=30 with max-age=30 -> effective=30
        self.assertEqual(resolve_news_window_days(30, "long"), 30)
        # ultra_short=1 with max-age=30 -> effective=1
        self.assertEqual(resolve_news_window_days(30, "ultra_short"), 1)


if __name__ == "__main__":
    unittest.main()
