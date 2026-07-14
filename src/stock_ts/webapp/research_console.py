from __future__ import annotations

from dataclasses import dataclass
from html import escape


@dataclass(frozen=True)
class ResearchContextOption:
    label: str
    code: str = ""
    name: str = ""
    sector: str = ""


MODULE_PRESETS = {
    "market": (
        ("指数结构", "三大指数当前趋势、强弱和关键位置如何？"),
        ("宏观变量", "近期哪些宏观指标和政策变量正在影响A股？"),
        ("主线板块", "筛选当前强度和成交额靠前的行业板块。"),
        ("风险新闻", "近期有哪些可能影响市场风险偏好的重要新闻？"),
    ),
    "portfolio": (
        ("业绩风险", "这家公司近期是否有业绩预告或经营风险？"),
        ("公告核查", "最近公告中有哪些需要持仓人重点核查的事项？"),
        ("机构下修", "机构盈利预期和评级是否出现下修？"),
        ("资金异动", "近期主力资金、成交量和价格是否出现异常？"),
    ),
    "stock": (
        ("财务质量", "收入、利润和现金流质量是否同步改善？"),
        ("机构预期", "未来两年盈利预期和机构评级如何变化？"),
        ("事件风险", "近期是否有解禁、质押、监管或业绩预告风险？"),
        ("行业位置", "当前行业估值和盈利排名处于什么位置？"),
    ),
    "opportunity": (
        ("板块持续性", "这个板块的强度、成交额和持续性如何？"),
        ("A股筛选", "在当前方向中筛选盈利改善且证据较完整的A股。"),
        ("事件催化", "近期有哪些可核查的公告、事件或新闻催化？"),
        ("风险排除", "这个方向或候选有哪些应优先排除的风险？"),
    ),
}

MODULE_META = {
    "market": ("市场研究 · 外部证据", "问财外部核查"),
    "portfolio": ("持仓研究 · 单股核查", "问财外部核查"),
    "stock": ("股票研究 · 外部证据", "问财研究追问"),
    "opportunity": ("机会研究 · 外部证据", "问财外部核查"),
}


def render_iwencai_research_console(
    *,
    module: str,
    status: str,
    code: str = "",
    name: str = "",
    sector: str = "",
    local_as_of: str = "",
    context_options: tuple[ResearchContextOption, ...] = (),
) -> str:
    if module not in MODULE_PRESETS:
        raise ValueError("不支持的研究模块。")
    configured = status == "configured"
    blocked = status == "requires_login"
    status_label = "已连接" if configured else ("需启用登录" if blocked else "未配置")
    status_class = "connected" if configured else ("blocked" if blocked else "missing")
    disabled = " disabled" if blocked else ""
    kicker, title = MODULE_META[module]
    suggestions = "".join(
        '<button type="button" class="iwencai-question-chip" '
        f'data-iwencai-question="{escape(question, quote=True)}"{disabled}>'
        f"{escape(label)}</button>"
        for label, question in MODULE_PRESETS[module]
    )
    context_select = _render_context_select(module, context_options, disabled)
    question_id = f"iwencai-question-{module}"
    return f"""
      <section class="iwencai-research-console" data-iwencai-research="true"
        data-iwencai-module="{escape(module)}"
        data-stock-code="{escape(code, quote=True)}" data-stock-name="{escape(name, quote=True)}"
        data-sector="{escape(sector, quote=True)}"
        data-local-as-of="{escape(local_as_of, quote=True)}"
        data-config-status="{escape(status, quote=True)}"
        aria-labelledby="iwencai-research-title-{escape(module)}">
        <header class="iwencai-research-header">
          <div><span>{escape(kicker)}</span>
            <h3 id="iwencai-research-title-{escape(module)}">{escape(title)}</h3></div>
          <strong class="iwencai-connection {status_class}">{status_label}</strong>
        </header>
        <div class="iwencai-question-rail">{suggestions}</div>
        <form class="iwencai-research-form" data-iwencai-form>
          {context_select}
          <label class="sr-only" for="{question_id}">研究问题</label>
          <textarea id="{question_id}" name="question" maxlength="200"
            rows="2" required data-iwencai-input{disabled}
            placeholder="输入一个需要外部数据核查的问题"></textarea>
          <button type="submit" data-iwencai-submit{disabled}>核查问财</button>
        </form>
        <p class="iwencai-console-state" data-iwencai-state>
          {'启用登录后可查询问财。' if blocked else '问财结果只作证据补充，不改写本地结论。'}</p>
        <div class="iwencai-research-result" data-iwencai-result hidden aria-live="polite"></div>
      </section>"""


def _render_context_select(
    module: str,
    options: tuple[ResearchContextOption, ...],
    disabled: str,
) -> str:
    if not options:
        return ""
    label = "选择持仓" if module == "portfolio" else "选择板块或候选"
    option_html = "".join(
        '<option value="context" '
        f'data-code="{escape(item.code, quote=True)}" '
        f'data-name="{escape(item.name, quote=True)}" '
        f'data-sector="{escape(item.sector, quote=True)}">'
        f"{escape(item.label)}</option>"
        for item in options
    )
    return (
        f'<label class="sr-only" for="iwencai-context-{escape(module)}">{label}</label>'
        f'<select id="iwencai-context-{escape(module)}" class="iwencai-context-select" '
        f'data-iwencai-context required{disabled}>'
        f'<option value="">{label}</option>{option_html}</select>'
    )
