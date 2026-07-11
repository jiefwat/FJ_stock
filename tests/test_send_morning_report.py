from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "send_morning_report", Path("scripts/send_morning_report.py")
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["send_morning_report"] = module
    spec.loader.exec_module(module)
    return module


def _section_lines(content: str, start_heading: str, end_heading: str) -> list[str]:
    start = content.index(start_heading)
    end = content.index(end_heading, start)
    return [
        line
        for line in content[start:end].splitlines()
        if line.startswith("- ") or re.match(r"^\d+[.、]\s", line)
    ]


def test_build_morning_report_combines_latest_artifacts(tmp_path: Path) -> None:
    module = _load_module()
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    (daily_dir / "latest.md").write_text(
        "# StockTS 每日深度复盘（2026-06-26）\n\n"
        "## 深度结论\n- 市场防守\n- 候选：20 只观察票\n\n"
        "## 每日大盘情况\n- 上证指数震荡，短线热度偏低\n\n"
        "## 板块情况\n- 商业航天、通用设备相对活跃\n\n"
        "## 持仓分析\n- 持仓先控风险，再看修复\n\n"
        "## 候选股票池摘要\n1. 测试股票：观察分 88/100\n",
        encoding="utf-8",
    )
    (daily_dir / "pipeline.status").write_text(
        "status=ok\nrefresh=ok\nexternal_enrich=failed:timeout\nannouncements=ok\nreport=ok\n",
        encoding="utf-8",
    )
    (announcement_dir / "latest.md").write_text(
        "# StockTS 公告事件快照\n\n## 603278\n- 返回公告：3\n- 风险事件：1\n",
        encoding="utf-8",
    )

    content = module.build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
        site_url="https://stock.example.com",
    )

    assert "早间简报（地铁版" in content
    assert "市场防守" in content
    assert "昨天大盘总结" in content
    assert "上证指数震荡" in content
    assert "今日市场机会" in content
    assert "商业航天" in content
    assert "我的持仓" in content
    assert "持仓先控风险" in content
    assert "测试股票" in content
    assert "数据与风险提示" in content
    assert "新闻/资金仍需补强" in content
    assert "公告：" in content
    assert "内容仅用于研究复盘" in content


def test_build_morning_report_is_commuter_readable_not_ops_log(tmp_path: Path) -> None:
    module = _load_module()
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    (daily_dir / "latest.md").write_text(
        "# StockTS 每日深度复盘（2026-06-26）\n\n"
        "## 深度结论\n- 防守退潮，先控仓位\n- 持仓优先处理弱势票\n\n"
        "## 每日大盘情况\n- 上涨 1234，下跌 3100，涨停 26，跌停 64\n"
        "- 热度 16/100，短线风险高\n\n"
        "## 板块情况\n- 商业航天、通用设备、白酒相对强\n"
        "- 高位题材分歧加大\n\n"
        "## 持仓分析\n- 组合健康度 46/100\n"
        "- 蓝色光标、大业股份、甬矽电子优先复核\n\n"
        "## 候选股票池摘要\n1. 测试股票：观察分 88/100，理由：板块共振\n\n"
        "# 候选股票池 Top 20（2026-06-26）\n\n"
        "免责声明：这部分不应该被塞进晨报机会摘要。\n",
        encoding="utf-8",
    )
    (daily_dir / "pipeline.status").write_text(
        "status=ok\n"
        "generated_at=2026-06-28T13:45:06\n"
        "codes=603278,688362,603268,300058,06088,600481,300516,000560,002383,002929\n"
        "refresh=ok\n"
        "a_share_kline=failed:subprocess.CalledProcessError: "
        "Command '['python'] returned non-zero exit status 2.\n"
        "external_enrich=failed:subprocess.TimeoutExpired: "
        "Command '['python'] timed out\n"
        "report=ok\n",
        encoding="utf-8",
    )
    (announcement_dir / "latest.md").write_text(
        "# StockTS 公告事件快照\n\n## 603278\n- 返回公告：3\n- 风险事件：1\n",
        encoding="utf-8",
    )

    content = module.build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
        site_url="https://stock.example.com",
    )

    assert "## 昨天大盘总结" in content
    assert "## 我的持仓" in content
    assert "## 投资建议 15只票" in content
    assert "测试股票" in content
    assert "免责声明：这部分不应该" not in content
    assert "网站：" not in content
    assert "HTML 报告" not in content
    assert "Markdown 报告" not in content
    assert "codes=" not in content
    assert "subprocess." not in content
    assert "Command '['" not in content
    assert "部分K线失败" in content
    assert all(len(line) <= 220 for line in content.splitlines())


