const CHINA_MARKET_TIME_ZONE = "Asia/Shanghai";

export function formatMarketDateTime(value: string) {
  return new Date(value).toLocaleString("zh-CN", {
    hour12: false,
    timeZone: CHINA_MARKET_TIME_ZONE,
  });
}
