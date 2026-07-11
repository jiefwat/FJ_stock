from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from stock_ts.data_chain import validate_data_chain

OK_STEPS = {
    "refresh": "ok",
    "tdx_enrich": "ok",
    "a_share_kline": "ok",
    "external_enrich": "ok",
    "announcements": "ok",
    "report": "ok",
}

SKIPPED_STEPS = {
    "refresh": "skipped",
    "tdx_enrich": "skipped",
    "a_share_kline": "skipped",
    "external_enrich": "skipped",
    "announcements": "skipped",
    "report": "ok",
}


def _bar(date: str = "2026-07-10") -> dict[str, float | str]:
    return {
        "date": date,
        "open": 10.0,
        "high": 11.0,
        "low": 9.8,
        "close": 10.6,
        "volume": 1000000.0,
    }


def _stock(code: str, *, with_context: bool = True, with_bars: bool = True) -> dict:
    payload = {
        "code": code,
        "name": f"测试{code}",
        "bars": [_bar("2026-07-09"), _bar("2026-07-10")] if with_bars else [],
        "theme": "半导体",
        "sector": "科技",
    }
    if with_context:
        payload.update(
            {
                "valuation": {"pe_ttm": 28.5, "source": "tushare.daily_basic"},
                "fundamental_metrics": {
                    "date": "2026-03-31",
                    "roe": 9.6,
                    "source": "akshare.stock_financial_analysis_indicator_em",
                },
                "fund_flow_detail": {
                    "date": "2026-07-10",
                    "main_net_inflow": 1.2,
                    "source": "akshare.stock_individual_fund_flow",
                },
                "news_items": [
                    {
                        "date": "2026-07-10",
                        "title": "测试公司订单增长",
                        "source": "eastmoney",
                    }
                ],
                "announcements": [
                    {
                        "date": "2026-07-10",
                        "title": "测试公司业绩预告",
                        "source": "cninfo",
                    }
                ],
            }
        )
    return payload


def _write_holdings(path: Path, codes: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=["code", "name", "shares", "cost_price", "sector", "note"]
        )
        writer.writeheader()
        for code in codes:
            writer.writerow(
                {
                    "code": code,
                    "name": f"测试{code}",
                    "shares": "100",
                    "cost_price": "10",
                    "sector": "科技",
                    "note": "",
                }
            )


def _write_snapshot(path: Path, *, context: bool = True, bars: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "tdx-snapshot",
        "generated_at": "2026-07-10T15:05:00",
        "market": {
            "trade_date": "2026-07-10",
            "indices": [{"code": "000001", "name": "上证指数", "close": 3500, "pct_chg": 0.8}],
            "advancing": 2600,
            "declining": 2100,
            "top_sectors": [["半导体", 3.2]],
        },
        "sectors": [{"name": "半导体", "pct_chg": 3.2}],
        "market_news": [
            {
                "date": "2026-07-10",
                "title": "半导体板块异动走强",
                "source": "longbridge.mcp.市场异动",
            }
        ],
        "candidate_universe": {
            "items": [
                {
                    **_stock("688362", with_context=context, with_bars=bars),
                    "pct_chg": 6.2,
                },
                {
                    **_stock("603278", with_context=context, with_bars=bars),
                    "pct_chg": 4.1,
                },
            ]
        },
        "stocks": {
            "688362": _stock("688362", with_context=context, with_bars=bars),
            "603278": _stock("603278", with_context=context, with_bars=bars),
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_data_chain_validator_marks_complete_snapshot_ok(tmp_path: Path) -> None:
    snapshot = tmp_path / "tdx_snapshots.json"
    holdings = tmp_path / "holdings.csv"
    output = tmp_path / "reports" / "daily" / "data_chain_status.json"
    _write_snapshot(snapshot)
    _write_holdings(holdings, ["688362", "603278"])

    result = validate_data_chain(
        snapshot_path=snapshot,
        holdings_path=holdings,
        output_path=output,
        pipeline_steps=OK_STEPS,
        now=datetime(2026, 7, 11, 9, 0, 0),
    )

    assert result["status"] == "ok"
    assert result["modules"]["market"]["status"] == "ok"
    assert result["modules"]["portfolio"]["coverage"]["complete"] == 2
    assert result["modules"]["opportunities"]["status"] == "ok"
    assert output.exists()


def test_data_chain_validator_warns_when_context_sources_missing(tmp_path: Path) -> None:
    snapshot = tmp_path / "tdx_snapshots.json"
    holdings = tmp_path / "holdings.csv"
    _write_snapshot(snapshot, context=False)
    _write_holdings(holdings, ["688362"])

    result = validate_data_chain(
        snapshot_path=snapshot,
        holdings_path=holdings,
        pipeline_steps=OK_STEPS,
        now=datetime(2026, 7, 11, 9, 0, 0),
    )

    assert result["status"] == "warn"
    assert "基本面" in "、".join(result["warnings"])
    assert "资金面" in "、".join(result["warnings"])
    assert "个股新闻" in "、".join(result["warnings"])
    assert "公告" in "、".join(result["warnings"])
    assert result["modules"]["portfolio"]["coverage"]["complete"] == 0


def test_data_chain_validator_blocks_when_holding_kline_missing(tmp_path: Path) -> None:
    snapshot = tmp_path / "tdx_snapshots.json"
    holdings = tmp_path / "holdings.csv"
    _write_snapshot(snapshot, bars=False)
    _write_holdings(holdings, ["688362"])

    result = validate_data_chain(
        snapshot_path=snapshot,
        holdings_path=holdings,
        pipeline_steps=OK_STEPS,
        now=datetime(2026, 7, 11, 9, 0, 0),
    )

    assert result["status"] == "failed"
    assert any("688362" in blocker and "K线" in blocker for blocker in result["blockers"])


def test_data_chain_validator_warns_not_blocks_when_hk_holding_kline_is_stale(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "tdx_snapshots.json"
    holdings = tmp_path / "holdings.csv"
    _write_snapshot(snapshot)
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    payload["stocks"]["06088"] = _stock("06088", with_context=False, with_bars=True)
    payload["stocks"]["06088"]["bars"] = [_bar("2026-07-09")]
    snapshot.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    _write_holdings(holdings, ["06088"])

    result = validate_data_chain(
        snapshot_path=snapshot,
        holdings_path=holdings,
        pipeline_steps=OK_STEPS,
        now=datetime(2026, 7, 11, 9, 0, 0),
    )

    assert result["status"] == "warn"
    assert not result["blockers"]
    assert any("港股 06088 K线滞后" in warning for warning in result["warnings"])


def test_data_chain_validator_treats_skipped_pipeline_steps_as_incomplete(tmp_path: Path) -> None:
    snapshot = tmp_path / "tdx_snapshots.json"
    holdings = tmp_path / "holdings.csv"
    _write_snapshot(snapshot)
    _write_holdings(holdings, ["688362"])

    result = validate_data_chain(
        snapshot_path=snapshot,
        holdings_path=holdings,
        pipeline_steps=SKIPPED_STEPS,
        now=datetime(2026, 7, 11, 9, 0, 0),
    )

    assert result["status"] == "warn"
    assert result["modules"]["automation"]["status"] == "warn"
    assert "refresh=skipped" in "、".join(result["warnings"])
