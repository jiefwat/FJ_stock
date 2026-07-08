from stock_ts.symbols import resolve_stock_query


def test_resolve_chinese_stock_name_to_code() -> None:
    symbol = resolve_stock_query("大业股份")

    assert symbol.query == "大业股份"
    assert symbol.code == "603278"
    assert symbol.name == "大业股份"
    assert symbol.source == "builtin-name"


def test_resolve_common_name_and_plain_code() -> None:
    assert resolve_stock_query("贵州茅台").code == "600519"
    assert resolve_stock_query("600519").name == "贵州茅台"
    assert resolve_stock_query("sh603278").code == "603278"


def test_unresolved_query_keeps_input_with_warning() -> None:
    symbol = resolve_stock_query("未知公司")

    assert symbol.code == "未知公司"
    assert symbol.warnings


def test_sector_lookup_covers_current_verified_symbol():
    from stock_ts.symbols import sector_for_code

    assert sector_for_code("603278") == "金属制品"
