"""Pure-logic unit tests (no network, no API keys needed)."""
from launchlens import config
from launchlens.state import reset_or_extend
from launchlens.tools import _asin_from, _trend_direction


def test_reset_or_extend():
    assert reset_or_extend(["a"], ["b"]) == ["a", "b"]   # merge (fan-out)
    assert reset_or_extend(["a", "b"], "RESET") == []      # reset between turns
    assert reset_or_extend(None, ["x"]) == ["x"]


def test_trend_direction():
    assert _trend_direction([50, 60, 80])[0] == "rising"
    assert _trend_direction([90, 70, 50])[0] == "declining"
    assert _trend_direction([50, 51, 49])[0] == "flat"
    assert _trend_direction([])[0] == "unknown"


def test_asin_from():
    assert _asin_from("B07G11R5LC") == "B07G11R5LC"
    assert _asin_from("https://www.amazon.in/dp/B07G11R5LC?ref=x") == "B07G11R5LC"
    assert _asin_from("/gp/product/B0ABCDE123") == "B0ABCDE123"


def test_market_fallback():
    assert config.market("com")["geo"] == "US"
    assert config.market("nonsense")["geo"] == config.market()["geo"]  # falls back to default


def test_cache_roundtrip():
    from launchlens import cache
    cache.set("test:viva:key", {"hello": "world"})
    assert cache.get("test:viva:key") == {"hello": "world"}
    assert cache.get("test:viva:missing") is None
