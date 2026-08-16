import { expect, it } from "vitest";

import { plainLanguage } from "./plainLanguage";

it("translates common stock-analysis jargon into everyday Chinese", () => {
  expect(
    plainLanguage(
      "历史K线确认：20日趋势 +8.4%，MA20偏离 +5.1%，20日波动偏高，催化仍需复核。",
    ),
  ).toBe(
    "过去一段时间的价格确认：近20天涨跌 +8.4%，与近20天平均价的距离 +5.1%，最近20天价格起伏偏高，可能推动股价的消息仍需再确认。",
  );
});

it("keeps the underlying number while explaining what capital flow means", () => {
  expect(plainLanguage("主动资金净流入 +2.1 亿")).toBe(
    "大额买入资金比卖出资金多 +2.1 亿",
  );
});

it("rewrites complete recommendation reasons before replacing individual terms", () => {
  expect(plainLanguage("当日涨幅 5.4% 未明显过热")).toBe(
    "今天上涨 5.4%，暂时不算涨得过急",
  );
  expect(plainLanguage("距 MA20 +7.2%，买点不拥挤")).toBe(
    "当前价格比近20天平均价高 +7.2%，暂时不算涨得太远",
  );
});
