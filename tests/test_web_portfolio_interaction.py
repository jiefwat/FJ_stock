from pathlib import Path

from stock_ts.models import Holding
from stock_ts.portfolio import delete_holding_csv, load_holdings_csv, upsert_holding_csv
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.web import PortfolioNotice, _portfolio_redirect_url, render_page


def _write_sample_holdings(path: Path) -> Path:
    path.write_text(
        "code,name,shares,cost_price,sector,note\n"
        "600519,贵州茅台,100,1500,白酒,核心仓位\n"
        "603278,大业股份,4000,9.5362,金属制品,测试持仓\n",
        encoding="utf-8",
    )
    return path


def test_upsert_holding_csv_creates_and_updates_rows(tmp_path: Path) -> None:
    holdings_file = tmp_path / "holdings.csv"

    result = upsert_holding_csv(
        holdings_file,
        Holding(
            code="600519",
            name="贵州茅台",
            shares=100,
            cost_price=1500,
            sector="白酒",
            note="核心仓位",
        ),
    )

    assert result == "added"
    loaded = load_holdings_csv(holdings_file)
    assert len(loaded) == 1
    assert loaded[0].name == "贵州茅台"

    result = upsert_holding_csv(
        holdings_file,
        Holding(
            code="600519",
            name="贵州茅台",
            shares=120,
            cost_price=1480,
            sector="白酒",
            note="更新后仓位",
        ),
    )

    assert result == "updated"
    loaded = load_holdings_csv(holdings_file)
    assert len(loaded) == 1
    assert loaded[0].shares == 120
    assert loaded[0].cost_price == 1480
    assert loaded[0].note == "更新后仓位"


def test_delete_holding_csv_blocks_last_position(tmp_path: Path) -> None:
    holdings_file = tmp_path / "holdings.csv"
    holdings_file.write_text(
        "code,name,shares,cost_price,sector,note\n600519,贵州茅台,100,1500,白酒,核心\n000001,平安银行,200,10.5,银行,观察\n",
        encoding="utf-8",
    )

    delete_holding_csv(holdings_file, "000001")
    loaded = load_holdings_csv(holdings_file)
    assert [item.code for item in loaded] == ["600519"]

    try:
        delete_holding_csv(holdings_file, "600519")
    except ValueError as exc:
        assert "至少保留一条持仓记录" in str(exc)
    else:
        raise AssertionError("expected ValueError when deleting final holding")


def test_web_renders_portfolio_interaction_controls(tmp_path: Path) -> None:
    holdings_file = _write_sample_holdings(tmp_path / "holdings.csv")

    html = render_page(
        stock_code="大业股份",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path=str(holdings_file),
        portfolio_notice=PortfolioNotice(level="success", message="已新增持仓"),
    )

    assert "持仓分析" in html
    assert "对应板块分析" not in html
    assert "仓位/成本分析" not in html
    assert "技术面" in html
    assert "资金面" in html
    assert "基本面" in html
    assert "消息面" in html
    assert "板块/主题" in html
    assert "仓位成本" in html
    assert 'method="post" action="/holdings"' in html
    assert 'name="portfolio_action" value="upsert"' in html
    assert 'name="portfolio_action" value="delete"' in html
    assert "保存持仓" in html
    assert "编辑" in html
    assert "删除" in html
    assert "添加持仓" not in html
    assert "已新增持仓" in html
    assert "持仓文件" not in html
    assert "CSV 表头" not in html
    assert "个股分析" in html
    assert 'id="portfolio-form"' in html
    assert "编辑 data/portfolio/holdings.csv" not in html
    assert "transactions CSV" not in html
    assert "Web URL 可加 holdings" not in html


def test_web_renders_daily_and_total_pnl_with_holding_stock_view(tmp_path: Path) -> None:
    holdings_file = _write_sample_holdings(tmp_path / "holdings.csv")

    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path=str(holdings_file),
    )

    assert "持仓/成本" in html
    assert "成本" in html
    assert "后续建议" in html
    assert "未来涨跌预测" in html


def test_web_forms_keep_user_in_target_modules(tmp_path: Path) -> None:
    holdings_file = _write_sample_holdings(tmp_path / "holdings.csv")

    html = render_page(
        stock_code="600519",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path=str(holdings_file),
    )

    assert 'action="/#module-stock"' in html
    assert 'class="stock-form" method="get" action="/#module-stock"' in html
    assert "确认删除这条持仓记录？" in html


def test_portfolio_redirect_url_returns_portfolio_anchor() -> None:
    url = _portfolio_redirect_url(
        code="",
        provider_name="auto",
        holdings_path="data/portfolio/holdings.csv",
        notice="已新增持仓",
        notice_level="success",
    )

    assert url.startswith("/?")
    assert "provider=auto" in url
    assert "holdings=data%2Fportfolio%2Fholdings.csv" in url
    assert "notice_level=success" in url
    assert url.endswith("#module-portfolio")


def test_web_can_render_clean_entry_without_explicit_code(tmp_path: Path) -> None:
    holdings_file = _write_sample_holdings(tmp_path / "holdings.csv")

    html = render_page(
        stock_code="",
        provider_name="sample",
        provider=SampleDataProvider(),
        holdings_path=str(holdings_file),
    )

    assert "研究分析平台" in html
    assert "贵州茅台" in html
    assert 'name="code"' in html