def test_morning_report_names_stocks_risks_and_today_actions(tmp_path: Path) -> None:
    module = _load_module()
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    (daily_dir / "latest.md").write_text(
        "# StockTS 每日深度复盘（2026-06-26）\n\n"
        "## 深度结论\n- 市场防守，今天先控仓，不追高\n\n"
        "## 每日大盘情况\n"
        "- 上涨 1234，下跌 3100，平盘 188，涨停 26，跌停 64\n"
        "- 市场状态：防守退潮\n"
        "- 明日观察：若跌停继续扩散，降低仓位\n\n"
        "## 板块情况\n"
        "- 商业航天、通用设备、白酒相对强\n\n"
        "## 每日持仓分析\n"
        "## 持仓明细\n"
        "- 大业股份（603278）：市值 50160.00，仓位 10.7%，"
        "盈亏 12015.20（31.50%），趋势 下降趋势，风险 高\n"
        "- 甬矽电子（688362）：市值 43790.00，仓位 9.3%，"
        "盈亏 8449.60（23.91%），趋势 下降趋势，风险 高\n"
        "- 蓝色光标（300058）：市值 53375.00，仓位 11.3%，"
        "盈亏 -3302.95（-5.83%），趋势 上升趋势，风险 低\n\n"
        "## 风险提示\n"
        "- 单票波动偏大，先处理下降趋势高风险票\n\n"
        "## 明日强势候选观察池 Top 20\n"
        "## 候选观察票\n"
        "1. 兆易创新（300000，半导体）：观察分 100/100，最新价 18.00，日涨跌 1.04%\n"
        "   - 入选理由：半导体强度 100/100；资金净流入\n"
        "   - 风险提示：等待次日确认\n"
        "   - 观察条件：竞价不明显弱于板块龙头\n"
        "2. 北方华创（600001，机器人）：观察分 99/100，最新价 19.70，日涨跌 -0.96%\n"
        "   - 入选理由：机器人板块共振\n"
        "   - 风险提示：回落需止损\n"
        "   - 观察条件：股价不快速跌破 5 日均线\n"
        "3. 中微公司（600002，人工智能）：观察分 98/100，最新价 21.40，日涨跌 1.05%\n"
        "   - 入选理由：人工智能主线\n"
        "   - 风险提示：高位分歧\n"
        "   - 观察条件：开盘承接强\n"
        "4. 机器人A（300003，算力）：观察分 97/100，最新价 23.10，日涨跌 1.04%\n"
        "   - 入选理由：算力放量\n"
        "   - 风险提示：缩量回落\n"
        "   - 观察条件：不追高\n"
        "5. 绿的谐波（600004，新能源车）：观察分 96/100，最新价 24.80，日涨跌 0.93%\n"
        "   - 入选理由：板块修复\n"
        "   - 风险提示：延续性待确认\n"
        "   - 观察条件：回踩不破\n"
        "6. 浪潮信息（600008，半导体）：观察分 95/100，最新价 31.60，日涨跌 1.04%\n"
        "   - 入选理由：趋势共振\n"
        "   - 风险提示：估值偏高\n"
        "   - 观察条件：成交额维持\n"
        "7. 中际旭创（300009，机器人）：观察分 94/100，最新价 33.30，日涨跌 1.04%\n"
        "   - 入选理由：资金抱团\n"
        "   - 风险提示：高位震荡\n"
        "   - 观察条件：板块延续\n"
        "8. 新易盛（600010，人工智能）：观察分 93/100，最新价 35.00，日涨跌 1.04%\n"
        "   - 入选理由：消息催化\n"
        "   - 风险提示：利好兑现\n"
        "   - 观察条件：放量承接\n"
        "9. 天孚通信（600011，算力）：观察分 92/100，最新价 36.70，日涨跌 -0.96%\n"
        "   - 入选理由：主线低吸\n"
        "   - 风险提示：弱于板块\n"
        "   - 观察条件：不破均线\n"
        "10. 中信证券（600016，证券）：观察分 91/100，最新价 45.20，日涨跌 -0.96%\n"
        "   - 入选理由：指数修复弹性\n"
        "   - 风险提示：大盘走弱\n"
        "   - 观察条件：指数放量\n",
        encoding="utf-8",
    )
    (daily_dir / "pipeline.status").write_text(
        "status=ok\ngenerated_at=2026-06-27T18:30:00\nrefresh=ok\nreport=ok\nannouncements=ok\n",
        encoding="utf-8",
    )
    (announcement_dir / "latest.md").write_text(
        "# StockTS 公告事件快照\n\n"
        "## 603278\n- 返回公告：5\n- 风险事件：2\n\n"
        "## 688362\n- 返回公告：5\n- 风险事件：0\n",
        encoding="utf-8",
    )

    content = module.build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
        site_url="https://stock.example.com",
    )

    assert "## 昨天大盘总结" in content
    assert "## 我的持仓" in content
    assert "大业股份：判断：锁利润" in content
    assert "甬矽电子：判断：锁利润" in content
    assert "蓝色光标：判断：持有观察" in content
    assert "风险：趋势 下降趋势，风险 高" in content
    assert "动作：不加仓" in content
    assert "禁忌：不补仓摊低" in content
    assert "## 投资建议 15只票" in content
    assert "1. 兆易创新" in content
    assert "10. 中信证券" in content
    assert "## 数据与风险提示" in content
    assert "大业股份：风险：公告风险 2 条" in content
    assert "返回公告" not in content
    assert "风险事件" not in content
    assert "## 603278" not in content


