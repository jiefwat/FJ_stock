from stock_ts.config import get_settings


def test_settings_has_app_id() -> None:
    assert get_settings().app_id == "stock-ts"
