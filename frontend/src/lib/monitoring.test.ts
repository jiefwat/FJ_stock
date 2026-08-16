import { describe, expect, it } from "vitest";

import { monitoringItem, monitoringText } from "./monitoring";

describe("monitoring copy", () => {
  it("turns research chores into system-owned monitoring", () => {
    expect(monitoringText("打开个股证据账本复核均线与资金")).toBe("持续复查价格、资金、可能收益和风险");
    expect(monitoringText("补齐公告与研报")).toBe("持续扫描公告与研报，获取后自动补入判断");
    expect(monitoringText("等待下一交易日确认")).toBe("等待下一交易日数据，届时自动更新结论");
  });

  it("keeps trading and private-data decisions with the user", () => {
    expect(monitoringItem("先减仓，再复核调仓顺序")).toEqual({
      owner: "user",
      label: "需要你决定",
      text: "先减仓，再检查调仓顺序",
    });
    expect(monitoringItem("录入真实成本价").owner).toBe("user");
  });
});