def test_morning_report_extracts_ten_opportunities_from_candidate_stock_heading(
    tmp_path: Path,
) -> None:
    module = _load_module()
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    candidates = []
    for index in range(1, 11):
        candidates.append(f"{index}. 测试股票{index}（6000{index:02d}，测试板块）：观察分 90/100")
        candidates.append("   - 入选理由：板块共振")
        candidates.append("   - 风险提示：等待确认")
        candidates.append("   - 观察条件：开盘承接强")
    (daily_dir / "latest.md").write_text(
        "# StockTS 每日深度复盘（2026-06-26）\n\n"
        "## 深度结论\n- 市场防守\n\n"
        "## 每日大盘情况\n- 大盘偏弱\n\n"
        "## 候选股票池摘要\n"
        "# 候选股票池 Top 20（2026-06-26）\n\n"
        "## 候选股票\n" + "\n".join(candidates),
        encoding="utf-8",
    )

    content = module.build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
    )

    assert "1. 测试股票1" in content
    assert "10. 测试股票10" in content
    assert "- 入选理由" not in content


def test_send_morning_report_uses_dispatcher_with_email_channel(tmp_path: Path) -> None:
    module = _load_module()
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    (daily_dir / "latest.md").write_text("# report\n\n## 深度结论\n- ok\n", encoding="utf-8")
    calls = []

    def fake_dispatch(
        content: str, *, channels: list[str], subject: str, dry_run: bool, style: str
    ):
        calls.append((content, channels, subject, dry_run, style))
        return module.SendResult(ok=True, markdown="# ok\n")

    result = module.send_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
        channels=["email"],
        dry_run=True,
        style="digest",
        dispatcher=fake_dispatch,
    )

    assert result.ok is True
    assert calls[0][1] == ["email"]
    assert calls[0][3] is True
    assert calls[0][4] == "digest"
    assert "StockTS 早间简报" in calls[0][2]


def test_send_morning_report_passes_personal_holdings_path(monkeypatch, tmp_path: Path) -> None:
    module = _load_module()
    calls = []

    def fake_build(**kwargs):  # noqa: ANN003, ANN202
        calls.append(kwargs)
        return "# report\n"

    def fake_dispatch(
        content: str, *, channels: list[str], subject: str, dry_run: bool, style: str
    ):
        return module.SendResult(ok=True, markdown="# ok\n")

    monkeypatch.setattr(module, "build_morning_report", fake_build)
    holdings_path = tmp_path / "user-data" / "2" / "holdings.csv"

    result = module.send_morning_report(
        holdings_path=holdings_path,
        channels=["email"],
        dry_run=True,
        dispatcher=fake_dispatch,
    )

    assert result.ok is True
    assert calls[0]["holdings_path"] == holdings_path


def test_main_skips_successfully_when_email_is_missing(monkeypatch, tmp_path: Path, capsys) -> None:
    module = _load_module()
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()

    class MissingEmailSettings:
        email_sender = ""
        email_password = ""

    monkeypatch.setattr(module, "get_settings", lambda: MissingEmailSettings())

    code = module.main(
        [
            "--daily-dir",
            str(daily_dir),
            "--html-dir",
            str(html_dir),
            "--announcement-dir",
            str(announcement_dir),
            "--channels",
            "email",
            "--skip-if-email-missing",
        ]
    )

    output = capsys.readouterr().out
    assert code == 0
    assert "邮箱未配置" in output


