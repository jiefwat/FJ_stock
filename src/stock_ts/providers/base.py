from __future__ import annotations

from abc import ABC, abstractmethod

from stock_ts.models import CandidateStockRawData, MarketRawData, SectorRawData, StockRawData


class DataProviderError(RuntimeError):
    pass


class StockDataProvider(ABC):
    @abstractmethod
    def fetch_market(self) -> MarketRawData:
        raise NotImplementedError

    @abstractmethod
    def fetch_stock(self, code: str) -> StockRawData:
        raise NotImplementedError

    def fetch_sectors(self) -> list[SectorRawData]:
        raise DataProviderError("Sector data is not implemented for this provider")

    def fetch_candidate_universe(self) -> list[CandidateStockRawData]:
        raise DataProviderError("Candidate universe is not implemented for this provider")
