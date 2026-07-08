from stock_ts.providers.eltdx_provider import EltdxProvider
from stock_ts.providers.factory import create_provider
from stock_ts.providers.tencent_provider import TencentProvider


def test_create_provider_auto_uses_tencent_by_default_even_when_eltdx_is_available(
    monkeypatch,
) -> None:
    from stock_ts.providers import factory

    monkeypatch.setattr(factory, "is_eltdx_bridge_available", lambda: True)
    monkeypatch.delenv("STOCK_TS_AUTO_PREFER_ELTDX", raising=False)

    provider = create_provider("auto")

    assert isinstance(provider, TencentProvider)
    assert provider.request_timeout == 1.5


def test_create_provider_auto_can_opt_into_eltdx(monkeypatch) -> None:
    from stock_ts.providers import factory

    monkeypatch.setattr(factory, "is_eltdx_bridge_available", lambda: True)
    monkeypatch.setenv("STOCK_TS_AUTO_PREFER_ELTDX", "1")

    provider = create_provider("auto")

    assert isinstance(provider, EltdxProvider)
    assert provider.request_timeout == 2.0


def test_create_provider_auto_falls_back_to_tencent_when_bridge_is_missing(monkeypatch) -> None:
    from stock_ts.providers import factory

    monkeypatch.setattr(factory, "is_eltdx_bridge_available", lambda: False)

    provider = create_provider("auto")

    assert isinstance(provider, TencentProvider)
    assert provider.request_timeout == 1.5


def test_create_provider_tencent_keeps_full_timeout() -> None:
    provider = create_provider("tencent")

    assert isinstance(provider, TencentProvider)
    assert provider.request_timeout == 10.0