def test_morning_report_prioritizes_professional_actions_over_generic_summary(
    tmp_path: Path,
) -> None:
    module = _load_module()
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    (daily_dir / "latest.md").write_text(
        "# StockTS 每日深度复盘（2026-07-03）\n\n"
        "## 深度结论\n- 市场偏强，但组合不跟主线，今天只处理风险和确认机会\n\n"
        "## 每日大盘情况\n"
        "- 市场偏强，赚钱效应扩散\n"
        "- 涨跌家数比 2.34\n\n"
        "## 板块情况\n"
        "- 新能源车\n- 外骨骼机器人\n- PCB概念\n\n"
        "## 每日持仓分析\n"
        "## 组合健康度\n"
        "- 健康度：54/100\n"
        "- 浮动盈亏：-34967.19（-6.84%）\n\n"
        "## 持仓明细\n"
        "- 甬矽电子（688362）：市值 54360.00，仓位 11.4%，"
        "盈亏 19019.60（53.82%），趋势 下降趋势，风险 高\n"
        "- 润建股份（002929）：市值 55192.00，仓位 11.6%，"
        "盈亏 -5837.12（-9.56%），趋势 下降趋势，风险 中\n"
        "- 双良节能（600481）：市值 50903.00，仓位 10.7%，"
        "盈亏 -5839.13（-10.29%），趋势 下降趋势，风险 中\n"
        "- 大业股份（603278）：市值 48440.00，仓位 10.2%，"
        "盈亏 10295.20（26.99%），趋势 上升趋势，风险 中\n\n"
        "## 候选股票池摘要\n"
        "## 候选股票\n"
        "1. 迈赫股份（301199，外骨骼机器人）：观察分 90/100，最新价 21.28，日涨跌 20.02%\n"
        "   - 入选理由：外骨骼机器人强度 100/100；收盘价位于短期均线上方；近期量能放大\n"
        "   - 风险提示：短线涨幅较大，次日追高风险上升\n"
        "   - 观察条件：高开超过 3% 不追，等回落承接；30 分钟不能跌回开盘价\n"
        "2. 泰胜风能（300129，风电）：观察分 90/100，最新价 10.63，日涨跌 19.98%\n"
        "   - 入选理由：风电强度 100/100；收盘价位于短期均线上方\n"
        "   - 风险提示：短线涨幅较大，次日追高风险上升\n"
        "   - 观察条件：只接受回踩不破 5 日线\n",
        encoding="utf-8",
    )
    (daily_dir / "pipeline.status").write_text(
        "status=ok\n"
        "generated_at=2026-07-03T16:18:58\n"
        "refresh=ok\n"
        "a_share_kline=partial:updated 303, failed 6\n"
        "external_enrich=partial:news_missing,moneyflow_missing\n"
        "announcements=ok\n"
        "report=ok\n",
        encoding="utf-8",
    )
    (announcement_dir / "latest.md").write_text("# 公告\n", encoding="utf-8")

    content = module.build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
    )

    assert "## 我的持仓" in content
    assert "甬矽电子" in content
    assert "润建股份" in content
    assert "双良节能" in content
    assert "不加仓；反弹先降仓/锁利润" in content
    assert "## 投资建议 15只票" in content
    assert "迈赫股份" in content
    assert "泰胜风能" in content
    assert "网页" not in content
    assert "去系统" not in content
    assert "数据缺口：新闻/资金仍需补强" in content
    assert "subprocess" not in content


def test_morning_report_adds_portfolio_layers_and_position_advice(tmp_path: Path) -> None:
    module = _load_module()
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    (daily_dir / "latest.md").write_text(
        "# StockTS 每日深度复盘（2026-07-06）\n\n"
        "## 深度结论\n- 市场震荡，先控仓位和问题股\n\n"
        "## 每日大盘情况\n- 市场震荡，结构性机会为主\n\n"
        "## 每日持仓分析\n"
        "## 组合健康度\n"
        "- 健康度：46/100\n"
        "- 浮动盈亏：-42000.00（-8.20%）\n\n"
        "## 持仓明细\n"
        "- 甬矽电子（688362）：市值 54360.00，仓位 11.4%，"
        "盈亏 19019.60（53.82%），趋势 下降趋势，风险 高\n"
        "- 润建股份（002929）：市值 55192.00，仓位 11.6%，"
        "盈亏 -5837.12（-9.56%），趋势 下降趋势，风险 中\n"
        "- 蓝色光标（300058）：市值 46200.00，仓位 9.7%，"
        "盈亏 -10477.95（-18.49%），趋势 上升趋势，风险 低\n"
        "- 大业股份（603278）：市值 48440.00，仓位 10.2%，"
        "盈亏 10295.20（26.99%），趋势 上升趋势，风险 中\n",
        encoding="utf-8",
    )
    (daily_dir / "pipeline.status").write_text(
        "status=ok\nrefresh=ok\nexternal_enrich=failed:timeout\nreport=ok\n",
        encoding="utf-8",
    )
    (announcement_dir / "latest.md").write_text("# 公告\n", encoding="utf-8")

    content = module.build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
    )

    assert "## 研究运行卡" not in content
    assert "Shadow Account" not in content
    assert "P0｜持仓风险处置" not in content
    assert "## 我的持仓" in content
    assert "甬矽电子" in content
    assert "润建股份" in content
    assert "蓝色光标" in content
    assert "大业股份" in content
    assert "新闻/资金仍需补强" in content


def test_morning_report_compresses_opportunities_for_phone_reading(tmp_path: Path) -> None:
    module = _load_module()
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    (daily_dir / "latest.md").write_text(
        "# StockTS 每日深度复盘（2026-07-06）\n\n"
        "## 深度结论\n- 市场偏强\n\n"
        "## 候选股票池摘要\n"
        "## 候选股票\n"
        "1. 迈赫股份（301199，外骨骼机器人）：观察分 90/100，最新价 21.28，日涨跌 20.02%\n"
        "   - 入选理由：迈赫股份所在外骨骼机器人强度 100/100；"
        "迈赫股份收盘价位于短期均线上方；迈赫股份近期量能放大，关注承接\n"
        "   - 风险提示：短线涨幅较大，次日追高风险上升；近期波动偏高\n"
        "   - 观察条件：迈赫股份高开超过 3% 不追，等回落承接；"
        "迈赫股份放量后 30 分钟不能跌回开盘价\n",
        encoding="utf-8",
    )

    content = module.build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
    )

    assert "1. 迈赫股份｜外骨骼机器人｜" in content
    assert "观察分" not in content
    assert "迈赫股份所在" not in content
    opportunity_lines = [line for line in content.splitlines() if line.startswith("1. 迈赫股份")]
    assert opportunity_lines
    assert len(opportunity_lines[0]) <= 150


