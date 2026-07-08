from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResolvedSymbol:
    query: str
    code: str
    name: str
    source: str
    warnings: list[str]


_SYMBOLS_BY_NAME: dict[str, tuple[str, str]] = {
    "大业股份": ("603278", "大业股份"),
    "贵州茅台": ("600519", "贵州茅台"),
    "平安银行": ("000001", "平安银行"),
    "宁德时代": ("300750", "宁德时代"),
}

_SYMBOLS_BY_CODE: dict[str, str] = {code: name for code, name in _SYMBOLS_BY_NAME.values()}

_SECTORS_BY_CODE: dict[str, str] = {
    "603278": "金属制品",
    "600519": "白酒",
    "000001": "银行",
    "300750": "新能源车",
}


def resolve_stock_query(query: str) -> ResolvedSymbol:
    """Resolve common A-share names and prefixed symbols to six-digit codes."""
    normalized = query.strip()
    compact = normalized.lower().removeprefix("sh").removeprefix("sz")
    warnings: list[str] = []

    if normalized in _SYMBOLS_BY_NAME:
        code, name = _SYMBOLS_BY_NAME[normalized]
        return ResolvedSymbol(normalized, code, name, "builtin-name", warnings)

    if compact.isdigit() and len(compact) == 6:
        name = _SYMBOLS_BY_CODE.get(compact, compact)
        source = "builtin-code" if compact in _SYMBOLS_BY_CODE else "code"
        return ResolvedSymbol(normalized, compact, name, source, warnings)

    warnings.append(f"未识别 {normalized} 对应的 A 股代码，已按原始输入尝试查询")
    return ResolvedSymbol(normalized, normalized, normalized, "unresolved", warnings)


def stock_name_for_code(code: str) -> str | None:
    return _SYMBOLS_BY_CODE.get(code.strip())


def sector_for_code(code: str) -> str:
    normalized = code.strip().lower().removeprefix("sh").removeprefix("sz")
    return _SECTORS_BY_CODE.get(normalized, "")
