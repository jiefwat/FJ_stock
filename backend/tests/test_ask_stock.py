from datetime import UTC, date, datetime, timedelta

import pytest

from marketdesk.analysis.ask_stock import (
    AmbiguousStockQuestion,
    StockQuestionNotFound,
    build_stock_answer,
    classify_stock_question,
    resolve_stock_question,
)
from marketdesk.analysis.stock import analyse_stock
from marketdesk.models import Bar, EquityQuote


def quotes() -> list[EquityQuote]:
    return [
        EquityQuote(
            symbol="SH.600519",
            code="600519",
            name="贵州茅台",
            price=1500,
            change_pct=1.2,
            amount=2_000_000_000,
            turnover_rate=0.8,
            volume_ratio=1.1,
            pe=23,
            pb=7,
            market_cap=1_900_000_000_000,
            net_flow=80_000_000,
            sector="白酒",
        ),
        EquityQuote(
            symbol="SZ.000858",
            code="000858",
            name="五粮液",
            price=130,
            change_pct=-0.4,
            amount=1_100_000_000,
            turnover_rate=1.1,
            pe=18,
            pb=4,
            market_cap=500_000_000_000,
            net_flow=-20_000_000,
            sector="白酒",
        ),
    ]


def dossier():
    start = date(2026, 1, 1)
    bars = [
        Bar(
            date=start + timedelta(days=index),
            open=100 + index,
            high=102 + index,
            low=99 + index,
            close=101 + index,
            volume=1000 + index,
            amount=10_000 + index,
        )
        for index in range(70)
    ]
    return analyse_stock(
        quotes()[0],
        bars,
        research_evidence=["公告显示经营保持稳定", "研报关注渠道库存"],
        peer_quotes=quotes(),
    )


def test_resolves_one_stock_by_code_or_name() -> None:
    assert resolve_stock_question("600519 的趋势怎么样", quotes()).symbol == "SH.600519"
    assert resolve_stock_question("贵州茅台主要风险", quotes()).symbol == "SH.600519"


def test_requires_exactly_one_local_stock() -> None:
    with pytest.raises(StockQuestionNotFound):
        resolve_stock_question("低估值白酒股", quotes())
    with pytest.raises(AmbiguousStockQuestion):
        resolve_stock_question("贵州茅台和五粮液哪个更好", quotes())


@pytest.mark.parametrize(
    ("question", "intent"),
    [
        ("贵州茅台有哪些风险", "risk"),
        ("贵州茅台技术趋势怎么样", "trend"),
        ("贵州茅台估值贵不贵", "valuation"),
        ("贵州茅台仓位和止损怎么定", "action"),
        ("贵州茅台怎么样", "overview"),
    ],
)
def test_classifies_question_intent(question: str, intent: str) -> None:
    assert classify_stock_question(question) == intent


@pytest.mark.parametrize("intent", ["risk", "trend", "valuation", "action", "overview"])
def test_builds_bounded_evidence_answer_for_each_intent(intent: str) -> None:
    observed_at = datetime(2026, 7, 25, 1, tzinfo=UTC)
    answer = build_stock_answer(
        question="贵州茅台怎么样",
        intent=intent,
        dossier=dossier(),
        observed_at=observed_at,
    )

    assert answer.kind == "stock_analysis"
    assert answer.symbol == "SH.600519"
    assert answer.name == "贵州茅台"
    assert answer.intent == intent
    assert answer.answer
    assert answer.observed_at == observed_at
    assert 1 <= len(answer.evidence) <= 5
    assert len(answer.risks) <= 4
    assert len(answer.next_actions) <= 4
    assert answer.source == "本地行情快照 + 确定性分析"
    assert answer.disclaimer == "研究辅助信息，不构成投资建议。"


def test_risk_answer_uses_existing_risk_evidence() -> None:
    stock = dossier()
    answer = build_stock_answer(
        question="贵州茅台主要风险是什么",
        intent="risk",
        dossier=stock,
        observed_at=datetime(2026, 7, 25, 1, tzinfo=UTC),
    )

    assert answer.risks == [*stock.bear_case, *stock.invalidation][:4]
    assert any(item in answer.answer for item in stock.bear_case[:2])
