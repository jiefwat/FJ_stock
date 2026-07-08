# daily_stock_analysis 参考落地记录

日期：2026-07-08
参考项目：[ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis)

## 参考结论

本轮没有照搬完整工程，而是吸收两类最适合 StockTS 的设计：

1. 多源行情不再只看“哪个 provider 成功”，而是记录主源、降级源、缺失字段和质量等级。
2. 实时新闻/情报采用 fail-open：单个外部新闻源失败不阻断日报，只把失败状态写入产物。
3. 新闻标题需要先做风险/催化分类，再进入个股事件维度，避免所有分析都变成“新闻若干条”的模板话术。
4. 实时行情预留统一 quote 类型，后续 Tencent、TDX、AKShare、iTick 可按同一结构接入。

## 已落地范围

- `src/stock_ts/data_quality.py`：新增数据源尝试记录、质量摘要和可读格式化。
- `src/stock_ts/realtime_quotes.py`：新增实时 quote 统一模型和 fallback 管理器。
- `src/stock_ts/news_intelligence.py`：新增 JSON 情报源读取、URL 去重、风险/催化分类和 fail-open 状态；已补充否定式催化过滤、监管语境误判过滤和市场相关新闻过滤。
- `scripts/enrich_tdx_snapshot.py`：外部补强时写入 `data_quality`、分类后的个股新闻、市场情报源状态；可跳过可选字段而不把数据质量误判为失败。
- `src/stock_ts/providers/tdx_snapshot_provider.py`：支持从快照读取 `market_news`。
- `src/stock_ts/workflows.py`：无新闻 CSV 时自动使用快照里的市场新闻生成日报新闻舆情。
- `src/stock_ts/analysis.py`：个股“消息事件”维度展示具体催化标题和风险标题。

## 外部新闻源配置

默认仍优先使用已有 AKShare 东方财富入口。若后续有 NewsNow/RSS bridge 或其他 JSON 新闻接口，可通过环境变量追加：

```bash
export STOCK_TS_INTELLIGENCE_URLS="https://example.com/newsnow.json,https://example.com/rss-bridge.json"
```

也可以在手工补强时传参：

```bash
PYTHONPATH=src python3 scripts/enrich_tdx_snapshot.py \
  --snapshot data/imports/tdx_snapshots.json \
  --intelligence-url https://example.com/newsnow.json
```

JSON 接口建议返回以下任一结构：

```json
{
  "items": [
    {
      "title": "机器人订单增长",
      "summary": "AI 算力方向成交活跃",
      "url": "https://example.com/news/1",
      "published_at": "2026-07-08 09:00:00",
      "source": "外部快讯"
    }
  ]
}
```

## 质量等级口径

- `good`：关键字段齐全，且未发生源失败。
- `partial`：有可用数据，但存在源失败或部分字段缺失。
- `poor`：关键字段几乎全缺，或所有尝试源失败。
- `stale`：预留给明显过期的实时源。

## 后续建议

1. 把 `realtime_quotes.py` 接到 Tencent/TDX/iTick 实时接口，Web 顶部价格直接显示质量等级。
2. 为外部情报源增加 SQLite 本地缓存，按 URL 去重并保留最近 7 天。
3. 增加“新闻影响对象”识别：市场、板块、个股、持仓，日报只展示与持仓/候选相关的信息。
4. 增加数据源熔断窗口：连续失败的源 10-30 分钟内不重复请求，降低接口抖动。
