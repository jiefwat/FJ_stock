#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from stock_ts.data_quality import DataSourceAttempt, summarize_data_quality
from stock_ts.news_intelligence import (
    IntelligenceSource,
    classify_news_item,
    default_intelligence_sources_from_env,
    fetch_json_intelligence_sources,
    is_market_relevant_news,
)


def enrich_snapshot(
    snapshot_path: str | Path,
    *,
    codes: list[str] | None = None,
    limit: int = 20,
    bar_count: int = 120,
    news_limit: int = 5,
    market_news_limit: int = 20,
    sleep_seconds: float = 0.2,
    field_timeout: int = 12,
    request_timeout: float = 8.0,
    akshare_stock_fields: bool = True,
    tushare_moneyflow: bool = False,
    ak: object | None = None,
    tushare_client: object | None = None,
    itick_client: object | None = None,
    intelligence_urls: list[str] | None = None,
    intelligence_opener: Callable[[str, float], bytes] | None = None,
) -> dict[str, int | str]:
    path = Path(snapshot_path)
    snapshot = _read_json(path)
    if ak is None:
        _patch_requests_timeout(request_timeout)
    ak_client = ak or _load_akshare()
    ts_client = (
        tushare_client
        if tushare_client is not None
        else None
        if ak is not None
        else _load_tushare_optional(timeout=request_timeout)
    )
    itick = (
        itick_client
        if itick_client is not None
        else None
        if ak is not None
        else _load_itick_optional(timeout=request_timeout)
    )
    selected_codes = _select_codes(snapshot, explicit_codes=codes, limit=limit)
    enriched_count = 0
    errors: dict[str, str] = {}

    stocks = snapshot.setdefault("stocks", {})
    if not isinstance(stocks, dict):
        stocks = {}
        snapshot["stocks"] = stocks
    path.parent.mkdir(parents=True, exist_ok=True)

    for index, code in enumerate(selected_codes):
        try:
            current = stocks.get(code, {}) if isinstance(stocks.get(code), dict) else {}
            enriched = _enrich_stock_payload(
                code,
                current,
                ak_client,
                bar_count=bar_count,
                news_limit=news_limit,
                field_timeout=field_timeout,
                tushare_client=ts_client,
                itick_client=itick,
                akshare_stock_fields=akshare_stock_fields,
                tushare_moneyflow=tushare_moneyflow,
            )
            stocks[code] = enriched
            _merge_candidate_payload(snapshot, code, enriched)
            enriched_count += 1
        except Exception as exc:
            errors[code] = str(exc)[:240]
        # Flush each stock so a later timeout still leaves K-line/news/fundamental progress.
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if sleep_seconds > 0 and index < len(selected_codes) - 1:
            time.sleep(sleep_seconds)

    intelligence_result = _fetch_market_intelligence(
        ak_client,
        limit=market_news_limit,
        urls=intelligence_urls,
        opener=intelligence_opener,
        timeout=request_timeout,
        field_timeout=field_timeout,
    )
    market_news = intelligence_result["items"]
    if market_news:
        existing_market_news = [
            item for item in _as_list(snapshot.get("market_news")) if isinstance(item, dict)
        ]
        snapshot["market_news"] = _dedupe_news_payloads(existing_market_news + market_news)

    snapshot["external_enrichment"] = {
        "source": "multi-source",
        "sources": _external_source_names(ak_client, ts_client, itick),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requested_count": len(selected_codes),
        "enriched_stock_count": enriched_count,
        "error_count": len(errors),
        "errors": errors,
        "fields": ["daily_bars", "valuation", "fund_flow", "stock_news", "market_news"],
        "intelligence_statuses": intelligence_result["statuses"],
        "intelligence_warnings": intelligence_result["warnings"],
    }
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "output": str(path),
        "requested_count": len(selected_codes),
        "enriched_stock_count": enriched_count,
        "error_count": len(errors),
        "market_news_count": len(snapshot.get("market_news", []))
        if isinstance(snapshot.get("market_news"), list)
        else 0,
    }


