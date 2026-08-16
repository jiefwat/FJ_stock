import { plainLanguage } from "./plainLanguage";

export type MonitoringItem = {
  owner: "system" | "user";
  label: "自动监控" | "需要你决定";
  text: string;
};

const userDecisionPattern = /买入|卖出|加仓|减仓|止损|止盈|调仓|下单|清仓|新增持仓|录入|填写|保存/;

function automaticCopy(value: string): string {
  const text = plainLanguage(value).replace(/[。；]$/, "");
  if (/^打开个股/.test(text) || /^回到个股/.test(text)) return "持续复查价格、资金、可能收益和风险";
  if (/^回到大盘页(?:检查|看)/.test(text)) return text.replace(/^回到大盘页(?:检查|看)/, "持续检查");
  if (/^补读/.test(text)) return text.replace(/^补读/, "持续扫描");
  if (/^补齐公告与研报/.test(text)) return "持续扫描公告与研报，获取后自动补入判断";
  if (/^补齐资金流后再判断/.test(text)) return text.replace(/^补齐资金流后再判断/, "资金数据补齐后自动判断");
  if (/^核对最近公告/.test(text)) return text.replace(/^核对/, "持续扫描");
  if (/^再确认公司经营情况/.test(text)) return text.replace(/^再确认/, "持续检查");
  if (/^再确认/.test(text) || /^复核/.test(text)) return text.replace(/^(再确认|复核)/, "持续检查");
  if (/^等待下一交易日确认/.test(text)) return "等待下一交易日数据，届时自动更新结论";
  if (/^等上涨后回落/.test(text)) return "等待价格回落条件出现后自动重算结论";
  if (/^继续观察/.test(text)) return "持续观察，状态变化后自动更新结论";
  if (/^写清参与条件和放弃条件/.test(text)) return "按参与条件和放弃条件自动检查";
  if (/^跟踪/.test(text)) return text.replace(/^跟踪/, "持续跟踪");
  if (/^持续|^系统|^自动/.test(text)) return text;
  return `持续跟踪：${text}`;
}

export function monitoringItem(value: string): MonitoringItem {
  const text = plainLanguage(value).replace(/再再确认/g, "再检查");
  if (userDecisionPattern.test(text)) {
    return { owner: "user", label: "需要你决定", text };
  }
  return { owner: "system", label: "自动监控", text: automaticCopy(text) };
}

export function monitoringText(value: string): string {
  return monitoringItem(value).text;
}
