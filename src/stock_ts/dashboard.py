from __future__ import annotations

from .analysis import analyze_market, analyze_stock
from .providers import create_provider
from .report import render_market_markdown, render_stock_markdown


def main() -> None:
    try:
        import streamlit as st
    except ImportError as exc:
        raise SystemExit("Streamlit is not installed. Run: pip install -e '.[dashboard]'") from exc

    st.set_page_config(page_title="StockTS A股分析", layout="wide")
    st.title("StockTS A股分析")
    st.caption("每日大盘分析、个股分析和研究报告生成。不构成投资建议。")

    provider_name = st.sidebar.selectbox("数据源", ["sample", "tencent", "eltdx", "akshare"])
    provider = create_provider(provider_name)

    tab_market, tab_stock = st.tabs(["每日大盘", "个股分析"])
    with tab_market:
        snapshot = analyze_market(provider.fetch_market())
        st.metric("市场温度", f"{snapshot.heat_score}/100", snapshot.summary)
        st.markdown(render_market_markdown(snapshot))

    with tab_stock:
        code = st.text_input("股票代码", value="600519")
        if st.button("生成个股分析"):
            report = analyze_stock(provider.fetch_stock(code))
            st.markdown(render_stock_markdown(report))


if __name__ == "__main__":
    main()