def _enrich_stock_payload(
    code: str,
    current: dict[str, Any],
    ak: object,
    *,
    bar_count: int,
    news_limit: int,
    field_timeout: int,
    tushare_client: object | None,
    itick_client: object | None,
    akshare_stock_fields: bool,
    tushare_moneyflow: bool,
) -> dict[str, Any]:
    payload = dict(current)
    payload["code"] = code
    payload.setdefault("name", code)
    field_errors: dict[str, str] = {}

    if tushare_client is not None:
        try:
            with _time_limit(field_timeout):
                bars = _fetch_tushare_daily_bars(tushare_client, code, limit=bar_count)
            if bars:
                payload["bars"] = bars
                payload["bar_source"] = "tushare.daily"
                payload["price_reliable"] = True
        except Exception as exc:
            field_errors["tushare_daily"] = str(exc)[:180]
        try:
            with _time_limit(field_timeout):
                valuation = _fetch_tushare_daily_basic(tushare_client, code)
            if valuation:
                payload["valuation"] = valuation
                payload["pe_ttm"] = valuation.get("pe_ttm")
                if valuation.get("turnover_rate") is not None:
                    payload["turnover_rate"] = valuation.get("turnover_rate")
        except Exception as exc:
            field_errors["tushare_daily_basic"] = str(exc)[:180]
        try:
            with _time_limit(field_timeout):
                fundamentals = _fetch_tushare_fina_indicator(tushare_client, code)
            if fundamentals:
                payload["fundamental_metrics"] = fundamentals
        except Exception as exc:
            field_errors["tushare_fina_indicator"] = str(exc)[:180]
        if tushare_moneyflow:
            try:
                with _time_limit(field_timeout):
                    fund_detail = _fetch_tushare_moneyflow(tushare_client, code)
                if fund_detail:
                    payload["fund_flow_detail"] = fund_detail
                    payload["fund_flow"] = fund_detail.get("main_net_inflow")
            except Exception as exc:
                field_errors["tushare_moneyflow"] = str(exc)[:180]
        else:
            field_errors["tushare_moneyflow"] = "skipped"

    if itick_client is not None and payload.get("bar_source") != "tushare.daily":
        try:
            with _time_limit(field_timeout):
                bars = _fetch_itick_daily_bars(itick_client, code, limit=bar_count)
            if bars:
                payload["bars"] = bars
                payload["bar_source"] = "itick.stock_kline"
                payload["price_reliable"] = True
        except Exception as exc:
            field_errors["itick_daily"] = str(exc)[:180]
        try:
            with _time_limit(field_timeout):
                quote = _fetch_itick_tick(itick_client, code)
            if quote:
                payload["latest_quote"] = quote
        except Exception as exc:
            field_errors["itick_tick"] = str(exc)[:180]

    if akshare_stock_fields:
        try:
            if payload.get("bar_source") not in {"tushare.daily", "itick.stock_kline"}:
                with _time_limit(field_timeout):
                    bars = _fetch_daily_bars(ak, code, limit=bar_count)
            else:
                bars = []
            if bars:
                payload["bars"] = bars
                payload["bar_source"] = "akshare.stock_zh_a_hist"
                payload["price_reliable"] = True
        except Exception as exc:
            field_errors["daily_bars"] = str(exc)[:180]

        try:
            if not payload.get("valuation"):
                with _time_limit(field_timeout):
                    valuation = _fetch_valuation(ak, code)
            else:
                valuation = {}
            if valuation:
                payload["valuation"] = valuation
                payload["pe_ttm"] = valuation.get("pe_ttm")
        except Exception as exc:
            field_errors["valuation"] = str(exc)[:180]

        try:
            if not payload.get("fund_flow_detail"):
                with _time_limit(field_timeout):
                    fund_detail = _fetch_fund_flow(ak, code)
            else:
                fund_detail = {}
            if fund_detail:
                payload["fund_flow_detail"] = fund_detail
                payload["fund_flow"] = fund_detail.get("main_net_inflow")
        except Exception as exc:
            field_errors["fund_flow"] = str(exc)[:180]

        try:
            with _time_limit(field_timeout):
                news_items = _fetch_stock_news(ak, code, limit=news_limit)
            if news_items:
                payload["news_items"] = news_items
        except Exception as exc:
            field_errors["stock_news"] = str(exc)[:180]
    else:
        field_errors["akshare_stock_fields"] = "skipped"

    sources = set(_as_list(payload.get("data_sources")))
    if itick_client is not None and (
        payload.get("bar_source") == "itick.stock_kline" or payload.get("latest_quote")
    ):
        sources.add("itick")
    if akshare_stock_fields:
        sources.add("akshare")
    if tushare_client is not None:
        sources.add("tushare")
    payload["data_sources"] = sorted(str(item) for item in sources if item)
    payload["enriched_at"] = datetime.now(timezone.utc).isoformat()
    payload["data_quality"] = _stock_data_quality_payload(payload, field_errors)
    if field_errors:
        payload["enrichment_errors"] = field_errors
    return payload


