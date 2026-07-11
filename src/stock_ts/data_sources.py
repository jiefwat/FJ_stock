from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DataSourceCapability:
    name: str
    status: str
    coverage: str
    best_for: str
    limitation: str
    integration: str


def build_data_source_matrix(
    *,
    active_provider: str,
    provider_class: str,
    has_tdx_snapshot: bool = False,
) -> list[DataSourceCapability]:
    return [
        DataSourceCapability(
            name="Tencent 行情",
            status="active" if provider_class == "TencentProvider" else "available",
            coverage="指数、个股 quote、日线 K 线",
            best_for="快速刷新个股行情和页面默认分析",
            limitation="板块、资金流、财务和公告覆盖不足",
            integration="内置 provider=tencent/auto",
        ),
        DataSourceCapability(
            name="eltdx MCP / 桥接",
            status="active" if provider_class == "EltdxProvider" else "available",
            coverage="实时 quote、最新日线、热题材、F10 主题和持仓相关辅助信息",
            best_for="最新行情刷新、热题材轮动和基于 TDX 的高频数据回补",
            limitation="依赖 python3.11 + eltdx 桥接进程，深度数据仍需结合其他源",
            integration="provider=eltdx / python3.11 scripts/eltdx_bridge.py",
        ),
        DataSourceCapability(
            name="AKShare",
            status="active" if provider_class == "AkshareProvider" else "available",
            coverage="指数、个股、行业板块、候选池、个股新闻",
            best_for="补行业、候选池和东方财富个股新闻",
            limitation="接口易限频或断连，必须保留 fallback 和告警",
            integration="内置 provider=akshare",
        ),
        DataSourceCapability(
            name="TDX MCP 快照",
            status=_tdx_status(provider_class, has_tdx_snapshot),
            coverage="实时 quote、盘口、成交、历史 K 线快照",
            best_for="用 Codex MCP/通达信服务校验行情和盘口，再导入本地分析",
            limitation="MCP 是会话工具，项目运行时通过 JSON 快照导入，不直接依赖聊天工具",
            integration="provider=tdx-snapshot / data/imports/tdx_snapshots.json",
        ),
        DataSourceCapability(
            name="Longbridge MCP",
            status="available",
            coverage="市场新闻、个股新闻、异动事件、市场温度、财经日历",
            best_for="补市场消息面、跨市场异动、宏观事件和风险偏好温度",
            limitation=(
                "MCP 是会话工具，需先导出 JSON 再由脚本写入快照；"
                "新闻只做证据，不单独作为交易理由"
            ),
            integration="scripts/import_mcp_market_intelligence.py / mcp_market_news_refresh",
        ),
        DataSourceCapability(
            name="本地 CSV/Excel 导入",
            status="available",
            coverage="行情 CSV、新闻舆情 CSV、持仓 CSV、交易流水 CSV",
            best_for="接券商导出、第三方数据或人工整理数据",
            limitation="需要用户或自动任务维护文件 freshness",
            integration="import-prices/news/portfolio/daily workflows",
        ),
        DataSourceCapability(
            name="CNInfo skill",
            status="skill",
            coverage="A股/港股公告、年报、季报和财报材料",
            best_for="基本面、财报、公告事件、风险事项研究",
            limitation="当前作为 Codex skill 使用，后续可沉淀为公告导入任务",
            integration="cninfo-to-notebooklm skill / 未来 reports importer",
        ),
        DataSourceCapability(
            name="AgentReach skill",
            status="skill",
            coverage="雪球/财经网页触达、搜索和跨站抓取能力",
            best_for="市场舆情、投资者讨论、新闻补充和多源交叉验证",
            limitation="内容质量需过滤，不能直接作为交易结论",
            integration="agent-reach skill / 未来 sentiment importer",
        ),
        DataSourceCapability(
            name="Tushare Pro",
            status="active" if provider_class == "TushareProvider" else "available",
            coverage="A股日线、指数、财务、资金流、交易日历",
            best_for="Token 稳定兜底、历史回补和中长期基本面",
            limitation="需要 TUSHARE_TOKEN，字段口径需和 TDX/AKShare 交叉校验",
            integration="provider=tushare / TUSHARE_TOKEN",
        ),
        DataSourceCapability(
            name="iTick",
            status="available",
            coverage="A股/港股/美股实时报价、盘口、K 线",
            best_for="补充全市场候选池的 K 线和最新报价，作为 AKShare/Tushare 慢接口的备用源",
            limitation=(
                "需要 ITICK_API_KEY；不提供估值、基本面、资金流和新闻，A股代码口径需用 Key 实测校验"
            ),
            integration="ITICK_API_KEY / scripts/enrich_tdx_snapshot.py",
        ),
        DataSourceCapability(
            name="Baostock / YFinance",
            status="planned",
            coverage="A股历史补充、港股/美股行情",
            best_for="跨市场扩展和历史行情补洞",
            limitation="免费源延迟、复权和成交额口径需要校验",
            integration="后续 provider 插件化接入",
        ),
    ]


def _tdx_status(provider_class: str, has_tdx_snapshot: bool) -> str:
    if provider_class == "TdxSnapshotProvider":
        return "active"
    if has_tdx_snapshot:
        return "available"
    return "ready"