def test_morning_report_uses_stock_decision_summary_for_holdings(tmp_path: Path) -> None:
    module = _load_module()
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    (daily_dir / "latest.md").write_text(
        "# StockTS 每日深度复盘（2026-07-08）\n\n"
        "## 深度结论\n- 市场震荡，先处理持仓风险\n\n"
        "## 每日持仓分析\n"
        "## 持仓明细\n"
        "- 甬矽电子（688362）：市值 54360.00，仓位 11.4%，"
        "盈亏 19019.60（53.82%），趋势 下降趋势，风险 高\n"
        "- 润建股份（002929）：市值 55192.00，仓位 11.6%，"
        "盈亏 -5837.12（-9.56%），趋势 下降趋势，风险 中\n\n"
        "## 个股分析\n\n"
        "# 个股分析：甬矽电子（688362）\n\n"
        "## 决策摘要\n"
        "- 最终判断：降风险\n"
        "- 核心矛盾：资金行为偏弱：主力资金净流出 2.40 亿元；"
        "估值基本面偏弱：PE(TTM) 96.00，估值偏高\n"
        "- 今日动作：不加仓；反弹先处理风险，等趋势和资金修复后再看。\n"
        "- 不能做什么：不能补仓摊低；不能因为跌多了就买。\n"
        "- 转强条件：站回并稳住 MA5 32.50；资金由流出转为流入\n"
        "- 离场条件：跌破 30.88 或继续放量下跌，优先降风险。\n"
        "- 数据可信度：部分可信\n\n"
        "# 个股分析：润建股份（002929）\n\n"
        "## 决策摘要\n"
        "- 最终判断：防守观察\n"
        "- 核心矛盾：技术趋势偏弱：下降趋势，单日涨跌 -2.10%\n"
        "- 今日动作：不加仓；先等重新站回短期均线并出现资金回流。\n"
        "- 不能做什么：不能补仓摊低；不能忽略资金流出。\n"
        "- 转强条件：站回并稳住 MA5 70.20；放量不跌回开盘价\n"
        "- 离场条件：跌破 66.50 且 30 分钟不能收回，降低观察优先级。\n"
        "- 数据可信度：低可信\n",
        encoding="utf-8",
    )
    (daily_dir / "pipeline.status").write_text("status=ok\nreport=ok\n", encoding="utf-8")
    (announcement_dir / "latest.md").write_text("# 公告\n", encoding="utf-8")

    content = module.build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
    )

    assert "甬矽电子：判断：降风险" in content
    assert "动作：不加仓；反弹先处理风险" in content
    assert "风险：资金行为偏弱" in content
    assert "禁忌：不能补仓摊低" in content
    assert "离场：跌破 30.88" in content
    assert "润建股份：判断：防守观察" in content
    assert "趋势 下降趋势、风险 高" not in content
    holding_lines = _section_lines(content, "## 我的持仓", "## 今日市场机会")
    assert holding_lines
    assert all(len(line) <= 170 for line in holding_lines)


def test_morning_report_falls_back_to_deep_stock_observation_for_holdings(tmp_path: Path) -> None:
    module = _load_module()
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    (daily_dir / "latest.md").write_text(
        "# StockTS 每日深度复盘（2026-07-08）\n\n"
        "## 持仓分析\n"
        "- 弱势或高风险持仓：甬矽电子、润建股份\n\n"
        "## 每日持仓分析\n"
        "## 持仓明细\n"
        "- 甬矽电子（688362）：市值 54360.00，仓位 11.4%，"
        "盈亏 19019.60（53.82%），趋势 下降趋势，风险 高\n"
        "- 润建股份（002929）：市值 55192.00，仓位 11.6%，"
        "盈亏 -5837.12（-9.56%），趋势 下降趋势，风险 中\n\n"
        "## 个股深度观察\n"
        "- 甬矽电子（688362）：47/100，甬矽电子 当前信号不足或风险约束较多，优先观察而非进攻。\n"
        "- 润建股份（002929）：35/100，润建股份 当前信号不足或风险约束较多，优先观察而非进攻。\n",
        encoding="utf-8",
    )
    (daily_dir / "pipeline.status").write_text("status=ok\nreport=ok\n", encoding="utf-8")
    (announcement_dir / "latest.md").write_text("# 公告\n", encoding="utf-8")

    content = module.build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
    )

    assert "甬矽电子：判断：防守观察" in content
    assert "深度分 47/100" in content
    assert "润建股份：判断：降风险" in content
    assert "深度分 35/100" in content
    assert "禁忌：不补仓摊低" in content
    assert "当前信号不足或风险约束较多" not in content
    assert "。；" not in content
    holding_lines = _section_lines(content, "## 我的持仓", "## 今日市场机会")
    assert holding_lines
    assert all(len(line) <= 170 for line in holding_lines)