def _fetch_daily_bars(ak: object, code: str, *, limit: int) -> list[dict[str, Any]]:
    frame = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")  # type: ignore[attr-defined]
    rows = _records(frame)[-limit:]
    bars: list[dict[str, Any]] = []
    for row in rows:
        bars.append(
            {
                "date": str(row.get("日期") or row.get("date") or ""),
                "open": _float(row.get("开盘", row.get("open"))),
                "high": _float(row.get("最高", row.get("high"))),
                "low": _float(row.get("最低", row.get("low"))),
                "close": _float(row.get("收盘", row.get("close"))),
                "volume": _float(row.get("成交量", row.get("volume", row.get("vol")))),
            }
        )
    return [bar for bar in bars if bar["date"] and bar["close"] > 0]


def _fetch_tushare_daily_bars(ts_client: object, code: str, *, limit: int) -> list[dict[str, Any]]:
    frame = ts_client.daily(ts_code=_tushare_code(code), limit=limit)  # type: ignore[attr-defined]
    rows = sorted(_records(frame), key=lambda row: str(row.get("trade_date") or ""))
    bars: list[dict[str, Any]] = []
    for row in rows[-limit:]:
        bars.append(
            {
                "date": _format_tushare_date(str(row.get("trade_date") or "")),
                "open": _float(row.get("open")),
                "high": _float(row.get("high")),
                "low": _float(row.get("low")),
                "close": _float(row.get("close")),
                "volume": _float(row.get("vol")) * 100,
            }
        )
    return [bar for bar in bars if bar["date"] and bar["close"] > 0]


def _fetch_itick_daily_bars(itick_client: object, code: str, *, limit: int) -> list[dict[str, Any]]:
    bars = itick_client.fetch_daily_bars(code, limit=limit)  # type: ignore[attr-defined]
    normalized: list[dict[str, Any]] = []
    for bar in bars:
        normalized.append(
            {
                "date": str(getattr(bar, "date", "")),
                "open": _float(getattr(bar, "open", 0.0)),
                "high": _float(getattr(bar, "high", 0.0)),
                "low": _float(getattr(bar, "low", 0.0)),
                "close": _float(getattr(bar, "close", 0.0)),
                "volume": _float(getattr(bar, "volume", 0.0)),
            }
        )
    return [bar for bar in normalized if bar["date"] and bar["close"] > 0]


def _fetch_itick_tick(itick_client: object, code: str) -> dict[str, Any]:
    quote = itick_client.fetch_tick(code)  # type: ignore[attr-defined]
    return quote if isinstance(quote, dict) else {}


