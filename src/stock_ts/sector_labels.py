from __future__ import annotations

BOARD_LABELS = {
    "sse_star_market": "科创板",
    "szse_chinext": "创业板",
    "sse_main_board": "沪市主板",
    "szse_main_board": "深市主板",
    "bse_listed_stock": "北交所",
}
BOARD_THEME_FALLBACK = "未识别主题"
NON_THEME_LABELS = {
    "近期强势",
    "近期弱势",
    "最近情绪指数",
    "昨日上榜",
    "昨日首板",
    "昨日涨停",
    "昨日连板",
    "今日涨停",
    "密集调研",
    "拟减持",
    "绩优股",
    "社保重仓",
    "保险重仓",
    "养老金持股",
    "股权激励",
    "两年新股",
    "非周期股",
    "人民币贬值受益",
    "含可转债",
    "次新股",
}


def localize_sector_name(name: object) -> str:
    """Convert exchange board codes from data providers into user-facing names."""
    raw = str(name or "").strip()
    return BOARD_LABELS.get(raw, raw or "未分类")


def localize_theme_name(name: object) -> str:
    """Return a research theme label, never an exchange-board label."""
    raw = str(name or "").strip()
    if not raw:
        return BOARD_THEME_FALLBACK
    if (
        raw in BOARD_LABELS
        or raw in set(BOARD_LABELS.values()) | {"主板", "沪深A股"}
        or raw in NON_THEME_LABELS
        or raw.startswith("通达信")
        and raw[3:].isdigit()
    ):
        return BOARD_THEME_FALLBACK
    return raw