def test_morning_report_starts_with_commuter_decision_brief(tmp_path: Path) -> None:
    module = _load_module()
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    (daily_dir / "latest.md").write_text(
        "# StockTS 每日深度复盘（2026-07-08）\n\n"
        "## 深度结论\n- 市场震荡，先控风险，只做主线前排观察\n\n"
        "## 每日大盘情况\n- 上涨 2100 / 下跌 2800 / 平盘 120，市场热度 48/100\n\n"
        "## 板块情况\n- 商业航天强，白酒弱\n\n"
        "## 每日持仓分析\n"
        "## 组合健康度\n- 健康度：46/100\n\n"
        "## 持仓明细\n"
        "- 甬矽电子（688362）：市值 54360.00，仓位 11.4%，"
        "盈亏 19019.60（53.82%），趋势 下降趋势，风险 高\n"
        "- 润建股份（002929）：市值 55192.00，仓位 11.6%，"
        "盈亏 -5837.12（-9.56%），趋势 下降趋势，风险 中\n\n"
        "## 候选股票池摘要\n"
        "## 候选股票\n"
        "1. 航天科技（000901，商业航天）：观察分 88/100\n"
        "   - 入选理由：商业航天强度高，量能放大\n"
        "   - 风险提示：高位分歧\n"
        "   - 观察条件：回踩不破开盘价\n",
        encoding="utf-8",
    )
    (daily_dir / "pipeline.status").write_text(
        "status=ok\nexternal_enrich=failed:timeout\nreport=ok\n",
        encoding="utf-8",
    )
    (announcement_dir / "latest.md").write_text("# 公告\n", encoding="utf-8")

    content = module.build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
    )

    first_block = content.split("## 投资建议 15只票", 1)[0]
    assert "## 昨天大盘总结" in first_block
    assert "## 我的持仓" in first_block
    assert "## 今日市场机会" in first_block
    assert "结论：" in first_block
    assert "盘面：" in first_block
    assert "原则：" in first_block
    assert "甬矽电子" in first_block
    assert "航天科技" in first_block
    assert "网页" not in first_block
    decision_lines = [line for line in first_block.splitlines() if line.startswith("- ")]
    assert decision_lines
    assert all(len(line) <= 150 for line in decision_lines)


def test_morning_report_adds_traffic_light_trade_list_without_duplicate_holdings(
    tmp_path: Path,
) -> None:
    module = _load_module()
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    (daily_dir / "latest.md").write_text(
        "# StockTS 每日深度复盘（2026-07-08）\n\n"
        "## 深度结论\n- 市场震荡，今天只做纪律动作\n\n"
        "## 每日大盘情况\n- 上涨 1800，下跌 3000，跌停 43，市场热度 42/100\n\n"
        "## 每日持仓分析\n"
        "## 持仓明细\n"
        "- 甬矽电子（688362）：市值 54360.00，仓位 11.4%，"
        "盈亏 19019.60（53.82%），趋势 下降趋势，风险 高\n"
        "- 润建股份（002929）：市值 55192.00，仓位 11.6%，"
        "盈亏 -5837.12（-9.56%），趋势 下降趋势，风险 中\n"
        "- 蓝色光标（300058）：市值 46200.00，仓位 9.7%，"
        "盈亏 -10477.95（-18.49%），趋势 上升趋势，风险 低\n"
        "- 大业股份（603278）：市值 48440.00，仓位 10.2%，"
        "盈亏 10295.20（26.99%），趋势 上升趋势，风险 中\n\n"
        "## 候选股票池摘要\n"
        "## 候选股票\n"
        "1. 航天科技（000901，商业航天）：观察分 88/100\n"
        "   - 入选理由：商业航天强度高，量能放大\n"
        "   - 风险提示：高位分歧\n"
        "   - 观察条件：回踩不破开盘价\n",
        encoding="utf-8",
    )
    (daily_dir / "pipeline.status").write_text("status=ok\nreport=ok\n", encoding="utf-8")
    (announcement_dir / "latest.md").write_text("# 公告\n", encoding="utf-8")

    content = module.build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
    )

    assert "## 我的持仓" in content
    trade_lines = _section_lines(content, "## 我的持仓", "## 今日市场机会")
    joined = "\n".join(trade_lines)
    assert "甬矽电子" in joined
    assert "润建股份" in joined
    assert "蓝色光标" in joined
    assert "大业股份" in joined
    assert joined.count("甬矽电子") == 1
    assert joined.count("润建股份") == 1
    assert joined.count("蓝色光标") == 1
    assert joined.count("大业股份") == 1


def test_morning_report_traffic_light_uses_weak_holding_summary_when_details_missing(
    tmp_path: Path,
) -> None:
    module = _load_module()
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    (daily_dir / "latest.md").write_text(
        "# StockTS 每日深度复盘（2026-07-08）\n\n"
        "## 深度结论\n- 市场偏弱，防守优先\n\n"
        "## 持仓分析\n"
        "- 弱势或高风险持仓：甬矽电子、润建股份、大业股份\n"
        "- 大盘环境偏弱，持仓需要降低回撤暴露\n\n"
        "## 候选股票\n"
        "1. 济民健康（603222，未识别主题）：观察分 80/100\n"
        "   - 入选理由：量能放大\n"
        "   - 风险提示：追高风险\n"
        "   - 观察条件：回踩承接\n",
        encoding="utf-8",
    )
    (daily_dir / "pipeline.status").write_text("status=ok\nreport=ok\n", encoding="utf-8")
    (announcement_dir / "latest.md").write_text("# 公告\n", encoding="utf-8")

    content = module.build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
    )

    trade_lines = _section_lines(content, "## 我的持仓", "## 今日市场机会")
    joined = "\n".join(trade_lines)
    assert "甬矽电子、润建股份、大业股份" in joined
    assert "暂无" not in joined