def _fetch_tushare_daily_basic(ts_client: object, code: str) -> dict[str, Any]:
    frame = ts_client.daily_basic(  # type: ignore[attr-defined]
        ts_code=_tushare_code(code),
        limit=1,
        fields="ts_code,trade_date,close,turnover_rate,pe_ttm,pb,ps,total_mv,circ_mv",
    )
    rows = _records(frame)
    if not rows:
        return {}
    latest = rows[0]
    return {
        "source": "tushare.daily_basic",
        "date": _format_tushare_date(str(latest.get("trade_date") or "")),
        "pe_ttm": _optional_float(latest.get("pe_ttm")),
        "pb": _optional_float(latest.get("pb")),
        "ps": _optional_float(latest.get("ps")),
        "total_mv": _optional_float(latest.get("total_mv")),
        "circ_mv": _optional_float(latest.get("circ_mv")),
        "turnover_rate": _optional_float(latest.get("turnover_rate")),
    }


def _fetch_tushare_fina_indicator(ts_client: object, code: str) -> dict[str, Any]:
    frame = ts_client.fina_indicator(  # type: ignore[attr-defined]
        ts_code=_tushare_code(code),
        limit=1,
        fields=(
            "ts_code,end_date,or_yoy,netprofit_yoy,roe,grossprofit_margin,"
            "debt_to_assets,ocf_to_profit"
        ),
    )
    rows = _records(frame)
    if not rows:
        return {}
    latest = rows[0]
    return {
        "source": "tushare.fina_indicator",
        "date": _format_tushare_date(str(latest.get("end_date") or "")),
        "revenue_yoy": _optional_float(latest.get("or_yoy")),
        "net_profit_yoy": _optional_float(latest.get("netprofit_yoy")),
        "roe": _optional_float(latest.get("roe")),
        "gross_margin": _optional_float(latest.get("grossprofit_margin")),
        "debt_to_assets": _optional_float(latest.get("debt_to_assets")),
        "ocf_to_profit": _optional_float(latest.get("ocf_to_profit")),
    }


def _fetch_tushare_moneyflow(ts_client: object, code: str) -> dict[str, Any]:
    frame = ts_client.moneyflow(ts_code=_tushare_code(code), limit=1)  # type: ignore[attr-defined]
    rows = _records(frame)
    if not rows:
        return {}
    latest = rows[0]
    main = _float(latest.get("net_mf_amount"))
    return {
        "source": "tushare.moneyflow",
        "date": _format_tushare_date(str(latest.get("trade_date") or "")),
        "main_net_inflow": round(main / 10000, 4),
        "main_net_inflow_yuan": main * 10000,
    }


def _fetch_valuation(ak: object, code: str) -> dict[str, Any]:
    frame = ak.stock_value_em(symbol=code)  # type: ignore[attr-defined]
    rows = _records(frame)
    if not rows:
        return {}
    latest = rows[-1]
    return {
        "source": "akshare.stock_value_em",
        "date": str(latest.get("数据日期") or latest.get("date") or ""),
        "pe_ttm": _optional_float(latest.get("PE(TTM)", latest.get("pe_ttm"))),
        "pb": _optional_float(latest.get("市净率", latest.get("pb"))),
        "ps": _optional_float(latest.get("市销率", latest.get("ps"))),
        "total_mv": _optional_float(latest.get("总市值", latest.get("total_mv"))),
    }


def _fetch_fund_flow(ak: object, code: str) -> dict[str, Any]:
    frame = ak.stock_individual_fund_flow(stock=code, market=_ak_market(code))  # type: ignore[attr-defined]
    rows = _records(frame)
    if not rows:
        return {}
    latest = rows[-1]
    main_yuan = _float(latest.get("主力净流入-净额", latest.get("main_net_inflow")))
    return {
        "source": "akshare.stock_individual_fund_flow",
        "date": str(latest.get("日期") or latest.get("date") or ""),
        "main_net_inflow": round(main_yuan / 100000000, 4),
        "main_net_inflow_yuan": main_yuan,
        "main_net_pct": _optional_float(
            latest.get("主力净流入-净占比", latest.get("main_net_pct"))
        ),
        "super_large_net_inflow_yuan": _optional_float(latest.get("超大单净流入-净额")),
        "large_net_inflow_yuan": _optional_float(latest.get("大单净流入-净额")),
        "small_net_inflow_yuan": _optional_float(latest.get("小单净流入-净额")),
    }


