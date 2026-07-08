from __future__ import annotations

from .view_models import WorkspaceMeta

WORKSPACES = [
    WorkspaceMeta(
        key="home",
        label="今日行动",
        badge="01",
        description="回答今天先看什么。",
    ),
    WorkspaceMeta(
        key="market",
        label="看大盘",
        badge="02",
        description="判断市场适合进攻、震荡还是防守。",
    ),
    WorkspaceMeta(
        key="sector",
        label="看主线",
        badge="03",
        description="确认主线位置和持续性。",
    ),
    WorkspaceMeta(
        key="sentiment",
        label="看情绪",
        badge="04",
        description="观察短线赚钱效应和亏钱效应。",
    ),
    WorkspaceMeta(
        key="screener",
        label="找机会",
        badge="05",
        description="筛选值得观察的候选池。",
    ),
    WorkspaceMeta(
        key="stock",
        label="分析个股",
        badge="06",
        description="围绕单只股票形成证据链和条件计划。",
    ),
    WorkspaceMeta(
        key="portfolio",
        label="处理持仓",
        badge="07",
        description="检查组合风险和仓位处理顺序。",
    ),
    WorkspaceMeta(
        key="watchlist",
        label="自选研究",
        badge="08",
        description="管理长期观察池、假设和提醒条件。",
    ),
    WorkspaceMeta(
        key="daily",
        label="看复盘",
        badge="09",
        description="生成、复制和归档复盘内容。",
    ),
    WorkspaceMeta(
        key="notify",
        label="收晨报",
        badge="10",
        description="dry-run 报告和测试发送渠道。",
    ),
    WorkspaceMeta(
        key="settings",
        label="检查系统",
        badge="11",
        description="检查数据源、缓存、凭证状态和体检入口。",
    ),
]

WORKSPACE_MODULES = {
    "home": ["home"],
    "market": ["market"],
    "sector": ["sector"],
    "sentiment": ["sentiment"],
    "screener": ["screener"],
    "stock": ["stock"],
    "portfolio": ["portfolio"],
    "watchlist": ["watchlist"],
    "daily": ["daily"],
    "notify": ["notify"],
    "settings": ["settings"],
}

MODULE_TO_WORKSPACE = {
    module: workspace for workspace, modules in WORKSPACE_MODULES.items() for module in modules
}


def module_to_workspace(module: str) -> str:
    return MODULE_TO_WORKSPACE.get(module, "market")


def group_sections_by_workspace(section_map: dict[str, str]) -> dict[str, str]:
    grouped: dict[str, str] = {}
    for meta in WORKSPACES:
        grouped[meta.key] = "".join(section_map[module] for module in WORKSPACE_MODULES[meta.key])
    return grouped