def test_morning_report_prefers_structured_decisions_json(tmp_path: Path) -> None:
    module = _load_module()
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    (daily_dir / "latest.md").write_text(
        "# StockTS 每日深度复盘（2026-07-08）\n\n"
        "## 深度结论\n- Markdown 旧摘要，不应覆盖 JSON\n",
        encoding="utf-8",
    )
    (daily_dir / "latest_decisions.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "trade_date": "2026-07-08",
                "market": {"summary": "结构化大盘：防守优先"},
                "traffic_lights": {
                    "red": [
                        {
                            "name": "甬矽电子",
                            "action": "不加仓；反弹降风险",
                            "reason": "趋势下降，风险高",
                        }
                    ],
                    "yellow": [
                        {"name": "蓝色光标", "action": "等待修复", "reason": "亏损但趋势未坏"}
                    ],
                    "green": [
                        {"name": "大业股份", "action": "持有跟踪", "reason": "盈利且趋势向上"}
                    ],
                },
                "opportunities": [
                    {
                        "name": "济民健康",
                        "sector": "医药",
                        "reason": "量能放大",
                        "risk": "追高风险",
                        "action": "回踩承接",
                    }
                ],
                "data_limits": ["资金面判断不可信"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (daily_dir / "pipeline.status").write_text("status=ok\nreport=ok\n", encoding="utf-8")
    (announcement_dir / "latest.md").write_text("# 公告\n", encoding="utf-8")

    content = module.build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
    )

    assert "结构化大盘：防守优先" in content
    assert "1. 济民健康｜医药｜机会：量能放大；风险：追高风险；动作：回踩承接" in content
    assert "Markdown 旧摘要" not in content.split("## 昨天大盘总结", 1)[0]


def test_morning_report_surfaces_structured_action_limits_and_automation(tmp_path: Path) -> None:
    module = _load_module()
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    (daily_dir / "latest.md").write_text(
        "# StockTS 每日深度复盘（2026-07-08）\n\n## 深度结论\n- 市场震荡\n",
        encoding="utf-8",
    )
    (daily_dir / "latest_decisions.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "trade_date": "2026-07-08",
                "market": {"summary": "市场震荡，先看风险"},
                "traffic_lights": {"red": [], "yellow": [], "green": []},
                "opportunities": [],
                "data_limits": ["资金面判断不可信"],
                "action_limits": ["资金面不可用：不把资金作为买入理由"],
                "automation": {
                    "failed_steps": ["外部补强"],
                    "advice": "外部补强失败，新闻资金只观察",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (daily_dir / "pipeline.status").write_text("status=ok\nreport=ok\n", encoding="utf-8")
    (announcement_dir / "latest.md").write_text("# 公告\n", encoding="utf-8")

    content = module.build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
    )

    assert "## 数据与风险提示" in content
    assert "资金面不可用：不把资金作为买入理由" in content
    assert "外部补强失败，新闻资金只观察" in content


def test_morning_report_surfaces_dual_git_method_chain_from_daily_artifact(tmp_path: Path) -> None:
    module = _load_module()
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    (daily_dir / "latest.md").write_text(
        "# StockTS 每日复盘（2026-07-08）\n\n"
        "## 深度结论\n- 市场震荡\n\n"
        "## 每日板块情况\n- 白酒\n\n"
        "## 板块统一方法链\n"
        "- 白酒：板块方法链：daily_stock_analysis 上下文包：可用 K线、资金；"
        "TradingAgents 板块审议：多空审议：资金改善。\n\n"
        "## 每日持仓分析\n- 贵州茅台（600519）：趋势 上升趋势，风险 低\n\n"
        "## 持仓股票统一方法链\n"
        "- 贵州茅台（600519）：daily_stock_analysis 信号归因：技术 40%；"
        "消息 20%；基本面 20%；资金/成交 20%\n"
        "  - TradingAgents 分析师团队：技术分析师支持\n"
        "  - 多空审议：多头观点明确；空头观点估值约束\n"
        "  - 组合经理最终意见：继续观察。\n",
        encoding="utf-8",
    )
    (daily_dir / "pipeline.status").write_text(
        "status=ok\ngenerated_at=2026-07-08T08:00:00+08:00\n",
        encoding="utf-8",
    )
    (announcement_dir / "latest.md").write_text("# 公告\n", encoding="utf-8")

    content = module.build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
    )

    assert "## 分析方法校验" not in content
    assert "daily_stock_analysis 信号归因" not in content
    assert "TradingAgents" not in content
    assert "## 数据与风险提示" in content


def test_morning_report_is_subway_brief_with_market_holdings_opportunities_and_15_stocks(
    tmp_path: Path,
) -> None:
    module = _load_module()
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    candidate_lines: list[str] = []
    for index in range(1, 16):
        candidate_line = (
            f"{index}. 测试股票{index}（600{index:03d}，测试板块{index % 3}）："
            f"观察分 {90 - index}/100，最新价 {10 + index:.2f}，"
            f"日涨跌 {index / 10:.2f}%"
        )
        candidate_lines.extend(
            [
                candidate_line,
                f"   - 入选理由：主题强度靠前，资金承接第{index}名",
                "   - 风险提示：追高风险，低开需放弃",
                "   - 观察条件：回踩不破且成交额维持",
            ]
        )
    (daily_dir / "latest.md").write_text(
        "# StockTS 每日深度复盘（2026-07-10）\n\n"
        "## 深度结论\n- 市场震荡，主线集中，今天只做强势方向低吸\n\n"
        "## 每日大盘情况\n"
        "- 上涨 2100，下跌 2800，涨停 45，跌停 12\n"
        "- 成交额缩量，指数震荡但题材局部活跃\n\n"
        "## 板块情况\n- CXO概念、海洋经济、国防军工相对强\n\n"
        "## 每日持仓分析\n"
        "## 持仓明细\n"
        "- 大业股份（603278）：市值 50160.00，仓位 10.7%，"
        "盈亏 12015.20（31.50%），趋势 下降趋势，风险 高\n"
        "- 蓝色光标（300058）：市值 53375.00，仓位 11.3%，"
        "盈亏 -3302.95（-5.83%），趋势 上升趋势，风险 低\n\n"
        "## 候选股票池摘要\n## 候选股票\n"
        + "\n".join(candidate_lines),
        encoding="utf-8",
    )
    (daily_dir / "pipeline.status").write_text(
        "status=ok\ngenerated_at=2026-07-10T18:30:00+08:00\nreport=ok\n",
        encoding="utf-8",
    )
    (announcement_dir / "latest.md").write_text("# 公告\n", encoding="utf-8")

    content = module.build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
    )

    assert "## 昨天大盘总结" in content
    assert "## 我的持仓" in content
    assert "## 今日市场机会" in content
    assert "## 投资建议 15只票" in content
    assert content.index("## 昨天大盘总结") < content.index("## 我的持仓")
    assert content.index("## 我的持仓") < content.index("## 今日市场机会")
    assert content.index("## 今日市场机会") < content.index("## 投资建议 15只票")
    suggestion_lines = _section_lines(content, "## 投资建议 15只票", "## 数据与风险提示")
    assert len([line for line in suggestion_lines if line[0].isdigit()]) == 15
    assert "1. 测试股票1" in content
    assert "15. 测试股票15" in content
    assert "红黄绿交易清单" not in content
    assert "分析方法校验" not in content
    assert "自动任务提醒" not in content
    assert "今日交易限制" not in content
    assert all(len(line) <= 220 for line in content.splitlines())