def _fetch_stock_news(ak: object, code: str, *, limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    frame = ak.stock_news_em(symbol=code)  # type: ignore[attr-defined]
    rows = _records(frame)[:limit]
    news: list[dict[str, Any]] = []
    for row in rows:
        item = _news_from_row(row, source_default="东方财富")
        if item["title"]:
            news.append(item)
    return news


def _fetch_market_news(ak: object, *, limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    frame = ak.stock_info_global_em()  # type: ignore[attr-defined]
    rows = _records(frame)[:limit]
    news: list[dict[str, Any]] = []
    for row in rows:
        item = _news_from_row(row, source_default="东方财富财经")
        if item["title"]:
            news.append(item)
    return news


def _fetch_market_intelligence(
    ak: object,
    *,
    limit: int,
    urls: list[str] | None,
    opener: Callable[[str, float], bytes] | None,
    timeout: float,
    field_timeout: int,
) -> dict[str, Any]:
    try:
        with _time_limit(field_timeout):
            builtin = _fetch_market_news(ak, limit=limit)
        builtin_status = f"ok:{len(builtin)}"
        warnings: list[str] = []
    except Exception as exc:
        builtin = []
        builtin_status = f"failed:{type(exc).__name__}:{str(exc)[:120]}"
        warnings = [f"AKShare 市场新闻抓取失败：{type(exc).__name__}"]
    external_sources = _intelligence_sources(urls)
    if not external_sources:
        return {
            "items": _dedupe_news_payloads(builtin),
            "statuses": {"akshare-global": builtin_status},
            "warnings": warnings,
        }
    external = fetch_json_intelligence_sources(
        external_sources,
        opener=opener,
        timeout=timeout,
        limit_per_source=limit,
    )
    items = builtin + [item.to_payload() for item in external.items]
    statuses = {"akshare-global": builtin_status, **external.source_statuses}
    return {
        "items": _dedupe_news_payloads(items),
        "statuses": statuses,
        "warnings": warnings + external.warnings,
    }


def _intelligence_sources(urls: list[str] | None) -> list[IntelligenceSource]:
    explicit = ",".join(urls or [])
    env_raw = os.getenv("STOCK_TS_INTELLIGENCE_URLS", "")
    return default_intelligence_sources_from_env(
        ",".join(item for item in [explicit, env_raw] if item)
    )


def _dedupe_news_payloads(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in items:
        key = str(item.get("url") or item.get("title") or "").strip()
        if not key or key in seen:
            continue
        if not is_market_relevant_news(
            str(item.get("title") or ""), str(item.get("summary") or "")
        ):
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


@contextmanager
def _time_limit(seconds: int):
    if seconds <= 0:
        yield
        return

    def _raise_timeout(_signum, _frame):
        raise TimeoutError(f"external field timed out after {seconds}s")

    previous = signal.signal(signal.SIGALRM, _raise_timeout)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def _news_from_row(row: dict[str, Any], *, source_default: str) -> dict[str, Any]:
    title = str(row.get("新闻标题") or row.get("标题") or row.get("title") or "").strip()
    summary = str(row.get("新闻内容") or row.get("摘要") or row.get("summary") or "").strip()
    classification = classify_news_item(title, summary)
    return {
        "date": str(row.get("发布时间") or row.get("时间") or row.get("date") or ""),
        "source": str(row.get("文章来源") or row.get("source") or source_default),
        "title": title,
        "summary": summary,
        "url": str(row.get("新闻链接") or row.get("链接") or row.get("url") or ""),
        "sentiment": classification.sentiment,
        "risk_tags": classification.risk_tags,
        "catalyst_tags": classification.catalyst_tags,
    }


def _select_codes(
    snapshot: dict[str, Any],
    *,
    explicit_codes: list[str] | None,
    limit: int,
) -> list[str]:
    if explicit_codes is None and limit <= 0:
        return []
    seen: set[str] = set()
    selected: list[str] = []
    sources: list[str] = []
    if explicit_codes:
        sources.extend(explicit_codes)
    stocks = snapshot.get("stocks", {})
    if isinstance(stocks, dict):
        sources.extend(str(code) for code in stocks.keys())
    universe = snapshot.get("candidate_universe", {})
    if isinstance(universe, dict):
        for item in _as_list(universe.get("items")):
            if isinstance(item, dict):
                sources.append(str(item.get("code") or ""))
    for code in sources:
        normalized = _normalize_code(code)
        if normalized and normalized not in seen:
            seen.add(normalized)
            selected.append(normalized)
        if not explicit_codes and limit > 0 and len(selected) >= limit:
            break
    return selected


def _merge_candidate_payload(snapshot: dict[str, Any], code: str, enriched: dict[str, Any]) -> None:
    universe = snapshot.get("candidate_universe", {})
    if not isinstance(universe, dict):
        return
    items = universe.get("items", [])
    if not isinstance(items, list):
        return
    for item in items:
        if isinstance(item, dict) and _normalize_code(str(item.get("code") or "")) == code:
            for key in [
                "bars",
                "bar_source",
                "price_reliable",
                "latest_quote",
                "pe_ttm",
                "valuation",
                "fund_flow",
                "fund_flow_detail",
                "news_items",
                "data_sources",
                "enriched_at",
            ]:
                if key in enriched:
                    item[key] = enriched[key]
            break


def _records(frame: object) -> list[dict[str, Any]]:
    if frame is None or bool(getattr(frame, "empty", False)):
        return []
    if hasattr(frame, "to_dict"):
        return [dict(item) for item in frame.to_dict("records")]  # type: ignore[call-arg]
    if hasattr(frame, "iterrows"):
        return [dict(row) for _, row in frame.iterrows()]  # type: ignore[attr-defined]
    if isinstance(frame, list):
        return [dict(item) for item in frame if isinstance(item, dict)]
    return []


def _ak_market(code: str) -> str:
    return "sh" if code.startswith(("6", "9")) else "bj" if code.startswith(("8", "4")) else "sz"


def _normalize_code(code: str) -> str:
    digits = "".join(ch for ch in str(code).strip() if ch.isdigit())
    return digits[:6] if len(digits) >= 6 else ""


def _tushare_code(code: str) -> str:
    normalized = _normalize_code(code)
    if normalized.startswith(("6", "9")):
        return f"{normalized}.SH"
    if normalized.startswith(("8", "4")):
        return f"{normalized}.BJ"
    return f"{normalized}.SZ"


def _format_tushare_date(value: str) -> str:
    text = value.strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return text


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _load_akshare() -> object:
    try:
        import akshare as ak  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("AKShare is not installed. Run: pip install akshare") from exc
    return ak


def _load_tushare_optional(*, timeout: float = 8.0) -> object | None:
    try:
        from stock_ts.config import get_settings
    except Exception:
        return None
    token = get_settings().tushare_token.strip()
    if not token:
        return None
    try:
        import tushare as ts  # type: ignore[import-not-found]
    except ImportError:
        return None
    return ts.pro_api(token, timeout=timeout)


def _load_itick_optional(*, timeout: float = 8.0) -> object | None:
    try:
        from stock_ts.config import get_settings
        from stock_ts.providers.itick_provider import ItickClient
    except Exception:
        return None
    key = get_settings().itick_api_key.strip()
    if not key:
        return None
    return ItickClient(api_key=key, timeout=timeout)


def _stock_data_quality_payload(
    payload: dict[str, Any], field_errors: dict[str, str]
) -> dict[str, Any]:
    attempts: list[DataSourceAttempt] = []
    active_errors = {key: value for key, value in field_errors.items() if value != "skipped"}
    sources = set(_as_list(payload.get("data_sources")))
    if "tushare" in sources:
        attempts.append(
            DataSourceAttempt(
                "tushare", ok=not any(key.startswith("tushare") for key in active_errors)
            )
        )
    if "itick" in sources:
        attempts.append(
            DataSourceAttempt("itick", ok=not any(key.startswith("itick") for key in active_errors))
        )
    if "akshare" in sources:
        attempts.append(
            DataSourceAttempt(
                "akshare",
                ok=not any(
                    key in active_errors
                    for key in ["daily_bars", "valuation", "fund_flow", "stock_news"]
                ),
            )
        )
    for key, reason in active_errors.items():
        source = key.split("_", 1)[0]
        if source in {"daily", "valuation", "fund", "stock"}:
            source = "akshare"
        if source == "akshare" and any(attempt.source == "akshare" for attempt in attempts):
            continue
        attempts.append(DataSourceAttempt(source, ok=False, reason=reason))
    primary_source = str(payload.get("bar_source") or "multi-source")
    summary = summarize_data_quality(
        primary_source=primary_source,
        payload=payload,
        required_fields=["bars", "valuation", "fund_flow_detail", "news_items"],
        attempts=attempts,
    )
    return summary.to_payload()


def _external_source_names(
    ak: object, tushare_client: object | None, itick_client: object | None
) -> list[str]:
    names = ["akshare"] if ak is not None else []
    if tushare_client is not None:
        names.append("tushare")
    if itick_client is not None:
        names.append("itick")
    return names


def _patch_requests_timeout(timeout: float) -> None:
    if timeout <= 0:
        return
    try:
        import requests  # type: ignore[import-not-found]
    except Exception:
        return
    original = requests.sessions.Session.request
    if getattr(original, "_stockts_timeout_patch", False):
        return

    def request_with_timeout(self, method, url, **kwargs):  # type: ignore[no-untyped-def]
        kwargs.setdefault("timeout", timeout)
        return original(self, method, url, **kwargs)

    request_with_timeout._stockts_timeout_patch = True  # type: ignore[attr-defined]
    requests.sessions.Session.request = request_with_timeout


def _as_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _float(value: object) -> float:
    parsed = _optional_float(value)
    return parsed if parsed is not None else 0.0


def _optional_float(value: object) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Enrich StockTS TDX snapshot with AKShare K-line, valuation, fund flow and news."
        )
    )
    parser.add_argument("--snapshot", default="data/imports/tdx_snapshots.json")
    parser.add_argument(
        "--codes",
        default="",
        help="Comma separated stock codes. Defaults to stocks plus candidate universe.",
    )
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--bar-count", type=int, default=120)
    parser.add_argument("--news-limit", type=int, default=5)
    parser.add_argument("--market-news-limit", type=int, default=20)
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--field-timeout", type=int, default=12)
    parser.add_argument("--request-timeout", type=float, default=8.0)
    parser.add_argument(
        "--skip-akshare-stock-fields",
        action="store_true",
        help="Use Tushare for stock fields and skip slow AKShare per-stock calls.",
    )
    parser.add_argument(
        "--enable-tushare-moneyflow",
        action="store_true",
        help="Try Tushare moneyflow when the token has permission.",
    )
    parser.add_argument(
        "--intelligence-url",
        action="append",
        default=[],
        help=(
            "Optional NewsNow/RSS-bridge JSON URL; can be repeated. "
            "Env: STOCK_TS_INTELLIGENCE_URLS"
        ),
    )
    args = parser.parse_args(argv)
    codes = [item.strip() for item in args.codes.split(",") if item.strip()] or None
    summary = enrich_snapshot(
        args.snapshot,
        codes=codes,
        limit=args.limit,
        bar_count=args.bar_count,
        news_limit=args.news_limit,
        market_news_limit=args.market_news_limit,
        sleep_seconds=args.sleep,
        field_timeout=args.field_timeout,
        request_timeout=args.request_timeout,
        akshare_stock_fields=not args.skip_akshare_stock_fields,
        tushare_moneyflow=args.enable_tushare_moneyflow,
        intelligence_urls=args.intelligence_url,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
