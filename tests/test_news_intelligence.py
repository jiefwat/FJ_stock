from stock_ts.news_intelligence import (
    IntelligenceItem,
    IntelligenceSource,
    classify_news_item,
    dedupe_items_by_url,
    fetch_json_intelligence_sources,
)


def test_classify_news_item_detects_risk_and_catalyst_tags() -> None:
    risk = classify_news_item("公司遭监管处罚并提示业绩下滑", "控股股东质押比例上升")
    catalyst = classify_news_item("商业航天订单增长，机器人业务签订大单", "公司回购股份")

    assert risk.sentiment == "negative"
    assert {"监管处罚", "业绩下滑", "股权质押"}.issubset(set(risk.risk_tags))
    assert catalyst.sentiment == "positive"
    assert {"商业航天", "机器人", "订单", "回购"}.issubset(set(catalyst.catalyst_tags))


def test_dedupe_items_by_url_keeps_first_concrete_item() -> None:
    items = [
        IntelligenceItem(title="AI算力订单", source="财联社", url="https://n/1"),
        IntelligenceItem(title="重复标题", source="其他", url="https://n/1"),
        IntelligenceItem(title="无链接标题", source="快讯", url=""),
        IntelligenceItem(title="无链接标题", source="另一个源", url=""),
    ]

    deduped = dedupe_items_by_url(items)

    assert [item.title for item in deduped] == ["AI算力订单", "无链接标题"]


def test_fetch_json_intelligence_sources_is_fail_open_and_classifies_items() -> None:
    def opener(url: str, timeout: float) -> bytes:
        if "bad" in url:
            raise TimeoutError("boom")
        payload = {
            "items": [
                {
                    "title": "AI算力订单增长",
                    "summary": "公司回购",
                    "url": "https://n/ai",
                    "published_at": "2026-07-08 09:00:00",
                }
            ]
        }
        import json

        return json.dumps(payload).encode()

    result = fetch_json_intelligence_sources(
        [
            IntelligenceSource(id="bad", name="坏源", url="https://bad.example/news"),
            IntelligenceSource(id="good", name="好源", url="https://good.example/news"),
        ],
        opener=opener,
    )

    assert len(result.items) == 1
    assert result.items[0].sentiment == "positive"
    assert result.source_statuses["bad"].startswith("failed:")
    assert result.source_statuses["good"] == "ok:1"


def test_classify_news_item_ignores_negated_catalyst_and_regulator_context() -> None:
    ai_denial = classify_news_item("太龙股份：公司不直接开展物理AI相关产品研发", "主营半导体分销")
    regulator_context = classify_news_item(
        "香港保险业监管局向顺丰控股自保公司发牌", "用于企业内部风险管理"
    )
    real_regulatory_risk = classify_news_item("公司被证监会立案并收到监管处罚", "涉嫌信息披露违法")

    assert ai_denial.sentiment == "neutral"
    assert "AI算力" not in ai_denial.catalyst_tags
    assert regulator_context.sentiment == "neutral"
    assert regulator_context.risk_tags == []
    assert real_regulatory_risk.sentiment == "negative"
    assert "监管处罚" in real_regulatory_risk.risk_tags


def test_market_relevance_filters_generic_world_news_but_keeps_a_share_and_theme_news() -> None:
    from stock_ts.news_intelligence import is_market_relevant_news

    assert not is_market_relevant_news("民调：不到两成美国人信任美国联邦政府", "")
    assert is_market_relevant_news("A股午评：创业板指半日涨近1%，半导体走强", "")
    assert is_market_relevant_news("科创50指数半日涨超3% 算力租赁产业链走强", "")


def test_market_relevance_filters_foreign_and_public_welfare_noise() -> None:
    from stock_ts.news_intelligence import is_market_relevant_news

    assert not is_market_relevant_news("特朗普重要票仓利益受损：数据中心推高美国能源成本", "")
    assert not is_market_relevant_news("韩国交易所对KOSPI指数启动熔断机制", "")
    assert not is_market_relevant_news("奇瑞汽车捐赠价值1000万元现金和物资驰援灾区", "")
    assert is_market_relevant_news("科创50指数半日涨超3% 半导体产业链集体走强", "")
    assert is_market_relevant_news("港股持续走高 恒生科技指数涨超4%", "")


def test_classify_news_item_marks_market_drawdown_as_negative() -> None:
    drawdown = classify_news_item("韩国KOSPI指数跌幅扩大至5%并触发熔断", "市场波动风险上升")

    assert drawdown.sentiment == "negative"
    assert "市场下跌" in drawdown.risk_tags


def test_market_relevance_filters_foreign_broker_target_price_noise() -> None:
    from stock_ts.news_intelligence import is_market_relevant_news

    assert not is_market_relevant_news("摩根大通将通用汽车目标价从98美元上调至110美元", "")
    assert is_market_relevant_news("百度旗下基金入股智元机器人旗下觅蜂科技", "")