def test_morning_report_fills_15_suggestions_when_decisions_json_has_fewer_items(
    tmp_path: Path,
) -> None:
    module = _load_module()
    daily_dir = tmp_path / "daily"
    html_dir = tmp_path / "html"
    announcement_dir = tmp_path / "announcements"
    daily_dir.mkdir()
    html_dir.mkdir()
    announcement_dir.mkdir()
    candidate_lines: list[str] = []
    for index in range(1, 16):
        candidate_lines.extend(
            [
                f"{index}. 候补股票{index}（600{index:03d}，候补板块）：观察分 80/100",
                "   - 入选理由：板块共振",
                "   - 风险提示：追高风险",
                "   - 观察条件：回踩承接",
            ]
        )
    (daily_dir / "latest.md").write_text(
        "# StockTS 每日深度复盘（2026-07-10）\n\n"
        "## 深度结论\n- 市场震荡\n\n"
        "## 候选股票池摘要\n## 候选股票\n"
        + "\n".join(candidate_lines),
        encoding="utf-8",
    )
    (daily_dir / "latest_decisions.json").write_text(
        json.dumps(
            {
                "trade_date": "2026-07-10",
                "market": {"summary": "结构化大盘"},
                "opportunities": [
                    {
                        "name": "结构票1",
                        "sector": "结构板块",
                        "reason": "JSON 优先",
                        "risk": "追高风险",
                        "action": "回踩承接",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (daily_dir / "pipeline.status").write_text("status=ok\nreport=ok\n", encoding="utf-8")
    (announcement_dir / "latest.md").write_text("# 公告\n", encoding="utf-8")

    content = module.build_morning_report(
        daily_dir=daily_dir,
        html_dir=html_dir,
        announcement_dir=announcement_dir,
    )

    suggestion_lines = _section_lines(content, "## 投资建议 15只票", "## 数据与风险提示")
    numbered = [line for line in suggestion_lines if line[0].isdigit()]
    assert len(numbered) == 15
    assert numbered[0].startswith("1. 结构票1")
    assert any("候补股票14" in line for line in numbered)
