from __future__ import annotations

from .view_models import WorkspaceMeta

WORKSPACES = [
    WorkspaceMeta(
        key="market",
        label="每日大盘",
        badge="01",
        description="指数、宽度、成交、板块与风险统计。",
    ),
    WorkspaceMeta(
        key="portfolio",
        label="我的持仓",
        badge="02",
        description="按成本、仓位、风险共振和处理顺序管理组合。",
    ),
    WorkspaceMeta(
        key="stock",
        label="个股分析",
        badge="03",
        description="把 K 线、资金、消息和持仓成本压成一张决策卡。",
    ),
    WorkspaceMeta(
        key="opportunity",
        label="热点机会",
        badge="04",
        description="合并板块热度、情绪温度和候选观察池。",
    ),
    WorkspaceMeta(
        key="data-center",
        label="数据中台",
        badge="05",
        description="集中核对行情、K线、资金、新闻、公告和基本面状态。",
    ),
    WorkspaceMeta(
        key="account",
        label="账户管理",
        badge="用户",
        description="登录、退出、密码和个人持仓账本。",
    ),
]

WORKSPACE_MODULES = {
    "market": ["market"],
    "portfolio": ["portfolio"],
    "stock": ["stock"],
    "opportunity": ["opportunity"],
    "data-center": ["data-center"],
    "account": ["account"],
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
