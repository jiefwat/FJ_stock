from __future__ import annotations

from stock_ts.research_run_card import build_research_run_card, render_research_run_card_markdown

DAILY = """# StockTS 每日深度复盘（2026-07-08）

## 深度结论
- 市场震荡，先处理持仓风险，不追高。

## 每日大盘情况
- 上涨 1234，下跌 3100，平盘 188，涨停 26，跌停 64
- 市场状态：防守退潮

## 板块情况
- 商业航天、通用设备、白酒相对强
- 高位题材分歧加大

## 每日持仓分析
## 组合健康度
- 健康度：46/100

## 持仓明细
- 甬矽电子（688362）：市值 54360.00，仓位 11.4%，盈亏 19019.60（53.82%），趋势 下降趋势，风险 高
- 润建股份（002929）：市值 55192.00，仓位 11.6%，盈亏 -5837.12（-9.56%），趋势 下降趋势，风险 中
- 蓝色光标（300058）：市值 46200.00，仓位 9.7%，盈亏 -10477.95（-18.49%），趋势 上升趋势，风险 低

## 个股深度观察
- 甬矽电子（688362）：47/100，当前信号不足或风险约束较多，优先观察而非进攻。
- 润建股份（002929）：35/100，当前信号不足或风险约束较多，优先观察而非进攻。

## 候选股票池摘要
## 候选股票
1. 迈赫股份（301199，外骨骼机器人）：观察分 90/100，最新价 21.28，日涨跌 20.02%
   - 入选理由：外骨骼机器人强度 100/100；收盘价位于短期均线上方
   - 风险提示：短线涨幅较大，次日追高风险上升
   - 观察条件：高开超过 3% 不追，等回落承接
2. 泰胜风能（300129，风电）：观察分 88/100，最新价 10.63，日涨跌 19.98%
   - 入选理由：风电强度 100/100；近期量能放大
   - 风险提示：一字板后分歧可能加大
   - 观察条件：只接受回踩不破 5 日线
"""


def test_research_run_card_turns_daily_report_into_auditable_tasks() -> None:
    card = build_research_run_card(
        DAILY,
        pipeline_status="status=ok\nexternal_enrich=partial:news_missing\nreport=ok\n",
    )

    assert card.title == "盘前研究运行卡"
    assert card.trade_date == "2026-07-08"
    assert card.mission.startswith("市场震荡")
    assert card.risk_budget == "5成以内"
    assert card.data_contract == "部分可信"
    assert [task.name for task in card.tasks] == [
        "市场状态确认",
        "持仓风险处置",
        "机会池验证",
        "数据质量闸门",
    ]
    portfolio_task = card.tasks[1]
    assert portfolio_task.priority == "P0"
    assert "甬矽电子" in "；".join(portfolio_task.evidence)
    assert "润建股份" in "；".join(portfolio_task.evidence)
    assert "先处理高风险/下降趋势持仓" in portfolio_task.action
    opportunity_task = card.tasks[2]
    assert "迈赫股份" in "；".join(opportunity_task.evidence)
    assert "不追高" in opportunity_task.guardrail
    assert card.shadow_account_policy == "只读研究和纸面推演；不接真实下单、不保存券商交易凭证。"


def test_research_run_card_markdown_is_short_and_mobile_readable() -> None:
    card = build_research_run_card(DAILY, pipeline_status="status=ok\nreport=ok\n")
    markdown = render_research_run_card_markdown(card)

    assert "## 研究运行卡" in markdown
    assert "目标：市场震荡" in markdown
    assert "数据：可信" in markdown
    assert "Shadow Account" in markdown
    assert "只读研究和纸面推演" in markdown
    assert "P0｜持仓风险处置" in markdown
    assert all(len(line) <= 170 for line in markdown.splitlines())
