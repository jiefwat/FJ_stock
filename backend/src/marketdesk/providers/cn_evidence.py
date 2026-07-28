from __future__ import annotations

import asyncio
import hashlib
import html
import re
import time
from datetime import UTC, datetime
from typing import Any, cast
from zoneinfo import ZoneInfo

import httpx

from marketdesk.models import (
    CapabilityStatus,
    EvidenceDocument,
    Freshness,
    InstrumentTheme,
    MarketEventRaw,
    SourceRef,
    TradingAnomaly,
)
from marketdesk.providers.base import ProviderUnavailable


class AshareEvidenceProvider:
    cninfo_org_url = "https://www.cninfo.com.cn/new/data/szse_stock.json"
    cninfo_query_url = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
    eastmoney_report_url = "https://reportapi.eastmoney.com/report/list"
    eastmoney_theme_url = "https://push2.eastmoney.com/api/qt/slist/get"
    eastmoney_datacenter_url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    cls_roll_url = "https://www.cls.cn/v1/roll/get_roll_list"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 MarketDesk/0.2"},
            follow_redirects=True,
            trust_env=False,
        )
        self._org_map: dict[str, str] | None = None
        self._eastmoney_lock = asyncio.Lock()
        self._eastmoney_last_request = 0.0
        self._status: dict[str, dict[str, Any]] = {
            "cninfo_filings": self._status_payload(
                CapabilityStatus.NOT_CHECKED, "巨潮公告元数据"
            ),
            "eastmoney_research": self._status_payload(
                CapabilityStatus.NOT_CHECKED, "东方财富研报元数据"
            ),
            "eastmoney_themes": self._status_payload(
                CapabilityStatus.NOT_CHECKED, "东方财富题材归属"
            ),
            "eastmoney_dragon_tiger": self._status_payload(
                CapabilityStatus.NOT_CHECKED, "东方财富龙虎榜"
            ),
            "cls_fast_news": self._status_payload(
                CapabilityStatus.NOT_CHECKED, "财联社快讯备源"
            ),
        }

    @staticmethod
    def _status_payload(status: CapabilityStatus, description: str) -> dict[str, Any]:
        return {"status": status.value, "required": False, "description": description}

    def _mark(
        self,
        key: str,
        status: CapabilityStatus,
        description: str,
        error: str | None = None,
    ) -> None:
        payload = self._status_payload(status, description)
        payload["fetched_at"] = datetime.now(UTC).isoformat()
        if error:
            payload["error"] = error
        self._status[key] = payload

    def provider_status(self) -> dict[str, dict[str, Any]]:
        return {key: dict(value) for key, value in self._status.items()}

    @staticmethod
    def _float(value: Any) -> float | None:
        if value in (None, "", "-", "--"):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _symbol(code: str) -> str:
        if code.startswith(("4", "8")):
            market = "BJ"
        elif code.startswith(("5", "6", "9")):
            market = "SH"
        else:
            market = "SZ"
        return f"{market}.{code}"

    @staticmethod
    def _document_freshness(observed_at: datetime, fetched_at: datetime) -> Freshness:
        age_days = max(0, (fetched_at - observed_at).days)
        if age_days <= 2:
            return Freshness.FRESH
        if age_days <= 30:
            return Freshness.DELAYED
        return Freshness.STALE

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value / 1000, tz=UTC)
            except (OSError, OverflowError, ValueError):
                return None
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
        return parsed.astimezone(UTC)

    @staticmethod
    def _clean_text(value: Any) -> str:
        raw = re.sub(r"<[^>]+>", "", str(value or ""))
        return html.unescape(raw).strip()

    @staticmethod
    def normalize_cninfo_org_map(payload: dict[str, Any]) -> dict[str, str]:
        result: dict[str, str] = {}
        for item in payload.get("stockList") or []:
            code = str(item.get("code") or "")
            org_id = str(item.get("orgId") or "")
            if len(code) == 6 and org_id:
                result[code] = org_id
        return result

    @classmethod
    def normalize_cninfo_announcements(
        cls, payload: dict[str, Any], symbol: str, fetched_at: datetime
    ) -> list[EvidenceDocument]:
        documents: list[EvidenceDocument] = []
        for item in payload.get("announcements") or []:
            item_id = str(item.get("announcementId") or "")
            title = cls._clean_text(item.get("announcementTitle"))
            published_at = cls._parse_datetime(item.get("announcementTime"))
            if not item_id or not title or published_at is None:
                continue
            source_url = (
                f"https://www.cninfo.com.cn/new/disclosure/detail?annoId={item_id}"
            )
            source = SourceRef(
                provider="cninfo",
                label="巨潮资讯",
                capability="filings",
                source_url=source_url,
                observed_at=published_at,
                fetched_at=fetched_at,
                freshness=cls._document_freshness(published_at, fetched_at),
            )
            documents.append(
                EvidenceDocument(
                    id=f"cninfo:{item_id}",
                    kind="filing",
                    symbol=symbol,
                    title=title,
                    category=cls._clean_text(item.get("announcementTypeName")) or "公司公告",
                    publisher="巨潮资讯",
                    published_at=published_at,
                    url=source_url,
                    source=source,
                )
            )
        return documents

    @classmethod
    def normalize_research_reports(
        cls, payload: dict[str, Any], symbol: str, fetched_at: datetime
    ) -> list[EvidenceDocument]:
        documents: list[EvidenceDocument] = []
        for item in payload.get("data") or []:
            item_id = str(item.get("infoCode") or "")
            title = cls._clean_text(item.get("title"))
            published_at = cls._parse_datetime(item.get("publishDate"))
            if not item_id or not title or published_at is None:
                continue
            eps_values = {
                "current_year": cls._float(item.get("predictThisYearEps")),
                "year_plus_1": cls._float(item.get("predictNextYearEps")),
                "year_plus_2": cls._float(item.get("predictNextTwoYearEps")),
            }
            eps = {key: value for key, value in eps_values.items() if value is not None}
            source_url = f"https://pdf.dfcfw.com/pdf/H3_{item_id}_1.pdf"
            source = SourceRef(
                provider="eastmoney_report",
                label="东方财富研报",
                capability="research",
                source_url=source_url,
                observed_at=published_at,
                fetched_at=fetched_at,
                freshness=cls._document_freshness(published_at, fetched_at),
            )
            documents.append(
                EvidenceDocument(
                    id=f"eastmoney-report:{item_id}",
                    kind="research",
                    symbol=symbol,
                    title=title,
                    category=cls._clean_text(item.get("indvInduName")) or "公司研究",
                    publisher=cls._clean_text(item.get("orgSName")) or "未知机构",
                    published_at=published_at,
                    url=source_url,
                    rating=cls._clean_text(item.get("emRatingName")) or None,
                    eps_forecasts=eps,
                    source=source,
                )
            )
        return documents

    @classmethod
    def normalize_themes(
        cls, payload: dict[str, Any], fetched_at: datetime
    ) -> list[InstrumentTheme]:
        raw_rows = (payload.get("data") or {}).get("diff") or []
        rows = raw_rows.values() if isinstance(raw_rows, dict) else raw_rows
        source = SourceRef(
            provider="eastmoney_theme",
            label="东方财富题材归属",
            capability="themes",
            source_url="https://quote.eastmoney.com/",
            observed_at=fetched_at,
            fetched_at=fetched_at,
            freshness=Freshness.FRESH,
        )
        themes: list[InstrumentTheme] = []
        for item in rows:
            code = str(item.get("f12") or "")
            name = cls._clean_text(item.get("f14"))
            if not code or not name:
                continue
            themes.append(
                InstrumentTheme(
                    code=code,
                    name=name,
                    change_pct=cls._float(item.get("f3")),
                    lead_stock=cls._clean_text(item.get("f128")) or None,
                    source=source,
                )
            )
        return themes

    @classmethod
    def normalize_dragon_tiger(
        cls, payload: dict[str, Any], fetched_at: datetime
    ) -> list[TradingAnomaly]:
        rows = (payload.get("result") or {}).get("data") or []
        anomalies: list[TradingAnomaly] = []
        for item in rows:
            code = str(item.get("SECURITY_CODE") or "")
            published_at = cls._parse_datetime(item.get("TRADE_DATE"))
            if len(code) != 6 or published_at is None:
                continue
            source = SourceRef(
                provider="eastmoney_datacenter",
                label="东方财富龙虎榜",
                capability="dragon_tiger",
                source_url="https://data.eastmoney.com/stock/lhb.html",
                observed_at=published_at,
                fetched_at=fetched_at,
                freshness=cls._document_freshness(published_at, fetched_at),
            )
            anomalies.append(
                TradingAnomaly(
                    symbol=cls._symbol(code),
                    name=cls._clean_text(item.get("SECURITY_NAME_ABBR")) or code,
                    trade_date=published_at.date(),
                    reason=cls._clean_text(item.get("EXPLANATION")) or "龙虎榜交易异动",
                    close=cls._float(item.get("CLOSE_PRICE")),
                    change_pct=cls._float(item.get("CHANGE_RATE")),
                    net_buy=cls._float(item.get("BILLBOARD_NET_AMT")),
                    buy_amount=cls._float(item.get("BILLBOARD_BUY_AMT")),
                    sell_amount=cls._float(item.get("BILLBOARD_SELL_AMT")),
                    turnover_rate=cls._float(item.get("TURNOVERRATE")),
                    source=source,
                )
            )
        return anomalies

    @staticmethod
    def cls_signed_params(page_size: int) -> dict[str, str]:
        params = {
            "appName": "CailianpressWeb",
            "os": "web",
            "sv": "7.7.5",
            "last_time": "",
            "refresh_type": "1",
            "rn": str(page_size),
        }
        query = "&".join(f"{key}={params[key]}" for key in sorted(params))
        sha1 = hashlib.sha1(query.encode(), usedforsecurity=False).hexdigest()
        params["sign"] = hashlib.md5(sha1.encode(), usedforsecurity=False).hexdigest()
        return params

    @classmethod
    def normalize_cls_events(
        cls, payload: dict[str, Any], fetched_at: datetime
    ) -> list[MarketEventRaw]:
        events: list[MarketEventRaw] = []
        for item in (payload.get("data") or {}).get("roll_data") or []:
            item_id = str(item.get("id") or item.get("telegraph_id") or "")
            title = cls._clean_text(item.get("title") or item.get("brief"))
            summary = cls._clean_text(item.get("content") or item.get("brief") or title)
            timestamp = item.get("ctime")
            if not item_id or not title or not isinstance(timestamp, (int, float)):
                continue
            try:
                published_at = datetime.fromtimestamp(timestamp, tz=UTC)
            except (OSError, OverflowError, ValueError):
                continue
            events.append(
                MarketEventRaw(
                    id=f"cls:{item_id}",
                    title=title,
                    summary=summary or title,
                    source="财联社电报",
                    url=f"https://www.cls.cn/detail/{item_id}",
                    published_at=published_at,
                )
            )
        return events

    async def _eastmoney_get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        async with self._eastmoney_lock:
            elapsed = time.monotonic() - self._eastmoney_last_request
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)
            try:
                response = await self.client.get(
                    url,
                    params=params,
                    headers={
                        "User-Agent": "Mozilla/5.0 MarketDesk/0.2",
                        "Referer": "https://data.eastmoney.com/",
                    },
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("response is not an object")
                return cast(dict[str, Any], payload)
            except (httpx.HTTPError, ValueError) as error:
                raise ProviderUnavailable(f"Eastmoney capability request failed: {error}") from error
            finally:
                self._eastmoney_last_request = time.monotonic()

    async def _load_org_map(self) -> dict[str, str]:
        if self._org_map is not None:
            return self._org_map
        try:
            response = await self.client.get(
                self.cninfo_org_url,
                headers={
                    "User-Agent": "Mozilla/5.0 MarketDesk/0.2",
                    "Referer": "https://www.cninfo.com.cn/new/disclosure",
                },
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("response is not an object")
            self._org_map = self.normalize_cninfo_org_map(payload)
        except (httpx.HTTPError, ValueError) as error:
            self._org_map = {}
            self._mark(
                "cninfo_filings",
                CapabilityStatus.PARTIAL,
                "巨潮公告元数据",
                f"orgId mapping unavailable: {error}",
            )
        return self._org_map

    @staticmethod
    def _fallback_org_id(code: str) -> str:
        if code.startswith("6"):
            return f"gssh0{code}"
        if code.startswith(("4", "8")):
            return f"gsbj0{code}"
        return f"gssz0{code}"

    async def fetch_filings(self, symbol: str, limit: int = 20) -> list[EvidenceDocument]:
        code = symbol.split(".", 1)[-1]
        org_map = await self._load_org_map()
        org_id = org_map.get(code) or self._fallback_org_id(code)
        fetched_at = datetime.now(UTC)
        try:
            response = await self.client.post(
                self.cninfo_query_url,
                data={
                    "stock": f"{code},{org_id}",
                    "tabName": "fulltext",
                    "pageSize": str(limit),
                    "pageNum": "1",
                    "column": "",
                    "category": "",
                    "plate": "",
                    "seDate": "",
                    "searchkey": "",
                    "secid": "",
                    "sortName": "",
                    "sortType": "",
                    "isHLtitle": "true",
                },
                headers={
                    "User-Agent": "Mozilla/5.0 MarketDesk/0.2",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": "https://www.cninfo.com.cn/new/disclosure",
                    "Origin": "https://www.cninfo.com.cn",
                },
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("response is not an object")
            documents = self.normalize_cninfo_announcements(payload, symbol, fetched_at)[:limit]
        except (httpx.HTTPError, ValueError) as error:
            self._mark(
                "cninfo_filings",
                CapabilityStatus.UNAVAILABLE,
                "巨潮公告元数据",
                str(error),
            )
            raise ProviderUnavailable(f"CNINFO filing request failed: {error}") from error
        current = self._status.get("cninfo_filings", {})
        status = CapabilityStatus.READY if documents else CapabilityStatus.EMPTY
        if current.get("status") != CapabilityStatus.PARTIAL.value:
            self._mark("cninfo_filings", status, "巨潮公告元数据")
        return documents

    async def fetch_research(
        self, symbol: str, limit: int = 20
    ) -> list[EvidenceDocument]:
        code = symbol.split(".", 1)[-1]
        fetched_at = datetime.now(UTC)
        try:
            payload = await self._eastmoney_get(
                self.eastmoney_report_url,
                {
                    "industryCode": "*",
                    "pageSize": str(limit),
                    "industry": "*",
                    "rating": "*",
                    "ratingChange": "*",
                    "beginTime": "2000-01-01",
                    "endTime": "2030-01-01",
                    "pageNo": "1",
                    "fields": "",
                    "qType": "0",
                    "orgCode": "",
                    "code": code,
                    "rcode": "",
                },
            )
            documents = self.normalize_research_reports(payload, symbol, fetched_at)[:limit]
        except ProviderUnavailable as error:
            self._mark(
                "eastmoney_research",
                CapabilityStatus.UNAVAILABLE,
                "东方财富研报元数据",
                str(error),
            )
            raise
        self._mark(
            "eastmoney_research",
            CapabilityStatus.READY if documents else CapabilityStatus.EMPTY,
            "东方财富研报元数据",
        )
        return documents

    async def fetch_themes(self, symbol: str, limit: int = 30) -> list[InstrumentTheme]:
        code = symbol.split(".", 1)[-1]
        market_code = 1 if code.startswith(("5", "6", "9")) else 0
        fetched_at = datetime.now(UTC)
        try:
            payload = await self._eastmoney_get(
                self.eastmoney_theme_url,
                {
                    "fltt": "2",
                    "invt": "2",
                    "secid": f"{market_code}.{code}",
                    "spt": "3",
                    "pi": "0",
                    "pz": str(limit),
                    "po": "1",
                    "fields": "f12,f14,f3,f128",
                },
            )
            themes = self.normalize_themes(payload, fetched_at)[:limit]
        except ProviderUnavailable as error:
            self._mark(
                "eastmoney_themes",
                CapabilityStatus.UNAVAILABLE,
                "东方财富题材归属",
                str(error),
            )
            raise
        self._mark(
            "eastmoney_themes",
            CapabilityStatus.READY if themes else CapabilityStatus.EMPTY,
            "东方财富题材归属",
        )
        return themes

    async def fetch_dragon_tiger(self, limit: int = 20) -> list[TradingAnomaly]:
        fetched_at = datetime.now(UTC)
        try:
            payload = await self._eastmoney_get(
                self.eastmoney_datacenter_url,
                {
                    "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
                    "columns": "ALL",
                    "filter": "",
                    "pageNumber": "1",
                    "pageSize": str(max(limit, 50)),
                    "sortColumns": "TRADE_DATE,BILLBOARD_NET_AMT",
                    "sortTypes": "-1,-1",
                    "source": "WEB",
                    "client": "WEB",
                },
            )
            anomalies = self.normalize_dragon_tiger(payload, fetched_at)
            if anomalies:
                latest_date = max(item.trade_date for item in anomalies)
                anomalies = [item for item in anomalies if item.trade_date == latest_date]
            anomalies = anomalies[:limit]
        except ProviderUnavailable as error:
            self._mark(
                "eastmoney_dragon_tiger",
                CapabilityStatus.UNAVAILABLE,
                "东方财富龙虎榜",
                str(error),
            )
            raise
        self._mark(
            "eastmoney_dragon_tiger",
            CapabilityStatus.READY if anomalies else CapabilityStatus.EMPTY,
            "东方财富龙虎榜",
        )
        return anomalies

    async def fetch_cls_events(self, limit: int = 50) -> list[MarketEventRaw]:
        fetched_at = datetime.now(UTC)
        try:
            response = await self.client.get(
                self.cls_roll_url,
                params=self.cls_signed_params(limit),
                headers={
                    "User-Agent": "Mozilla/5.0 MarketDesk/0.2",
                    "Referer": "https://www.cls.cn/",
                },
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("response is not an object")
            events = self.normalize_cls_events(payload, fetched_at)[:limit]
        except (httpx.HTTPError, ValueError) as error:
            self._mark(
                "cls_fast_news",
                CapabilityStatus.UNAVAILABLE,
                "财联社快讯备源",
                str(error),
            )
            raise ProviderUnavailable(f"CLS event request failed: {error}") from error
        self._mark(
            "cls_fast_news",
            CapabilityStatus.READY if events else CapabilityStatus.EMPTY,
            "财联社快讯备源",
        )
        return events
