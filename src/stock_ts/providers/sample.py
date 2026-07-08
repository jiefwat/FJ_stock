from __future__ import annotations

from stock_ts.models import (
    CandidateStockRawData,
    DailyBar,
    IndexQuote,
    MarketRawData,
    SectorRawData,
    StockRawData,
)
from stock_ts.providers.base import StockDataProvider


class SampleDataProvider(StockDataProvider):
    _STOCKS = {
        "600519": ("贵州茅台", 1586.0, 28.5),
        "000001": ("平安银行", 12.2, 6.2),
        "300750": ("宁德时代", 205.5, 32.4),
        "603278": ("大业股份", 12.06, 42.0),
    }

    _SECTORS = [
        ("半导体", 3.8, 0.78, 22.5, 18.6, 3, 14, False),
        ("机器人", 2.9, 0.72, 18.1, 12.4, 2, 10, False),
        ("人工智能", 2.2, 0.68, 15.3, 9.7, 2, 8, False),
        ("算力", 1.9, 0.64, 12.2, 7.8, 1, 6, False),
        ("金属制品", 1.6, 0.60, 9.8, 5.2, 1, 4, False),
        ("新能源车", 1.4, 0.58, 8.9, 4.5, 1, 4, False),
        ("证券", 1.1, 0.55, 7.4, 3.2, 1, 3, False),
        ("银行", -0.4, 0.42, -3.2, -2.6, 0, 1, False),
        ("白酒", -1.2, 0.35, -8.1, -5.4, 0, 0, True),
        ("医药", -1.6, 0.31, -9.4, -6.2, 0, 0, True),
    ]

    def fetch_market(self) -> MarketRawData:
        return MarketRawData(
            trade_date="2026-06-05",
            indices=[
                IndexQuote(
                    code="000001", name="上证指数", close=3120.5, pct_chg=0.82, amount=5123.4
                ),
                IndexQuote(
                    code="399001", name="深证成指", close=9850.2, pct_chg=1.12, amount=6421.8
                ),
                IndexQuote(
                    code="399006", name="创业板指", close=2101.7, pct_chg=1.56, amount=2890.1
                ),
            ],
            advancing=3620,
            declining=1260,
            limit_up=78,
            limit_down=8,
            top_sectors=[("半导体", 3.8), ("机器人", 2.9), ("人工智能", 2.2), ("银行", -0.4)],
            northbound_net_inflow=42.6,
        )

    def fetch_stock(self, code: str) -> StockRawData:
        normalized_code = code.strip()
        name, latest_close, pe_ttm = self._STOCKS.get(normalized_code, ("示例股票", 18.8, 18.0))
        return StockRawData(
            code=normalized_code,
            name=name,
            bars=self._bars(latest_close),
            fund_flow=1.8,
            pe_ttm=pe_ttm,
        )

    def fetch_sectors(self) -> list[SectorRawData]:
        return [
            SectorRawData(
                name=name,
                pct_chg=pct_chg,
                advancing_ratio=advancing_ratio,
                amount_change=amount_change,
                fund_flow=fund_flow,
                consecutive_days=consecutive_days,
                limit_up_count=limit_up_count,
                high_divergence=high_divergence,
            )
            for (
                name,
                pct_chg,
                advancing_ratio,
                amount_change,
                fund_flow,
                consecutive_days,
                limit_up_count,
                high_divergence,
            ) in self._SECTORS
        ]

    def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
        sectors = ["半导体", "机器人", "人工智能", "算力", "新能源车", "证券", "银行", "白酒"]
        names = [
            "兆易创新",
            "北方华创",
            "中微公司",
            "机器人A",
            "绿的谐波",
            "拓斯达",
            "科大讯飞",
            "寒武纪",
            "浪潮信息",
            "中际旭创",
            "新易盛",
            "天孚通信",
            "宁德时代",
            "比亚迪",
            "阳光电源",
            "东方财富",
            "中信证券",
            "平安银行",
            "贵州茅台",
            "五粮液",
            "沪电股份",
            "工业富联",
            "晶方科技",
            "赛力斯",
            "长安汽车",
        ]
        universe: list[CandidateStockRawData] = []
        for index, name in enumerate(names):
            sector = sectors[index % len(sectors)]
            code = f"{300000 + index:06d}" if index % 3 == 0 else f"{600000 + index:06d}"
            latest = 18 + index * 1.7
            sector_bonus = 1.0 if sector in {"半导体", "机器人", "人工智能", "算力"} else 0.0
            universe.append(
                CandidateStockRawData(
                    code=code,
                    name=name,
                    sector=sector,
                    bars=self._candidate_bars(latest, index, sector_bonus),
                    fund_flow=round(0.4 + sector_bonus + index % 5 * 0.18, 2),
                    turnover_rate=round(3.5 + index % 6 * 0.7, 2),
                    amount=round(8 + index * 0.9, 2),
                    pe_ttm=22 + index % 9 * 5,
                )
            )
        return universe

    def _bars(self, latest_close: float) -> list[DailyBar]:
        closes = [
            latest_close * 0.95,
            latest_close * 0.97,
            latest_close * 0.985,
            latest_close * 0.995,
            latest_close * 0.991,
            latest_close,
        ]
        dates = [
            "2026-05-27",
            "2026-05-28",
            "2026-05-29",
            "2026-06-01",
            "2026-06-02",
            "2026-06-03",
        ]
        return [
            DailyBar(
                date=date,
                open=close * 0.99,
                high=close * 1.01,
                low=close * 0.985,
                close=close,
                volume=1000 + index * 380,
            )
            for index, (date, close) in enumerate(zip(dates, closes))
        ]

    def _candidate_bars(
        self,
        latest_close: float,
        seed: int,
        sector_bonus: float,
    ) -> list[DailyBar]:
        dates = [f"2026-05-{day:02d}" for day in range(12, 32)] + [
            "2026-06-01",
            "2026-06-02",
            "2026-06-03",
            "2026-06-04",
            "2026-06-05",
        ]
        closes = []
        base = latest_close * (0.86 - seed % 4 * 0.005)
        for index, _date in enumerate(dates):
            drift = 1 + index * (0.006 + sector_bonus * 0.0015)
            pulse = 1 + ((index + seed) % 5 - 2) * 0.004
            closes.append(base * drift * pulse)
        scale = latest_close / closes[-1]
        closes = [close * scale for close in closes]
        return [
            DailyBar(
                date=date,
                open=close * (0.992 + seed % 3 * 0.002),
                high=close * 1.018,
                low=close * 0.982,
                close=close,
                volume=1600 + index * (80 + seed % 5 * 12),
            )
            for index, (date, close) in enumerate(zip(dates, closes))
        ]
