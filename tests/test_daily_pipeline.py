from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from stock_ts.announcements import AnnouncementItem, AnnouncementReport


def _load_pipeline_module():
    spec = importlib.util.spec_from_file_location(
        "run_daily_pipeline", Path("scripts/run_daily_pipeline.py")
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_daily_pipeline"] = module
    spec.loader.exec_module(module)
    return module


pipeline_module = _load_pipeline_module()
DailyPipelineConfig = pipeline_module.DailyPipelineConfig
run_daily_pipeline = pipeline_module.run_daily_pipeline


def _write_snapshot(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bars = [
        {"date": "2026-07-10", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 1000}
    ]
    path.write_text(
        json.dumps(
            {
                "market": {
                    "trade_date": "2026-07-10",
                    "indices": [
                        {
                            "code": "000001",
                            "name": "上证指数",
                            "close": 3500,
                            "pct_chg": 0.5,
                        }
                    ],
                    "top_sectors": [["半导体", 2.5]],
                },
                "market_news": [
                    {
                        "date": "2026-07-10",
                        "title": "半导体异动",
                        "source": "longbridge.mcp.市场异动",
                    }
                ],
                "candidate_universe": {
                    "items": [
                        {
                            "code": "688362",
                            "name": "甬矽电子",
                            "bars": bars,
                            "theme": "半导体",
                            "pct_chg": 6.0,
                        },
                        {
                            "code": "600481",
                            "name": "双良节能",
                            "bars": bars,
                            "theme": "光伏",
                            "pct_chg": 1.0,
                        },
                    ]
                },
                "stocks": {
                    "603278": {
                        "name": "大业股份",
                        "bars": bars,
                        "valuation": {"source": "tushare.daily_basic"},
                        "fundamental_metrics": {"source": "akshare", "date": "2026-03-31"},
                        "fund_flow_detail": {
                            "source": "derived.kline_turnover",
                            "date": "2026-07-10",
                        },
                        "news_items": [
                            {"date": "2026-07-10", "title": "订单增长", "source": "eastmoney"}
                        ],
                        "announcements": [
                            {"date": "2026-07-10", "title": "业绩预告", "source": "cninfo"}
                        ],
                    },
                    "688362": {
                        "name": "甬矽电子",
                        "bars": bars,
                        "valuation": {"source": "tushare.daily_basic"},
                        "fundamental_metrics": {"source": "akshare", "date": "2026-03-31"},
                        "fund_flow_detail": {"source": "akshare", "date": "2026-07-10"},
                        "news_items": [
                            {"date": "2026-07-10", "title": "封测景气", "source": "eastmoney"}
                        ],
                        "announcements": [
                            {"date": "2026-07-10", "title": "经营公告", "source": "cninfo"}
                        ],
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_daily_pipeline_runs_refresh_enrich_announcements_and_report(tmp_path: Path) -> None:
    snapshot = tmp_path / "tdx_snapshots.json"
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n"
        "603278,大业股份,100,10,高端装备,测试\n"
        "688362,甬矽电子,100,20,半导体,测试\n",
        encoding="utf-8",
    )
    calls: list[list[str]] = []

    def fake_runner(command: list[str], timeout_seconds: int) -> None:
        calls.append(command)
        if any("refresh_tdx_snapshot.py" in item for item in command):
            _write_snapshot(snapshot)
        if any("enrich_tdx_snapshot.py" in item for item in command):
            payload = json.loads(snapshot.read_text(encoding="utf-8"))
            payload["external_enrichment"] = {
                "generated_at": "2026-06-26T16:40:00",
                "enriched_stock_count": 2,
            }
            snapshot.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        if any("run_daily_analysis.py" in item for item in command):
            out_dir = Path(command[command.index("--output-dir") + 1])
            html_dir = Path(command[command.index("--html-dir") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            html_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "latest.status").write_text(
                "status=ok\ntrade_date=2026-06-26\n", encoding="utf-8"
            )
            (out_dir / "latest.md").write_text("# report", encoding="utf-8")
            (html_dir / "latest.html").write_text("<html></html>", encoding="utf-8")

    result = run_daily_pipeline(
        DailyPipelineConfig(
            snapshot_path=snapshot,
            holdings_path=holdings,
            output_dir=tmp_path / "reports" / "daily",
            html_dir=tmp_path / "reports" / "html",
            announcement_dir=tmp_path / "reports" / "announcements",
            provider_name="tdx-snapshot",
            candidate_limit=50,
            enrich_limit=12,
            announcement_limit=3,
            skip_refresh=False,
            skip_external_enrich=False,
            skip_announcements=False,
        ),
        runner=fake_runner,
    )

    assert result.ok is True
    assert result.status_path.exists()
    status = result.status_path.read_text(encoding="utf-8")
    assert "status=ok" in status
    assert "refresh=ok" in status
    assert "external_enrich=ok" in status
    assert "announcements=ok" in status
    assert "report=ok" in status
    assert "codes=603278,688362" in status
    assert any(any("refresh_tdx_snapshot.py" in item for item in command) for command in calls)
    assert any(any("refresh_a_share_kline.py" in item for item in command) for command in calls)
    enrich_command = next(
        command for command in calls if any("enrich_tdx_snapshot.py" in item for item in command)
    )
    assert "--news-limit" in enrich_command
    assert enrich_command[enrich_command.index("--news-limit") + 1] == "3"
    assert "--market-news-limit" in enrich_command
    assert enrich_command[enrich_command.index("--market-news-limit") + 1] == "20"
    assert any(any("run_daily_analysis.py" in item for item in command) for command in calls)
    assert "a_share_kline=ok" in status
    assert (tmp_path / "reports" / "announcements" / "latest.md").exists()
    decisions_path = tmp_path / "reports" / "daily" / "latest_decisions.json"
    assert decisions_path.exists()
    decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
    assert decisions["schema_version"] == 1


def test_daily_pipeline_writes_cninfo_announcements_back_to_snapshot(
    tmp_path: Path, monkeypatch
) -> None:
    snapshot = tmp_path / "tdx_snapshots.json"
    _write_snapshot(snapshot)

    def fake_fetch(query: str, *, limit: int):
        return AnnouncementReport(
            query=query,
            total=1,
            items=[
                AnnouncementItem(
                    code=query,
                    name="测试公司",
                    title="测试公司半年度业绩预告公告",
                    date="2026-07-09",
                    url="https://static.cninfo.com.cn/test.pdf",
                    risk_flags=[],
                )
            ],
            risk_events=[],
        )

    monkeypatch.setattr(pipeline_module, "fetch_cninfo_announcements", fake_fetch)

    pipeline_module._write_announcements(
        DailyPipelineConfig(
            snapshot_path=snapshot,
            announcement_dir=tmp_path / "reports" / "announcements",
            announcement_limit=3,
        ),
        ["603278"],
    )

    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    announcements = payload["stocks"]["603278"]["announcements"]
    assert announcements[0]["title"] == "测试公司半年度业绩预告公告"
    assert announcements[0]["source"] == "cninfo"
    assert payload["announcement_refresh"]["source"] == "cninfo"
    assert payload["announcement_refresh"]["requested_count"] == 1
    assert payload["announcement_refresh"]["updated_count"] == 1


def test_daily_pipeline_refreshes_announcements_for_all_holdings_not_only_limit(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "tdx_snapshots.json"
    holdings = tmp_path / "holdings.csv"
    _write_snapshot(snapshot)
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n"
        "603278,大业股份,100,10,高端装备,测试\n"
        "688362,甬矽电子,100,20,半导体,测试\n"
        "300516,久之洋,100,30,军工,测试\n",
        encoding="utf-8",
    )
    codes = ["603278", "688362", "300516", "600481"]

    selected = pipeline_module._announcement_codes(
        DailyPipelineConfig(
            snapshot_path=snapshot,
            holdings_path=holdings,
            announcement_limit=1,
        ),
        codes,
    )

    assert selected == ["603278", "688362", "300516"]


def test_daily_pipeline_records_step_failure_without_hiding_error(tmp_path: Path) -> None:
    snapshot = tmp_path / "tdx_snapshots.json"
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n603278,大业股份,100,10,高端装备,测试\n",
        encoding="utf-8",
    )

    def failing_runner(command: list[str], timeout_seconds: int) -> None:
        raise RuntimeError("network down")

    result = run_daily_pipeline(
        DailyPipelineConfig(
            snapshot_path=snapshot,
            holdings_path=holdings,
            output_dir=tmp_path / "reports" / "daily",
            html_dir=tmp_path / "reports" / "html",
            skip_refresh=False,
        ),
        runner=failing_runner,
    )

    assert result.ok is False
    status = result.status_path.read_text(encoding="utf-8")
    assert "status=failed" in status
    assert "network down" in status


def test_daily_pipeline_continues_when_external_enrichment_times_out(tmp_path: Path) -> None:
    snapshot = tmp_path / "tdx_snapshots.json"
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n603278,大业股份,100,10,高端装备,测试\n",
        encoding="utf-8",
    )
    _write_snapshot(snapshot)

    def runner(command: list[str], timeout_seconds: int) -> None:
        if any("enrich_tdx_snapshot.py" in item for item in command):
            raise TimeoutError("external timeout")
        if any("run_daily_analysis.py" in item for item in command):
            out_dir = Path(command[command.index("--output-dir") + 1])
            html_dir = Path(command[command.index("--html-dir") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            html_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "latest.status").write_text("status=ok\n", encoding="utf-8")
            (out_dir / "latest.md").write_text("# report", encoding="utf-8")
            (html_dir / "latest.html").write_text("<html></html>", encoding="utf-8")

    result = run_daily_pipeline(
        DailyPipelineConfig(
            snapshot_path=snapshot,
            holdings_path=holdings,
            output_dir=tmp_path / "reports" / "daily",
            html_dir=tmp_path / "reports" / "html",
            announcement_dir=tmp_path / "reports" / "announcements",
            skip_refresh=True,
            skip_tdx_enrich=True,
            skip_announcements=True,
        ),
        runner=runner,
    )

    assert result.ok is True
    status = result.status_path.read_text(encoding="utf-8")
    assert "status=degraded" in status
    assert "external_enrich=failed" in status
    assert "data_chain=warn" in status
    assert "report=ok" in status


def test_daily_pipeline_continues_when_a_share_kline_hits_rate_limit(tmp_path: Path) -> None:
    snapshot = tmp_path / "tdx_snapshots.json"
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n603278,大业股份,100,10,高端装备,测试\n",
        encoding="utf-8",
    )
    _write_snapshot(snapshot)
    calls: list[list[str]] = []

    def runner(command: list[str], timeout_seconds: int) -> None:
        calls.append(command)
        if any("refresh_a_share_kline.py" in item for item in command):
            raise RuntimeError("tushare rate limit")
        if any("run_daily_analysis.py" in item for item in command):
            out_dir = Path(command[command.index("--output-dir") + 1])
            html_dir = Path(command[command.index("--html-dir") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            html_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "latest.status").write_text("status=ok\n", encoding="utf-8")
            (out_dir / "latest.md").write_text("# report", encoding="utf-8")
            (html_dir / "latest.html").write_text("<html></html>", encoding="utf-8")

    result = run_daily_pipeline(
        DailyPipelineConfig(
            snapshot_path=snapshot,
            holdings_path=holdings,
            output_dir=tmp_path / "reports" / "daily",
            html_dir=tmp_path / "reports" / "html",
            announcement_dir=tmp_path / "reports" / "announcements",
            skip_refresh=True,
            skip_tdx_enrich=True,
            skip_announcements=True,
        ),
        runner=runner,
    )

    assert result.ok is True
    status = result.status_path.read_text(encoding="utf-8")
    assert "a_share_kline=failed" in status
    assert "tushare rate limit" in status
    assert "external_enrich=ok" in status
    assert "report=ok" in status
    assert any(any("run_daily_analysis.py" in item for item in command) for command in calls)


def test_daily_pipeline_enriches_holdings_with_news_before_broad_candidate_chunks(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "tdx_snapshots.json"
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n"
        "603278,大业股份,100,10,高端装备,测试\n"
        "688362,甬矽电子,100,20,半导体,测试\n",
        encoding="utf-8",
    )
    _write_snapshot(snapshot)
    calls: list[list[str]] = []

    def runner(command: list[str], timeout_seconds: int) -> None:
        calls.append(command)
        if any("run_daily_analysis.py" in item for item in command):
            out_dir = Path(command[command.index("--output-dir") + 1])
            html_dir = Path(command[command.index("--html-dir") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            html_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "latest.status").write_text("status=ok\n", encoding="utf-8")
            (out_dir / "latest.md").write_text("# report", encoding="utf-8")
            (html_dir / "latest.html").write_text("<html></html>", encoding="utf-8")

    result = run_daily_pipeline(
        DailyPipelineConfig(
            snapshot_path=snapshot,
            holdings_path=holdings,
            output_dir=tmp_path / "reports" / "daily",
            html_dir=tmp_path / "reports" / "html",
            announcement_dir=tmp_path / "reports" / "announcements",
            enrich_limit=12,
            skip_refresh=True,
            skip_tdx_enrich=True,
            skip_a_share_kline=True,
            skip_announcements=True,
        ),
        runner=runner,
    )

    assert result.ok is True
    enrich_calls = [
        command
        for command in calls
        if any("enrich_tdx_snapshot.py" in item for item in command)
    ]
    assert len(enrich_calls) >= 2
    holdings_command = enrich_calls[0]
    assert holdings_command[holdings_command.index("--codes") + 1] == "603278,688362"
    assert "--skip-akshare-stock-fields" not in holdings_command
    assert holdings_command[holdings_command.index("--news-limit") + 1] == "3"
    assert any("--skip-akshare-stock-fields" in command for command in enrich_calls[1:])


def test_daily_pipeline_uses_python311_for_tdx_bridge_when_runner_python_lacks_eltdx(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        pipeline_module,
        "_python_can_import_eltdx",
        lambda executable: executable == "python3.11",
    )
    config = DailyPipelineConfig(python_executable=".venv/bin/python")

    refresh_command = pipeline_module._refresh_command(config)
    enrich_command = pipeline_module._tdx_enrich_command(config)

    assert refresh_command[refresh_command.index("--python") + 1] == "python3.11"
    assert enrich_command[enrich_command.index("--python") + 1] == "python3.11"


def test_daily_pipeline_prefers_runner_python_for_tdx_bridge_when_eltdx_is_installed(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        pipeline_module,
        "_python_can_import_eltdx",
        lambda executable: executable == "/opt/stock-ts/.venv/bin/python",
    )
    config = DailyPipelineConfig(python_executable="/opt/stock-ts/.venv/bin/python")

    refresh_command = pipeline_module._refresh_command(config)

    assert refresh_command[refresh_command.index("--python") + 1] == (
        "/opt/stock-ts/.venv/bin/python"
    )


def test_daily_pipeline_writes_data_chain_artifact_and_degrades_on_skipped_steps(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "tdx_snapshots.json"
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n603278,大业股份,100,10,高端装备,测试\n",
        encoding="utf-8",
    )
    _write_snapshot(snapshot)

    def runner(command: list[str], timeout_seconds: int) -> None:
        if any("run_daily_analysis.py" in item for item in command):
            out_dir = Path(command[command.index("--output-dir") + 1])
            html_dir = Path(command[command.index("--html-dir") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            html_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "latest.status").write_text("status=ok\n", encoding="utf-8")
            (out_dir / "latest.md").write_text("# report", encoding="utf-8")
            (html_dir / "latest.html").write_text("<html></html>", encoding="utf-8")

    result = run_daily_pipeline(
        DailyPipelineConfig(
            snapshot_path=snapshot,
            holdings_path=holdings,
            output_dir=tmp_path / "reports" / "daily",
            html_dir=tmp_path / "reports" / "html",
            announcement_dir=tmp_path / "reports" / "announcements",
            skip_refresh=True,
            skip_tdx_enrich=True,
            skip_a_share_kline=True,
            skip_external_enrich=True,
            skip_announcements=True,
        ),
        runner=runner,
    )

    assert result.ok is True
    status = result.status_path.read_text(encoding="utf-8")
    assert "status=degraded" in status
    assert "data_chain=warn" in status
    artifact = tmp_path / "reports" / "daily" / "data_chain_status.json"
    assert artifact.exists()
    chain = json.loads(artifact.read_text(encoding="utf-8"))
    assert chain["modules"]["automation"]["status"] == "warn"
